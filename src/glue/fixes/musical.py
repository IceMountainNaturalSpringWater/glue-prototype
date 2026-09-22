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
    voices,
)
from glue.analysis.single import analyze_single_clip
from glue.io.edited import validate_note_edits
from glue.models import MidiClip, MidiNote

from .minimal import RepairPreset
from .musical_config import EditPermissions, MusicalSearch, MusicalWeights, musical_search_for


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
        for voice in voices(clip):
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
                totals["Rhythm complementarity"] += (
                    max(0, 1 - difference / 0.125)
                    * (0.5 if close and not joint_support else 0)
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
        for voice in voices(original):
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
        suggestions = defaultdict(list)
        for s in old_suggestions:
            if s.confidence >= 0.65:
                suggestions[s.target_note_id].extend(s.alternatives)
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
        ranked = sorted(
            clip.notes, key=lambda n: (-2 * bool(suggestions[n.id]) - evidence[n.id], n.id)
        )
        pool = max(2, ceil(config.note_pool * (1 - preserve / 150)))
        for n in ranked[:pool]:
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
            if allow.pitch and not context.protected and n.id not in disabled_pitch_ids:
                for p in dict.fromkeys(targets):
                    if (
                        p != n.pitch
                        and 0 <= p <= 127
                        and (n.id not in pitch_choices or p in pitch_choices[n.id])
                        and (abs(p - n.pitch) <= config.pitch_range or abs(p - n.pitch) == 12)
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
                            >= 4
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
                and not supported_joint_overlap(
                    n, b, clip.ticks_per_beat, clips[1 - slot].ticks_per_beat, joint_spans
                )
                for b in clips[1 - slot].notes
                if not b.is_percussion
            )
            timing_ok = technical or (config.preset is not RepairPreset.MINIMAL and crowding)
            if allow.timing and timing_ok:
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
            if allow.duration and duration_ok:
                amounts = {
                    min(
                        config.duration_beats * clip.ticks_per_beat,
                        n.duration_ticks * config.duration_fraction,
                    ),
                    clip.ticks_per_beat / 8,
                }
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
            if allow.duration and gap and config.preset is not RepairPreset.MINIMAL:
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
    return tuple(options)


def _apply(clips: tuple[MidiClip, ...], options: tuple[_Option, ...]) -> tuple[MidiClip, ...]:
    revised = list(clips)
    for option in options:
        revised[option.slot] = revised[option.slot].with_notes(
            replace(n, **{option.field: option.value}) if n.id == option.note_id else n
            for n in revised[option.slot].notes
        )
    return tuple(revised)


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
    budget = max(1, ceil(config.evaluations * (1 - min(preserves) / 150)))
    limits = tuple(
        0 if p == 100 else max(1, ceil(config.max_edits * (1 - p / 100))) for p in preserves
    )
    evaluated: dict[tuple[MidiClip, ...], MusicalScore] = {clips: before}
    initial = _candidate(clips, clips, (), before, preserves, config)
    frontier = [(initial, ())]
    improving: dict[tuple[MidiClip, ...], MusicalCandidate] = {}

    def evaluate(
        parent: MusicalCandidate, history: tuple[_Option, ...], additions: tuple[_Option, ...]
    ) -> tuple[MusicalCandidate, tuple[_Option, ...]] | None:
        revised = _apply(parent.clips, additions)
        if revised in evaluated or len(evaluated) >= budget:
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
        except ValueError:
            return None
        if _retention(clips, revised, config.weights) == float("inf"):
            return None  # Structural rejection precedes expensive full rescoring.
        score = score_passage(revised, config.weights)
        evaluated[revised] = score
        candidate = _candidate(clips, revised, history + additions, score, preserves, config)
        if candidate.objective < before.cost - 0.01 and score.cost < before.cost - 0.01:
            improving[revised] = candidate
        return candidate, history + additions

    for _ in range(config.depth):
        successors = []
        for parent, history in frontier:
            touched = {(o.slot, o.note_id, o.field) for o in history}
            available = tuple(o for o in options if (o.slot, o.note_id, o.field) not in touched)
            atomic = []
            for option in available:
                if len(evaluated) >= budget * 0.75 and not history:
                    break
                result = evaluate(parent, history, (option,))
                if result:
                    successors.append(result)
                    atomic.append((result[0].objective, option))
            # Coordinated beat/measure/motif bundles; include non-improving
            # atomic options. Distinct fields on the same note can cooperate.
            best_options = [o for _, o in sorted(atomic, key=lambda x: x[0])[:8]]
            if config.preset is not RepairPreset.MINIMAL:
                for a, b in combinations(best_options, 2):
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
            if len(evaluated) >= budget:
                break
        if not successors:
            break
        frontier = sorted(
            successors,
            key=lambda r: (
                r[0].objective,
                len(r[0].edits),
                tuple(
                    (e.slot, e.note_id, e.after.pitch, e.after.onset_ticks, e.after.duration_ticks)
                    for e in r[0].edits
                ),
            ),
        )[: config.beam]
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
    return MusicalRepair(
        clips, before, tuple(retained), allows, preserves, config, len(evaluated), reason
    )
