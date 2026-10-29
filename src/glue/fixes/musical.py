"""Bounded passage search shared by Polish and Combine workflows.

Every state is a complete clip or complete pair. Non-improving intermediate
states remain in the beam, and coordinated phrase bundles get a reserved
evaluation share. Candidate diversity is measured by note, field and strategy.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, replace
from functools import lru_cache
from itertools import combinations, pairwise
from math import ceil

from glue.analysis.musical import (
    analyze_musical,
    harmony_at,
    joint_chord_spans,
    supported_joint_overlap,
)
from glue.analysis.relationships import performance_relations
from glue.analysis.single import analyze_single_clip
from glue.analysis.voices import (
    octave_confidence,
    octave_supported,
    pitch_supported,
    voice_ornaments,
    voice_paths,
)
from glue.io.edited import validate_note_edits
from glue.models import MidiClip, MidiNote

from .context_candidates import context_options
from .minimal import RepairPreset
from .musical_config import EditPermissions, MusicalSearch, MusicalWeights, musical_search_for
from .search_trace import SearchTrace


@dataclass(frozen=True)
class MusicalEdit:
    slot: int
    note_id: int
    before: MidiNote
    after: MidiNote
    reasons: tuple[str, ...]

    @property
    def kinds(self) -> tuple[str, ...]:
        return tuple(
            name
            for name, field in (
                ("Pitch", "pitch"),
                ("Timing", "onset_ticks"),
                ("Duration", "duration_ticks"),
            )
            if getattr(self.before, field) != getattr(self.after, field)
        )


@dataclass(frozen=True)
class MusicalScore:
    components: tuple[tuple[str, float], ...]
    cost: float

    @property
    def estimate(self) -> float:
        return 100 / (1 + self.cost / 20)


@dataclass(frozen=True)
class MusicalCandidate:
    clips: tuple[MidiClip, ...]
    edits: tuple[MusicalEdit, ...]
    score: MusicalScore
    objective: float
    retention_cost: float
    edit_cost: float
    description: str

    @property
    def counts(self) -> tuple[int, int, int]:
        return tuple(
            sum(kind in e.kinds for e in self.edits) for kind in ("Pitch", "Timing", "Duration")
        )


@dataclass(frozen=True)
class MusicalRepair:
    originals: tuple[MidiClip, ...]
    before: MusicalScore
    candidates: tuple[MusicalCandidate, ...]
    permissions: tuple[EditPermissions, ...]
    preservation: tuple[int, ...]
    config: MusicalSearch
    evaluations: int
    stop_reason: str


def _overlap(a: MidiNote, b: MidiNote, ppq_a: int, ppq_b: int) -> float:
    return max(
        0.0,
        min(a.end_ticks / ppq_a, b.end_ticks / ppq_b)
        - max(a.onset_ticks / ppq_a, b.onset_ticks / ppq_b),
    )


def _tension(a: int, b: int) -> float:
    interval = (a - b) % 12
    return {1: 1.0, 11: 1.0, 6: 0.7, 2: 0.15, 10: 0.15}.get(interval, 0.0)


def score_passage(clips: tuple[MidiClip, ...], weights: MusicalWeights) -> MusicalScore:
    """Full passage musical costs; syncopation alone incurs no cost."""
    totals = dict.fromkeys(
        (
            "Harmony",
            "Resolution",
            "Melodic continuity",
            "Voice leading",
            "Bass movement",
            "Rhythm complementarity",
            "Register",
            "Collisions",
            "Unnecessary unisons",
            "Motif consistency (ambiguous)",
            "Performance rhythm",
            "Contextual articulation",
            "Octave context",
        ),
        0.0,
    )
    contexts = []
    for clip in clips:
        model = analyze_musical(clip)
        context = {n.note_id: n for n in model.notes}
        contexts.append(context)
        for motif in model.motifs:
            if len(motif.pitch_variations) == 1:
                ident = motif.pitch_variations[0]
                # One long accented discrepancy in a matching four-attack
                # pattern is weak evidence, not a demand for exact repetition.
                note = next(n for n in clip.notes if n.id == ident)
                if (
                    context[ident].metric_strength >= 0.7
                    and note.duration_ticks >= 0.75 * clip.ticks_per_beat
                ):
                    totals["Motif consistency (ambiguous)"] += 0.25
        count = max(1, len(model.notes))
        totals["Resolution"] += sum(n.tension for n in model.notes) / count
        totals["Voice leading"] += model.voice_leading / 12 + model.parallel_motion * 0.1
        totals["Bass movement"] += max(0, model.bass_motion - 7) / 12
        totals["Collisions"] += len(model.collisions)
        totals["Melodic continuity"] += sum(
            gap / clip.ticks_per_beat for _, gap in model.legato_gaps
        )
        for relation in performance_relations(clip):
            label = "Performance rhythm" if relation.field == "onset_ticks" else "Contextual articulation"
            totals[label] += relation.confidence * relation.deviation
        for note in clip.notes:
            totals["Octave context"] += max(octave_confidence(clip, note, note.pitch + delta)
                                            for delta in (-12, 12))
        for voice in voice_paths(clip):
            totals["Melodic continuity"] += (
                sum(
                    max(0, abs(a.pitch - b.pitch) - 9) / 12
                    for a, b in pairwise(voice)
                    if a.onset_ticks != b.onset_ticks
                )
                / count
            )
        for i, a in enumerate(clip.notes):
            if a.is_percussion:
                continue
            for b in clip.notes[i + 1 :]:
                if b.onset_ticks >= a.end_ticks:
                    break
                if b.is_percussion:
                    continue
                protected = (
                    context.get(a.id)
                    and context[a.id].protected
                    or (context.get(b.id) and context[b.id].protected)
                )
                duration = _overlap(a, b, clip.ticks_per_beat, clip.ticks_per_beat)
                totals["Harmony"] += (
                    duration
                    * _tension(a.pitch, b.pitch)
                    * (0.1 if protected else 1)
                    / max(1, count / 4)
                )
    if len(clips) == 2:
        left, right = clips
        joint_spans = joint_chord_spans(clips)
        norm = max(1, min(len(left.notes), len(right.notes)) / 4)
        for a in left.notes:
            if a.is_percussion:
                continue
            for b in right.notes:
                if b.is_percussion:
                    continue
                overlap = _overlap(a, b, left.ticks_per_beat, right.ticks_per_beat)
                difference = abs(
                    a.onset_ticks / left.ticks_per_beat - b.onset_ticks / right.ticks_per_beat
                )
                close = abs(a.pitch - b.pitch) < 12
                conflict = _tension(a.pitch, b.pitch)
                joint_support = supported_joint_overlap(
                    a, b, left.ticks_per_beat, right.ticks_per_beat, joint_spans
                )
                protected = (
                    joint_support
                    or contexts[0].get(a.id)
                    and contexts[0][a.id].protected
                    or (contexts[1].get(b.id) and contexts[1][b.id].protected)
                )
                totals["Harmony"] += overlap * conflict * (0.15 if protected else 1) / norm
                # Same attacks are evidence only when parts crowd the same
                # register or create tension; aligned accompaniment is valid.
                competing_lines = (len(voice_paths(left)) == len(voice_paths(right)) == 1
                                   and close and conflict > 0)
                totals["Rhythm complementarity"] += (
                    max(0, 1 - difference / 0.125)
                    * (0.5 if close and not joint_support and (conflict >= .7 or competing_lines) else 0)
                    / norm
                )
                totals["Register"] += overlap * max(0, 3 - abs(a.pitch - b.pitch)) / 3 / norm
                totals["Unnecessary unisons"] += overlap * (a.pitch == b.pitch) / norm
    factors = (
        weights.harmony,
        weights.resolution,
        weights.melody,
        weights.voice_leading,
        weights.bass,
        weights.rhythm,
        weights.register,
        weights.collision,
        weights.unison,
        weights.motif_consistency,
        weights.performance_rhythm,
        weights.articulation,
        weights.octave_context,
    )
    return MusicalScore(
        tuple(totals.items()), sum(v * w for v, w in zip(totals.values(), factors, strict=True))
    )


def _retention(
    originals: tuple[MidiClip, ...], revised: tuple[MidiClip, ...], weights: MusicalWeights
) -> float:
    if len(originals) == 2:
        before_coincidence = _coincidence(originals)
        after_coincidence = _coincidence(revised)
        if after_coincidence >= 0.8 and after_coincidence - before_coincidence > 0.3:
            return float("inf")  # Do not turn distinct parts into one doubled line.
    cost = 0.0
    for original, clip in zip(originals, revised, strict=True):
        before = {n.id: n for n in original.notes}
        after = {n.id: n for n in clip.notes}
        model = analyze_musical(original)
        rhythmic_evidence = {r.note_id: r for r in performance_relations(original) if r.field == "onset_ticks"}
        for voice in voice_paths(original):
            if (
                len(voice) >= 4
                and len({n.onset_ticks for n in voice}) == len(voice)
                and max(n.pitch for n in voice) - min(n.pitch for n in voice) >= 4
                and len({after[n.id].pitch for n in voice}) == 1
            ):
                return float("inf")  # Full contour flattening is not musical repair.
            for a, b in pairwise(voice):
                if a.onset_ticks == b.onset_ticks:
                    continue
                old = b.pitch - a.pitch
                new = after[b.id].pitch - after[a.id].pitch
                # Preserve direction; octave-error correction can smooth a leap.
                if old * new < 0 and abs(old) <= 9:
                    cost += weights.contour
                old_gap = b.onset_ticks - a.onset_ticks
                new_gap = after[b.id].onset_ticks - after[a.id].onset_ticks
                if new_gap <= 0:
                    return float("inf")
                supported = any(n.id in rhythmic_evidence and after[n.id].onset_ticks in rhythmic_evidence[n.id].values
                                for n in (a, b))
                if not supported:
                    cost += weights.groove * abs(new_gap - old_gap) / original.ticks_per_beat * 0.1
        for motif in model.motifs:
            variation = set(motif.pitch_variations)
            damage = 0
            for a, b in zip(motif.first, motif.repeated, strict=True):
                if b not in variation:
                    pitch_delta = (after[b].pitch - before[b].pitch) - (
                        after[a].pitch - before[a].pitch
                    )
                    timing_delta = (after[b].onset_ticks - before[b].onset_ticks) - (
                        after[a].onset_ticks - before[a].onset_ticks
                    )
                    duration_delta = (after[b].duration_ticks - before[b].duration_ticks) - (
                        after[a].duration_ticks - before[a].duration_ticks
                    )
                    damage += pitch_delta != 0
                    cost += weights.motif * min(1, abs(pitch_delta) / 2)
                    cost += (
                        weights.groove
                        * (abs(timing_delta) + abs(duration_delta))
                        / original.ticks_per_beat
                    )
            if damage > len(motif.first) / 2:
                return float("inf")
        for context in model.notes:
            if context.protected:
                a, b = before[context.note_id], after[context.note_id]
                if a.pitch != b.pitch:
                    return float("inf")
    return cost


@lru_cache(maxsize=192)
def _coincidence(clips: tuple[MidiClip, ...]) -> float:
    signatures = [
        Counter(
            (n.pitch, n.onset_ticks / c.ticks_per_beat)
            for n in c.notes
            if not n.is_percussion and n.duration_ticks > 0
        )
        for c in clips
    ]
    count = min(sum(s.values()) for s in signatures)
    return sum((signatures[0] & signatures[1]).values()) / count if count >= 3 else 0.0


@dataclass(frozen=True)
class _Option:
    slot: int
    note_id: int
    field: str
    value: int
    reason: str
    provenance: tuple[str, ...] = ()


@lru_cache(maxsize=64)
def _suggestions(clip: MidiClip) -> tuple:
    return analyze_single_clip(clip).suggestions


def _options(
    clips: tuple[MidiClip, ...],
    permissions: tuple[EditPermissions, ...],
    preservation: tuple[int, ...],
    config: MusicalSearch,
    enabled: frozenset[int] | None,
    disabled_pitch_ids: frozenset[int],
    pitch_choices: Mapping[int, frozenset[int]],
) -> tuple[_Option, ...]:
    options = []
    joint_spans = joint_chord_spans(clips) if len(clips) == 2 else ((), ())
    for slot, (clip, allow, preserve) in enumerate(
        zip(clips, permissions, preservation, strict=True)
    ):
        if preserve == 100:
            continue
        model = analyze_musical(clip)
        contexts = {n.note_id: n for n in model.notes}
        old_suggestions = _suggestions(clip)
        ornaments = voice_ornaments(clip)
        suggestions = defaultdict(list)
        notes_by_id = {n.id: n for n in clip.notes}
        for s in old_suggestions:
            if (s.category.value in {"harmonic-conflict", "bass-conflict"}
                    and contexts[s.target_note_id].function == "chord tone"):
                continue  # Global-key disagreement alone must not override local chord support.
            if s.confidence >= 0.65:
                suggestions[s.target_note_id].extend(
                    p for p in s.alternatives
                    if octave_supported(clip, notes_by_id[s.target_note_id], p)
                )
        contextual = context_options(clip, allow, config)
        context_strength = defaultdict(int)
        for option in contextual:
            field_key = (option.note_id, option.field)
            context_strength[field_key] = max(context_strength[field_key], option.strength)
        evidence = {n.id: contexts[n.id].tension if n.id in contexts else 0 for n in clip.notes}
        for a, b in model.collisions:
            evidence[a] += 6
            evidence[b] += 6
        if len(clips) == 2:
            other = clips[1 - slot]
            for n in clip.notes:
                evidence[n.id] += sum(
                    _overlap(n, b, clip.ticks_per_beat, other.ticks_per_beat)
                    * _tension(n.pitch, b.pitch)
                    for b in other.notes
                    if not b.is_percussion
                )
        pool = max(2, ceil(config.note_pool * (1 - preserve / 150)))
        fields = ("pitch", "onset_ticks", "duration_ticks")
        ranked_fields = {field: sorted(clip.notes, key=lambda n: (
            -2 * bool(suggestions[n.id]) * (field == "pitch") - evidence[n.id]
            - context_strength[n.id, field], n.id))[:pool] for field in fields}
        selected = {field: {n.id for n in notes} for field, notes in ranked_fields.items()}
        ranked = list(dict.fromkeys(n for field in fields for n in ranked_fields[field]))
        for n in ranked:
            if (
                n.is_percussion
                or n.duration_ticks <= 0
                or enabled is not None
                and n.id not in enabled
            ):
                continue
            context = contexts[n.id]
            frame = harmony_at(model.frames, n.onset_ticks / clip.ticks_per_beat)
            targets = list(suggestions[n.id])
            if (
                frame
                and context.tension > 0
                and context.metric_strength >= 0.7
                and n.duration_ticks >= clip.ticks_per_beat * 0.75
            ):
                targets += sorted(
                    (
                        p
                        for p in range(
                            max(0, n.pitch - config.pitch_range),
                            min(128, n.pitch + config.pitch_range + 1),
                        )
                        if p % 12 in frame.harmony.pitches
                    ),
                    key=lambda p: (abs(p - n.pitch), p),
                )
            if len(clips) == 2:
                other = clips[1 - slot]
                for b in other.notes:
                    if (
                        not b.is_percussion
                        and _overlap(n, b, clip.ticks_per_beat, other.ticks_per_beat)
                        and _tension(n.pitch, b.pitch) >= 0.7
                        and not supported_joint_overlap(
                            n, b, clip.ticks_per_beat, other.ticks_per_beat, joint_spans
                        )
                    ):
                        targets += [
                            n.pitch + d
                            for d in (-2, -1, 1, 2)
                            if _tension(n.pitch + d, b.pitch) == 0
                        ]
            if (allow.pitch and n.id in selected["pitch"]
                    and not context.protected and n.id not in ornaments and n.id not in disabled_pitch_ids):
                for p in sorted(set(targets), key=lambda p: (abs(p - n.pitch) >= 12, abs(p - n.pitch), p)):
                    if (
                        p != n.pitch
                        and 0 <= p <= 127
                        and (n.id not in pitch_choices or p in pitch_choices[n.id])
                        and (abs(p - n.pitch) <= config.pitch_range or abs(p - n.pitch) == 12)
                        and pitch_supported(clip, n, p)
                    ):
                        support = next(
                            (
                                s.explanation
                                for s in old_suggestions
                                if s.target_note_id == n.id
                                and p in s.alternatives
                                and s.confidence >= 0.65
                            ),
                            "Possible unresolved local or cross-clip tension.",
                        )
                        options.append(
                            _Option(
                                slot,
                                n.id,
                                "pitch",
                                p,
                                support
                                + " "
                                + f"Possible {context.function} at beat {n.onset_ticks / clip.ticks_per_beat:g}; "
                                f"metric strength {context.metric_strength:.2f}, local "
                                f"{frame.harmony.label if frame else 'ambiguous harmony'} "
                                f"({context.confidence:.0%} confidence). "
                                "Full-passage harmony and phrase/motif retention favor this alternative.",
                            )
                        )
                        if (
                            sum(
                                o.slot == slot and o.note_id == n.id and o.field == "pitch"
                                for o in options
                            )
                            >= {RepairPreset.MINIMAL: 4, RepairPreset.BALANCED: 8,
                                RepairPreset.CREATIVE: 12}[config.preset]
                        ):
                            break
            technical = any(n.id in pair for pair in model.collisions)
            crowding = len(clips) == 2 and any(
                abs(
                    n.onset_ticks / clip.ticks_per_beat
                    - b.onset_ticks / clips[1 - slot].ticks_per_beat
                )
                < 0.125
                and abs(n.pitch - b.pitch) < 12
                # Coincidence alone is not a mistake. Require actual dissonance
                # or competing monophonic second-interval lines, not doubling.
                and (_tension(n.pitch, b.pitch) >= 0.7 or
                     _tension(n.pitch, b.pitch) > 0
                     and len(voice_paths(clip)) == len(voice_paths(clips[1 - slot])) == 1)
                and not supported_joint_overlap(
                    n, b, clip.ticks_per_beat, clips[1 - slot].ticks_per_beat, joint_spans
                )
                for b in clips[1 - slot].notes
                if not b.is_percussion
            )
            # A nearby dissonant attack can justify moving a short linked
            # response phrase, including its consonant tail. This is evidence
            # from the phrase, not permission based on unison alone.
            linked_clash = len(clips) == 2 and any(
                a.id != n.id and a.track == n.track and a.channel == n.channel
                and abs(a.onset_ticks - n.onset_ticks) <= clip.ticks_per_beat
                and _tension(a.pitch, b.pitch) >= 0.7
                and abs(a.onset_ticks / clip.ticks_per_beat
                        - b.onset_ticks / clips[1 - slot].ticks_per_beat) < 0.125
                for a in clip.notes for b in clips[1 - slot].notes)
            timing_ok = technical or (config.preset is not RepairPreset.MINIMAL
                                      and (crowding or linked_clash))
            if allow.timing and timing_ok and n.id in selected["onset_ticks"]:
                for shift in sorted({config.grid_beats, config.onset_beats}):
                    ticks = shift * clip.ticks_per_beat
                    if ticks != int(ticks):
                        continue  # Never introduce rounding drift at unusual PPQ.
                    for sign in (1, -1):
                        target = n.onset_ticks + sign * int(ticks)
                        if target >= 0:
                            options.append(
                                _Option(
                                    slot,
                                    n.id,
                                    "onset_ticks",
                                    target,
                                    "Reduces a competing or duplicate attack while retaining the original off-grid offset.",
                                )
                            )
            sustain_conflict = len(clips) == 2 and any(
                _overlap(n, b, clip.ticks_per_beat, clips[1 - slot].ticks_per_beat) > 0
                and _tension(n.pitch, b.pitch) >= 0.7
                and not supported_joint_overlap(
                    n, b, clip.ticks_per_beat, clips[1 - slot].ticks_per_beat, joint_spans
                )
                for b in clips[1 - slot].notes
                if not b.is_percussion
            )
            # Do not trim an intentional ornament (or its accompaniment) merely
            # to remove a small residual dissonance cost. Single-part sustain
            # edits require a technical collision; cross-part edits require
            # concrete sustained clash evidence.
            duration_ok = technical or (
                config.preset is not RepairPreset.MINIMAL
                and sustain_conflict
                and not context.protected
            )
            if allow.duration and duration_ok and n.id in selected["duration_ticks"]:
                if len(clips) == 2:
                    other = clips[1 - slot]
                    for b in other.notes:
                        boundary = b.onset_ticks * clip.ticks_per_beat / other.ticks_per_beat
                        value = boundary - n.onset_ticks
                        if (boundary == int(boundary) and value > 0
                                and _tension(n.pitch, b.pitch) >= 0.7
                                and abs(value - n.duration_ticks) <= min(
                                    config.duration_beats * clip.ticks_per_beat,
                                    config.duration_fraction * n.duration_ticks)):
                            options.append(_Option(slot, n.id, "duration_ticks", int(value),
                                "Sustain ends at a conflicting other-voice attack boundary.",
                                ("collision resolution", "voice release")))
                amounts = {
                    min(
                        config.duration_beats * clip.ticks_per_beat,
                        n.duration_ticks * config.duration_fraction,
                    ),
                    clip.ticks_per_beat / 8,
                }
                if config.preset is not RepairPreset.MINIMAL:
                    amounts.update((clip.ticks_per_beat / 4, clip.ticks_per_beat / 2))
                for amount in sorted(amounts):
                    if amount != int(amount):
                        continue
                    for sign in (-1, 1):
                        target = n.duration_ticks + sign * int(amount)
                        if target > 0:
                            options.append(
                                _Option(
                                    slot,
                                    n.id,
                                    "duration_ticks",
                                    target,
                                    "Adjusts sustain across a local harmony or phrase boundary; the complete passage is rescored.",
                                )
                            )
            gap = dict(model.legato_gaps).get(n.id)
            if (allow.duration and gap and config.preset is not RepairPreset.MINIMAL
                    and n.id in selected["duration_ticks"]):
                options.append(
                    _Option(
                        slot,
                        n.id,
                        "duration_ticks",
                        n.duration_ticks + gap,
                        "Closes an isolated small gap in an otherwise legato, stepwise line; "
                        "retains its attacks and leaves repeated articulation unchanged.",
                    )
                )
            extra = [o for o in contextual if o.note_id == n.id
                     and n.id in selected[o.field]
                     and (o.field != "pitch" or n.id not in disabled_pitch_ids
                          and (n.id not in pitch_choices or o.value in pitch_choices[n.id]))]
            for option in extra:
                options.append(_Option(slot, n.id, option.field, option.value, option.reason,
                                       (option.reason,)))
    # Merge evidence for identical values and bound each field independently.
    # The unchanged value remains the starting search state, never a fake edit.
    merged: dict[tuple, _Option] = {}
    counts: Counter = Counter()
    caps = {RepairPreset.MINIMAL: (4, 2, 2), RepairPreset.BALANCED: (8, 4, 6),
            RepairPreset.CREATIVE: (12, 6, 8)}[config.preset]
    for option in options:
        key = (option.slot, option.note_id, option.field, option.value)
        provenance = option.provenance or ("legacy contextual evidence: " + option.reason,)
        if key in merged:
            merged[key] = replace(merged[key], provenance=tuple(dict.fromkeys(
                merged[key].provenance + provenance)))
            continue
        field = key[:3]
        cap = caps[("pitch", "onset_ticks", "duration_ticks").index(option.field)]
        if counts[field] < cap:
            merged[key] = replace(option, provenance=provenance)
            counts[field] += 1
    # Share the same fixed evaluation budget across target fields and clips.
    # Round-robin first alternatives before spending it on one note's rank 8.
    groups: dict[tuple, list[_Option]] = {}
    for option in merged.values():
        groups.setdefault((option.slot, option.note_id, option.field), []).append(option)
    lanes = [[values for (s, _, f), values in groups.items() if s == slot and f == field]
             for slot in range(len(clips)) for field in ("pitch", "onset_ticks", "duration_ticks")]
    return tuple(lane[target][rank]
                 for rank in range(max(caps))
                 for target in range(max((len(lane) for lane in lanes), default=0))
                 for lane in lanes if target < len(lane) and rank < len(lane[target]))


def _apply(clips: tuple[MidiClip, ...], options: tuple[_Option, ...]) -> tuple[MidiClip, ...]:
    revised = list(clips)
    for option in options:
        revised[option.slot] = revised[option.slot].with_notes(
            replace(n, **{option.field: option.value}) if n.id == option.note_id else n
            for n in revised[option.slot].notes
        )
    return tuple(revised)


def _linked_options(options: tuple[_Option, ...]) -> tuple[tuple[_Option, ...], ...]:
    """Bounded evidence-linked bundles, before generic local combinations.

    Corresponding motif pitch/onset/release values describe one unit. Keep
    several ranked alternatives rather than an unconstrained cross product.
    All bundles still pass the ordinary full-state validation and rescoring.
    """
    units: dict[tuple[int, int], dict[str, _Option]] = {}
    for option in options:
        if any("motif" in p or "voice" in p or "articulation" in p for p in option.provenance):
            fields = units.setdefault((option.slot, option.note_id), {})
            fields.setdefault(option.field, option)
    bundles = []
    for fields in units.values():
        if len(fields) > 1:
            bundles.append(tuple(fields.values()))
        if len(bundles) >= 8:
            break
    return tuple(bundles)


def _rhythmic_bundles(clips: tuple[MidiClip, ...], options: tuple[_Option, ...], limit: int) -> tuple:
    """Move a short, already-targeted line coherently rather than destroy its IOIs."""
    grouped: dict[tuple, list[_Option]] = {}
    for slot, clip in enumerate(clips):
        notes = {n.id: n for n in clip.notes}
        identities = {n.id: i for i, line in enumerate(voice_paths(clip)) for n in line}
        for option in options:
            if option.slot == slot and option.field == "onset_ticks":
                delta = option.value - notes[option.note_id].onset_ticks
                grouped.setdefault((slot, identities.get(option.note_id), delta), []).append(option)
    return tuple(tuple(values[:limit]) for _, values in sorted(grouped.items())
                 if 2 <= len(values) <= limit)[:4]


def _candidate(
    originals: tuple[MidiClip, ...],
    revised: tuple[MidiClip, ...],
    options: tuple[_Option, ...],
    score: MusicalScore,
    preservation: tuple[int, ...],
    config: MusicalSearch,
) -> MusicalCandidate:
    edits, edit_cost = [], 0.0
    for slot, (before, after) in enumerate(zip(originals, revised, strict=True)):
        originals_by_id = {n.id: n for n in before.notes}
        for note in after.notes:
            old = originals_by_id[note.id]
            if old == note:
                continue
            reasons = tuple(
                dict.fromkeys(o.reason for o in options if o.slot == slot and o.note_id == note.id)
            )
            edits.append(MusicalEdit(slot, note.id, old, note, reasons))
            p = preservation[slot] / 100
            w = config.weights
            edit_cost += (
                p
                * (
                    w.edit
                    + abs(note.pitch - old.pitch) * w.pitch_distance
                    + abs(note.onset_ticks - old.onset_ticks)
                    / before.ticks_per_beat
                    * w.onset_distance
                    + abs(note.duration_ticks - old.duration_ticks)
                    / before.ticks_per_beat
                    * w.duration_distance
                )
                + p * p * w.preservation
            )
    retention = _retention(originals, revised, config.weights)
    kinds = sorted({kind for edit in edits for kind in edit.kinds})
    description = " + ".join(kinds) + " adjustment"
    return MusicalCandidate(
        revised,
        tuple(edits),
        score,
        score.cost + retention + edit_cost,
        retention,
        edit_cost,
        description,
    )


def _signature(candidate: MusicalCandidate) -> frozenset:
    return frozenset((e.slot, e.note_id, kind) for e in candidate.edits for kind in e.kinds)


def _changes(candidate: MusicalCandidate) -> frozenset:
    return frozenset(
        (e.slot, e.note_id, field, getattr(e.after, field))
        for e in candidate.edits
        for field in ("pitch", "onset_ticks", "duration_ticks")
        if getattr(e.before, field) != getattr(e.after, field)
    )


def generate_musical_repairs(
    clip_a: MidiClip,
    clip_b: MidiClip | None = None,
    *,
    permissions: tuple[EditPermissions, ...] | None = None,
    preservation: tuple[int, ...] | None = None,
    preset: RepairPreset | str = RepairPreset.MINIMAL,
    enabled_note_ids: frozenset[int] | None = None,
    disabled_pitch_ids: frozenset[int] = frozenset(),
    pitch_choices: Mapping[int, frozenset[int]] | None = None,
    weights: MusicalWeights | None = None,
    trace: SearchTrace | None = None,
) -> MusicalRepair:
    """Return diverse improving passage candidates under explicit permissions."""
    clips = (clip_a,) if clip_b is None else (clip_a, clip_b)
    if pitch_choices is not None and clip_b is not None:
        raise ValueError("Suggestion pitch choices apply to single-clip repair")
    allows = permissions if permissions is not None else (EditPermissions(),) * len(clips)
    preserves = preservation if preservation is not None else (100,) * len(clips)
    if len(allows) != len(clips) or not all(isinstance(p, EditPermissions) for p in allows):
        raise ValueError("Provide one EditPermissions value per clip")
    if len(preserves) != len(clips) or any(
        type(p) is not int or not 0 <= p <= 100 for p in preserves
    ):
        raise ValueError("Provide integer preservation percentages for every clip")
    config = musical_search_for(preset)
    if weights is not None:
        config = replace(config, weights=weights)
    before = score_passage(clips, config.weights)
    options = _options(
        clips, allows, preserves, config, enabled_note_ids, disabled_pitch_ids, pitch_choices or {}
    )
    if trace is not None:
        trace.reset(options, clips)
    budget = max(1, ceil(config.evaluations * (1 - min(preserves) / 150)))
    limits = tuple(
        0 if p == 100 else max(1, ceil(config.max_edits * (1 - p / 100))) for p in preserves
    )
    evaluated: dict[tuple[MidiClip, ...], MusicalScore] = {clips: before}
    initial = _candidate(clips, clips, (), before, preserves, config)
    frontier = [(initial, ())]
    improving: dict[tuple[MidiClip, ...], MusicalCandidate] = {}
    round_budget = budget

    def evaluate(
        parent: MusicalCandidate, history: tuple[_Option, ...], additions: tuple[_Option, ...]
    ) -> tuple[MusicalCandidate, tuple[_Option, ...]] | None:
        revised = _apply(parent.clips, additions)
        if revised in evaluated or len(evaluated) >= round_budget:
            if trace is not None:
                trace.record(history + additions, "duplicate_state" if revised in evaluated
                             else "evaluation_budget" if round_budget == budget else "round_budget")
            return None
        try:
            for slot, (source, target, allow) in enumerate(
                zip(clips, revised, allows, strict=True)
            ):
                count = sum(
                    a != b
                    for a, b in zip(
                        sorted(source.notes, key=lambda n: n.id),
                        sorted(target.notes, key=lambda n: n.id),
                        strict=True,
                    )
                )
                if count > limits[slot]:
                    if trace is not None:
                        trace.record(history + additions, f"clip_{slot}_edit_limit")
                    return None
                validate_note_edits(
                    source,
                    target,
                    pitch=allow.pitch,
                    timing=allow.timing,
                    duration=allow.duration,
                    onset_limit=config.onset_beats,
                    duration_limit=config.duration_beats,
                    duration_fraction=config.duration_fraction,
                )
        except ValueError as exc:
            if trace is not None:
                trace.record(history + additions, f"safety: {exc}")
            return None
        if _retention(clips, revised, config.weights) == float("inf"):
            if trace is not None:
                trace.record(history + additions, "structural_retention")
            return None  # Structural rejection precedes expensive full rescoring.
        score = score_passage(revised, config.weights)
        evaluated[revised] = score
        candidate = _candidate(clips, revised, history + additions, score, preserves, config)
        if candidate.objective < before.cost - 0.01 and score.cost < before.cost - 0.01:
            improving[revised] = candidate
        if trace is not None:
            trace.record(history + additions, "improving" if revised in improving
                         else "not_improving_objective", candidate)
        return candidate, history + additions

    for _ in range(config.depth):
        # Reserve evaluations for later coordinated rounds; widening options
        # must not spend the entire budget on shallow one/two-note variations.
        round_start = len(evaluated)
        round_budget = min(budget, max(round_start + 1, ceil(budget * (_ + 1) / config.depth)))
        if trace is not None:
            trace.round = _ + 1
        successors = []
        for parent, history in frontier:
            touched = {(o.slot, o.note_id, o.field) for o in history}
            available = tuple(o for o in options if (o.slot, o.note_id, o.field) not in touched)
            if config.preset is not RepairPreset.MINIMAL:
                for bundle in _rhythmic_bundles(clips, available, config.max_edits):
                    result = evaluate(parent, history, bundle)
                    if result:
                        successors.append(result)
            atomic = []
            for option in available:
                if len(evaluated) >= round_start + (round_budget - round_start) * 0.75:
                    break
                result = evaluate(parent, history, (option,))
                if result:
                    successors.append(result)
                    atomic.append((result[0].objective, option))
            # Coordinated beat/measure/motif bundles; include non-improving
            # atomic options. Distinct fields on the same note can cooperate.
            best_options = [o for _, o in sorted(atomic, key=lambda x: x[0])[:8]]
            if config.preset is not RepairPreset.MINIMAL:
                for bundle in _linked_options(available):
                    result = evaluate(parent, history, bundle)
                    if result:
                        successors.append(result)
                # Reserve bounded proposals even when their isolated states
                # violate a collision/retention constraint. A simultaneous swap
                # or coordinated movement can be valid as a complete passage.
                seeds = []
                seen_fields = set()
                for option in available:
                    field = (option.slot, option.note_id, option.field)
                    if field not in seen_fields:
                        seeds.append(option)
                        seen_fields.add(field)
                seed_cap = 4 if config.preset is RepairPreset.BALANCED else 8
                bundle_options = list(dict.fromkeys(best_options + seeds[:seed_cap]))
                for a, b in combinations(bundle_options, 2):
                    if (a.slot, a.note_id, a.field) == (b.slot, b.note_id, b.field):
                        continue
                    na = next(n for n in clips[a.slot].notes if n.id == a.note_id)
                    nb = next(n for n in clips[b.slot].notes if n.id == b.note_id)
                    if (
                        abs(
                            na.onset_ticks / clips[a.slot].ticks_per_beat
                            - nb.onset_ticks / clips[b.slot].ticks_per_beat
                        )
                        > 4
                    ):
                        continue
                    result = evaluate(parent, history, (a, b))
                    if result:
                        successors.append(result)
            if len(evaluated) >= round_budget:
                break
        if not successors:
            break
        ordered = sorted(
            successors,
            key=lambda r: (
                r[0].objective,
                len(r[0].edits),
                tuple(
                    (e.slot, e.note_id, e.after.pitch, e.after.onset_ticks, e.after.duration_ticks)
                    for e in r[0].edits
                ),
            ),
        )
        frontier = ordered[: config.beam]
        if config.preset is RepairPreset.CREATIVE and min(preserves) < 50:
            # Keep the best objective state, but reserve two slots for a
            # different note/field footprint. Neutral enabling edits should not
            # all lose to many near-identical alternatives of the same note.
            core = ordered[: max(1, config.beam - 2)]
            footprints = {_signature(candidate) for candidate, _ in core}
            probes = []
            for item in ordered[len(core):]:
                footprint = _signature(item[0])
                if footprint not in footprints:
                    probes.append(item)
                    footprints.add(footprint)
                    if len(probes) == 2:
                        break
            frontier = (core + probes)
            frontier += [item for item in ordered if item not in frontier][
                :config.beam - len(frontier)]
        if trace is not None:
            trace.beam(successors, frontier)
        if len(evaluated) >= budget:
            break
    retained = []
    ordered_candidates = sorted(
        improving.values(),
        key=lambda c: (round(c.objective, 9), sum(c.counts), len(c.edits), c.description),
    )
    change_sets = [(other, _changes(other)) for other in ordered_candidates]
    for c in ordered_candidates:
        # At 0% preservation ordinary edit costs disappear, but adding a
        # redundant edit still must not count as a genuinely new alternative.
        changes = _changes(c)
        if any(
            other_changes < changes
            and other.objective <= c.objective + 1e-9
            and other.score.cost <= c.score.cost + 1e-9
            for other, other_changes in change_sets
        ):
            continue
        sig = _signature(c)
        if any(
            len(sig & _signature(p)) / max(1, len(sig | _signature(p))) > 0.75 for p in retained
        ):
            continue
        retained.append(c)
        if len(retained) == config.alternatives:
            break
    reason = (
        f"Retained {len(retained)} improving passage alternatives."
        if retained
        else "No improving candidate found within the selected permissions, preservation, and search bounds."
    )
    if all(p == 100 for p in preserves):
        reason = "Preservation is 100%; no edits are allowed."
    if len(evaluated) >= budget:
        reason += " Evaluation budget reached."
    if trace is not None:
        trace.finish(retained)
    return MusicalRepair(
        clips, before, tuple(retained), allows, preserves, config, len(evaluated), reason
    )
