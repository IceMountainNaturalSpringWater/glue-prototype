"""Deterministic, GUI-independent review suggestions for one MIDI clip.

The heuristics in this module intentionally use neutral language.  They point
to material a producer may wish to inspect; they do not classify notes as
objectively correct or incorrect.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import pairwise
from math import floor

from glue.models import MidiClip, MidiNote

from .compatibility import infer_local_harmony_candidates, scale_pitch_classes
from .config import DEFAULT_SINGLE_ANALYSIS_CONFIG, SingleAnalysisConfig
from .key import estimate_key
from .results import (
    PITCH_CLASS_NAMES,
    KeyEstimate,
    SingleClipAnalysis,
    SingleClipSuggestion,
    SingleSuggestionCategory,
)

_EPSILON = 1e-9
_CATEGORY_ORDER = {
    category: index for index, category in enumerate(SingleSuggestionCategory)
}


def _pitched_notes(clip: MidiClip) -> tuple[MidiNote, ...]:
    return tuple(
        note
        for note in clip.notes
        if not note.is_percussion and note.duration_ticks > 0
    )


def _notes_overlap(left: MidiNote, right: MidiNote) -> bool:
    return (
        left.onset_ticks < right.end_ticks
        and right.onset_ticks < left.end_ticks
    )


def _would_create_new_collision(
    clip: MidiClip,
    note: MidiNote,
    pitch: int,
) -> bool:
    return any(
        other.id != note.id
        and other.track == note.track
        and other.channel == note.channel
        and other.pitch == pitch
        and other.pitch != note.pitch
        and _notes_overlap(note, other)
        for other in clip.notes
    )


def _bounded_alternatives(
    clip: MidiClip,
    note: MidiNote,
    pitches: Iterable[int],
    config: SingleAnalysisConfig,
) -> tuple[int, ...]:
    alternatives: list[int] = []
    seen: set[int] = set()
    for pitch in pitches:
        if (
            pitch in seen
            or pitch == note.pitch
            or not 0 <= pitch <= 127
            or _would_create_new_collision(clip, note, pitch)
        ):
            continue
        seen.add(pitch)
        alternatives.append(pitch)
        if len(alternatives) >= config.maximum_alternatives:
            break
    if alternatives:
        return tuple(alternatives)

    # MIDI-boundary material can exhaust a theory-derived list.  Retain one
    # small, structurally safe review option so every public suggestion has an
    # explicit alternative.
    for delta in (-1, 1, -2, 2, -12, 12):
        pitch = note.pitch + delta
        if (
            0 <= pitch <= 127
            and not _would_create_new_collision(clip, note, pitch)
        ):
            return (pitch,)
    return ()


def _pitches_for_pitch_classes(
    note: MidiNote,
    pitch_classes: Iterable[int],
) -> tuple[int, ...]:
    classes = frozenset(pitch_class % 12 for pitch_class in pitch_classes)
    return tuple(
        sorted(
            (
                pitch
                for pitch in range(
                    max(0, note.pitch - 12),
                    min(127, note.pitch + 12) + 1,
                )
                if pitch != note.pitch and pitch % 12 in classes
            ),
            key=lambda pitch: (
                abs(pitch - note.pitch),
                pitch,
            ),
        )
    )


def _note_name(pitch: int) -> str:
    return f"{PITCH_CLASS_NAMES[pitch % 12]}{pitch // 12 - 1}"


def _suggestion(
    clip: MidiClip,
    note: MidiNote,
    category: SingleSuggestionCategory,
    confidence: float,
    explanation: str,
    alternatives: Iterable[int],
    config: SingleAnalysisConfig,
    *,
    related: Iterable[int] = (),
) -> SingleClipSuggestion | None:
    related_ids = tuple(
        sorted(
            {
                note_id
                for note_id in related
                if note_id != note.id
            }
        )
    )
    bounded = _bounded_alternatives(
        clip,
        note,
        alternatives,
        config,
    )
    if not bounded:
        return None
    related_suffix = "-".join(str(note_id) for note_id in related_ids) or "none"
    return SingleClipSuggestion(
        suggestion_id=f"{category.value}:{note.id}:{related_suffix}",
        target_note_id=note.id,
        related_note_ids=related_ids,
        original_pitch=note.pitch,
        onset_ticks=note.onset_ticks,
        duration_ticks=note.duration_ticks,
        track=note.track,
        channel=note.channel,
        onset_beats=note.onset_ticks / clip.ticks_per_beat,
        duration_beats=note.duration_ticks / clip.ticks_per_beat,
        category=category,
        confidence=max(0.0, min(1.0, confidence)),
        explanation=explanation,
        alternatives=bounded,
    )


def _voice_groups(
    notes: Iterable[MidiNote],
) -> dict[tuple[int, int], tuple[MidiNote, ...]]:
    grouped: dict[tuple[int, int], list[MidiNote]] = defaultdict(list)
    for note in notes:
        grouped[(note.track, note.channel)].append(note)
    return {
        voice: tuple(
            sorted(
                members,
                key=lambda note: (
                    note.onset_ticks,
                    note.pitch,
                    note.id,
                ),
            )
        )
        for voice, members in grouped.items()
    }


def _onset_groups(
    notes: Sequence[MidiNote],
) -> tuple[tuple[MidiNote, ...], ...]:
    by_onset: dict[int, list[MidiNote]] = defaultdict(list)
    for note in notes:
        by_onset[note.onset_ticks].append(note)
    return tuple(
        tuple(sorted(by_onset[onset], key=lambda note: (note.pitch, note.id)))
        for onset in sorted(by_onset)
    )


def _monophonic_neighbors(
    clip: MidiClip,
    note: MidiNote,
) -> tuple[MidiNote | None, MidiNote | None]:
    voice = tuple(
        candidate
        for candidate in _pitched_notes(clip)
        if candidate.track == note.track
        and candidate.channel == note.channel
        and candidate.onset_ticks != note.onset_ticks
    )
    previous = next(
        (
            candidate
            for candidate in reversed(voice)
            if candidate.onset_ticks < note.onset_ticks
        ),
        None,
    )
    following = next(
        (
            candidate
            for candidate in voice
            if candidate.onset_ticks > note.onset_ticks
        ),
        None,
    )
    return previous, following


def _is_chromatic_connector(
    clip: MidiClip,
    note: MidiNote,
) -> bool:
    previous, following = _monophonic_neighbors(clip, note)
    if previous is None or following is None:
        return False
    before = note.pitch - previous.pitch
    after = following.pitch - note.pitch
    duration_beats = note.duration_ticks / clip.ticks_per_beat
    weak_position = (
        abs(note.onset_ticks / clip.ticks_per_beat - round(
            note.onset_ticks / clip.ticks_per_beat
        ))
        > _EPSILON
    )
    return (
        duration_beats <= 0.375
        and weak_position
        and before != 0
        and after != 0
        and (before > 0) == (after > 0)
        and abs(before) <= 2
        and abs(after) <= 2
    )


def _window_bounds(
    clip: MidiClip,
    note: MidiNote,
    config: SingleAnalysisConfig,
) -> tuple[float, float]:
    onset = note.onset_ticks / clip.ticks_per_beat
    start = floor(onset / config.window_beats) * config.window_beats
    return start, start + config.window_beats


def _context_without_note(
    clip: MidiClip,
    note: MidiNote,
) -> MidiClip:
    return clip.with_notes(candidate for candidate in clip.notes if candidate.id != note.id)


def _strong_tension(
    note: MidiNote,
    context_notes: Iterable[MidiNote],
) -> bool:
    return any(
        min(
            (note.pitch - other.pitch) % 12,
            (other.pitch - note.pitch) % 12,
        )
        in (1, 6)
        for other in context_notes
    )


def _harmonic_suggestions(
    clip: MidiClip,
    key: KeyEstimate,
    config: SingleAnalysisConfig,
) -> tuple[SingleClipSuggestion, ...]:
    top = key.top
    if top is None:
        return ()
    scale = scale_pitch_classes(top)
    suggestions: list[SingleClipSuggestion] = []
    for note in _pitched_notes(clip):
        start, end = _window_bounds(clip, note, config)
        context = _context_without_note(clip, note)
        context_notes = tuple(
            candidate
            for candidate in _pitched_notes(context)
            if candidate.onset_ticks / clip.ticks_per_beat < end - _EPSILON
            and candidate.end_ticks / clip.ticks_per_beat > start + _EPSILON
        )
        local = infer_local_harmony_candidates(
            context,
            top,
            start_beat=start,
            end_beat=end,
        )
        local_pitch_classes = (
            frozenset(
                pitch_class
                for candidate in local[:2]
                for pitch_class in candidate.pitch_classes
            )
            if local
            else frozenset()
        )
        outside_scale = note.pitch % 12 not in scale
        local_unsupported = (
            len({candidate.pitch % 12 for candidate in context_notes}) >= 2
            and bool(local)
            and note.pitch % 12 not in local_pitch_classes
            and _strong_tension(note, context_notes)
            and note.duration_ticks / clip.ticks_per_beat >= 0.75
        )
        if not outside_scale and not local_unsupported:
            continue
        if key.confidence < config.minimum_key_confidence and not local_unsupported:
            continue

        connector = _is_chromatic_connector(clip, note)
        duration_factor = min(1.0, note.duration_ticks / clip.ticks_per_beat)
        downbeat = abs(
            note.onset_ticks / clip.ticks_per_beat
            - round(note.onset_ticks / clip.ticks_per_beat)
        ) <= _EPSILON
        confidence = (
            0.36
            + 0.22 * key.confidence
            + 0.14 * duration_factor
            + (0.10 if downbeat else 0.0)
            + (0.10 if local_unsupported else 0.0)
        )
        if connector:
            confidence = min(0.44, confidence * 0.48)

        alternative_classes = (
            tuple(local_pitch_classes)
            + tuple(sorted(scale))
        )
        alternatives = _pitches_for_pitch_classes(
            note,
            alternative_classes,
        )
        qualification = (
            "Its short stepwise placement may instead be intentional chromatic motion."
            if connector
            else (
                f"It has limited support from the estimated {top.label} scale "
                "or the strongest local chord reading."
            )
        )
        item = _suggestion(
            clip,
            note,
            SingleSuggestionCategory.HARMONIC_CONFLICT,
            confidence,
            (
                f"Possible harmonic conflict. {_note_name(note.pitch)} at beat "
                f"{note.onset_ticks / clip.ticks_per_beat:.2f} may stand apart "
                f"from the current context. {qualification}"
            ),
            alternatives,
            config,
            related=(candidate.id for candidate in context_notes),
        )
        if item is not None:
            suggestions.append(item)
    return tuple(suggestions)


def _melodic_suggestions(
    clip: MidiClip,
    key: KeyEstimate,
    config: SingleAnalysisConfig,
) -> tuple[SingleClipSuggestion, ...]:
    scale = scale_pitch_classes(key.top) if key.top is not None else frozenset()
    suggestions: list[SingleClipSuggestion] = []
    for notes in _voice_groups(_pitched_notes(clip)).values():
        singleton_groups = tuple(
            group for group in _onset_groups(notes) if len(group) == 1
        )
        sequence = tuple(group[0] for group in singleton_groups)
        for index in range(1, len(sequence)):
            previous = sequence[index - 1]
            note = sequence[index]
            leap = note.pitch - previous.pitch
            if abs(leap) <= config.leap_threshold_semitones:
                continue
            following = sequence[index + 1] if index + 1 < len(sequence) else None
            resolution = (
                following.pitch - note.pitch if following is not None else None
            )
            resolves = (
                resolution is not None
                and (resolution > 0) != (leap > 0)
                and abs(resolution) <= config.step_resolution_semitones
            )
            confidence = (
                0.56
                + min(
                    0.27,
                    (
                        abs(leap)
                        - config.leap_threshold_semitones
                    )
                    / 36.0,
                )
                + (0.10 if not resolves else -0.18)
            )
            octave_pitch = note.pitch - 12 if leap > 0 else note.pitch + 12
            contour_center = (
                round((previous.pitch + following.pitch) / 2)
                if following is not None
                else previous.pitch
            )
            tonal = tuple(
                pitch
                for pitch in range(
                    max(0, contour_center - 5),
                    min(127, contour_center + 5) + 1,
                )
                if not scale or pitch % 12 in scale
            )
            alternatives = tuple(
                sorted(
                    (octave_pitch, *tonal),
                    key=lambda pitch: (
                        0 if pitch == octave_pitch else 1,
                        abs(pitch - contour_center),
                        pitch,
                    ),
                )
            )
            item = _suggestion(
                clip,
                note,
                SingleSuggestionCategory.MELODIC_LEAP,
                confidence,
                (
                    f"Possible melodic discontinuity. The move from "
                    f"{_note_name(previous.pitch)} to {_note_name(note.pitch)} "
                    f"spans {abs(leap)} semitones"
                    f"{' without a nearby contrary resolution' if not resolves else ''}; "
                    "a smaller contour is one possible interpretation."
                ),
                alternatives,
                config,
                related=(
                    previous.id,
                    *((following.id,) if following is not None else ()),
                ),
            )
            if item is not None:
                suggestions.append(item)
    return tuple(suggestions)


def _voice_leading_suggestions(
    clip: MidiClip,
    config: SingleAnalysisConfig,
) -> tuple[SingleClipSuggestion, ...]:
    suggestions: list[SingleClipSuggestion] = []
    for notes in _voice_groups(_pitched_notes(clip)).values():
        chords = tuple(
            group for group in _onset_groups(notes) if len(group) >= 2
        )
        for previous, current in pairwise(chords):
            if len(previous) != len(current):
                continue
            for earlier, note in zip(previous, current, strict=True):
                movement = note.pitch - earlier.pitch
                if abs(movement) <= config.voice_leading_threshold_semitones:
                    continue
                octave_pitch = note.pitch - 12 if movement > 0 else note.pitch + 12
                if not 0 <= octave_pitch <= 127:
                    continue
                if abs(octave_pitch - earlier.pitch) >= abs(movement):
                    continue
                confidence = min(
                    0.94,
                    0.62
                    + (
                        abs(movement)
                        - config.voice_leading_threshold_semitones
                    )
                    / 32.0,
                )
                item = _suggestion(
                    clip,
                    note,
                    SingleSuggestionCategory.VOICE_LEADING,
                    confidence,
                    (
                        "Possible weak voice leading. This chord voice moves "
                        f"{abs(movement)} semitones from {_note_name(earlier.pitch)} "
                        f"to {_note_name(note.pitch)}; an octave-equivalent voicing "
                        "may retain the harmony with less motion."
                    ),
                    (octave_pitch,),
                    config,
                    related=(earlier.id,),
                )
                if item is not None:
                    suggestions.append(item)
    return tuple(suggestions)


def _duplicate_suggestions(
    clip: MidiClip,
    key: KeyEstimate,
    config: SingleAnalysisConfig,
) -> tuple[SingleClipSuggestion, ...]:
    scale = scale_pitch_classes(key.top) if key.top is not None else frozenset()
    suggestions: list[SingleClipSuggestion] = []
    notes = _pitched_notes(clip)
    for index, left in enumerate(notes):
        for right in notes[index + 1 :]:
            if (
                left.track != right.track
                or left.channel != right.channel
                or left.pitch != right.pitch
                or not _notes_overlap(left, right)
            ):
                continue
            target, related = sorted(
                (left, right),
                key=lambda note: (
                    note.onset_ticks,
                    note.id,
                ),
            )
            target, related = related, target
            overlap_ticks = min(left.end_ticks, right.end_ticks) - max(
                left.onset_ticks,
                right.onset_ticks,
            )
            overlap_fraction = overlap_ticks / max(
                1,
                min(left.duration_ticks, right.duration_ticks),
            )
            exact = (
                left.onset_ticks == right.onset_ticks
                and left.duration_ticks == right.duration_ticks
            )
            confidence = min(
                0.98,
                (0.88 if exact else 0.64) + 0.10 * overlap_fraction,
            )
            pitch_classes = scale or frozenset(
                ((target.pitch - 2) % 12, (target.pitch + 2) % 12)
            )
            candidates = (
                target.pitch - 12,
                target.pitch + 12,
                *_pitches_for_pitch_classes(target, pitch_classes),
            )
            item = _suggestion(
                clip,
                target,
                SingleSuggestionCategory.DUPLICATE_OVERLAP,
                confidence,
                (
                    "Possible duplicate or overlapping note. Two notes with "
                    f"pitch {_note_name(target.pitch)} overlap in the same track "
                    "and channel; this may be intentional doubling."
                ),
                candidates,
                config,
                related=(related.id,),
            )
            if item is not None:
                suggestions.append(item)
    return tuple(suggestions)


def _active_at(notes: Sequence[MidiNote], tick: int) -> tuple[MidiNote, ...]:
    return tuple(
        note
        for note in notes
        if note.onset_ticks <= tick < note.end_ticks
    )


def _register_suggestions(
    clip: MidiClip,
    config: SingleAnalysisConfig,
) -> tuple[SingleClipSuggestion, ...]:
    notes = _pitched_notes(clip)
    suggestions: list[SingleClipSuggestion] = []
    seen_targets: set[int] = set()
    for tick in sorted({note.onset_ticks for note in notes}):
        active = tuple(sorted(_active_at(notes, tick), key=lambda note: (note.pitch, note.id)))
        distinct_pitches = {note.pitch for note in active}
        if (
            len(active) < config.crowding_minimum_notes
            or len(distinct_pitches) < config.crowding_minimum_notes
        ):
            continue
        span = max(distinct_pitches) - min(distinct_pitches)
        if span > config.crowding_span_semitones:
            continue
        confidence = min(
            0.94,
            0.64
            + 0.05 * (len(distinct_pitches) - config.crowding_minimum_notes)
            + 0.12
            * (
                config.crowding_span_semitones - span
            )
            / config.crowding_span_semitones,
        )
        targets = (active[0], active[-1])
        for target in targets:
            if target.id in seen_targets:
                continue
            seen_targets.add(target.id)
            outward = (
                target.pitch - 12
                if target is active[0]
                else target.pitch + 12
            )
            inward = (
                target.pitch + 12
                if target is active[0]
                else target.pitch - 12
            )
            item = _suggestion(
                clip,
                target,
                SingleSuggestionCategory.REGISTER_CROWDING,
                confidence,
                (
                    "Possible register crowding. "
                    f"{len(distinct_pitches)} simultaneous pitches occupy a "
                    f"{span}-semitone span near beat "
                    f"{tick / clip.ticks_per_beat:.2f}; a wider voicing is one option."
                ),
                (outward, inward),
                config,
                related=(note.id for note in active if note.id != target.id),
            )
            if item is not None:
                suggestions.append(item)
    return tuple(suggestions)


def _bass_alternatives(
    note: MidiNote,
    upper: Sequence[MidiNote],
    chord: frozenset[int],
    root_pc: int,
) -> tuple[int, ...]:
    upper_floor = min(candidate.pitch for candidate in upper)
    ordered_classes = (
        root_pc,
        (root_pc + 7) % 12,
        *sorted(chord - {root_pc, (root_pc + 7) % 12}),
    )
    pitches: list[int] = []
    for pitch_class in ordered_classes:
        candidates = tuple(
            pitch
            for pitch in _pitches_for_pitch_classes(note, (pitch_class,))
            if pitch < upper_floor
        )
        pitches.extend(candidates)
    return tuple(pitches)


def _bass_suggestions(
    clip: MidiClip,
    key: KeyEstimate,
    config: SingleAnalysisConfig,
) -> tuple[SingleClipSuggestion, ...]:
    if key.top is None:
        return ()
    notes = _pitched_notes(clip)
    suggestions: dict[int, SingleClipSuggestion] = {}
    for tick in sorted({note.onset_ticks for note in notes}):
        active = tuple(sorted(_active_at(notes, tick), key=lambda note: (note.pitch, note.id)))
        if len(active) < 3:
            continue
        bass = active[0]
        upper = active[1:]
        if len({note.pitch % 12 for note in upper}) < 2:
            continue
        upper_clip = clip.with_notes(upper)
        end = min(note.end_ticks for note in active) / clip.ticks_per_beat
        start = tick / clip.ticks_per_beat
        if end <= start + _EPSILON:
            continue
        local = infer_local_harmony_candidates(
            upper_clip,
            key.top,
            start_beat=start,
            end_beat=end,
        )
        if not local:
            continue
        strongest = local[0]
        chord = frozenset(strongest.pitch_classes)
        if bass.pitch % 12 in chord:
            continue
        distance = min(
            (bass.pitch % 12 - strongest.root_pc) % 12,
            (strongest.root_pc - bass.pitch % 12) % 12,
        )
        outside_scale = bass.pitch % 12 not in scale_pitch_classes(key.top)
        if distance not in (1, 6) and not outside_scale:
            continue
        confidence = min(
            0.96,
            0.58
            + (0.18 if distance in (1, 6) else 0.0)
            + 0.10 * strongest.coverage
            + 0.08 * key.confidence,
        )
        item = _suggestion(
            clip,
            bass,
            SingleSuggestionCategory.BASS_CONFLICT,
            confidence,
            (
                "Possible bass conflict. "
                f"{_note_name(bass.pitch)} sits below an estimated "
                f"{strongest.label} sonority with limited root or chord-tone "
                "support; an inversion or intentional tension may still be valid."
            ),
            _bass_alternatives(
                bass,
                upper,
                chord,
                strongest.root_pc,
            ),
            config,
            related=(note.id for note in upper),
        )
        if item is None:
            continue
        existing = suggestions.get(bass.id)
        if existing is None or item.confidence > existing.confidence:
            suggestions[bass.id] = item
    return tuple(suggestions.values())


def _rhythm_signature(notes: Sequence[MidiNote]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    start = notes[0].onset_ticks
    return (
        tuple(note.onset_ticks - start for note in notes),
        tuple(note.duration_ticks for note in notes),
    )


@dataclass(frozen=True, slots=True)
class _MotifMatch:
    left: tuple[MidiNote, ...]
    right: tuple[MidiNote, ...]
    transposition: int
    agreement: int
    mismatches: tuple[int, ...]
    left_start: int
    right_start: int


def _motif_suggestions(
    clip: MidiClip,
    config: SingleAnalysisConfig,
) -> tuple[SingleClipSuggestion, ...]:
    suggestions: list[SingleClipSuggestion] = []
    for notes in _voice_groups(_pitched_notes(clip)).values():
        groups = _onset_groups(notes)
        if any(len(group) != 1 for group in groups):
            continue
        sequence = tuple(group[0] for group in groups)
        matches: list[_MotifMatch] = []
        for length in range(
            min(config.motif_maximum_length, len(sequence) // 2),
            config.motif_minimum_length - 1,
            -1,
        ):
            for left_start in range(len(sequence) - 2 * length + 1):
                left = sequence[left_start : left_start + length]
                for right_start in range(
                    left_start + length,
                    len(sequence) - length + 1,
                ):
                    right = sequence[right_start : right_start + length]
                    if _rhythm_signature(left) != _rhythm_signature(right):
                        continue
                    differences = tuple(
                        right_note.pitch - left_note.pitch
                        for left_note, right_note in zip(left, right, strict=True)
                    )
                    counts = Counter(differences)
                    transposition, agreement = min(
                        (
                            (difference, count)
                            for difference, count in counts.items()
                        ),
                        key=lambda item: (
                            -item[1],
                            abs(item[0]),
                            item[0],
                        ),
                    )
                    mismatches = tuple(
                        index
                        for index, difference in enumerate(differences)
                        if difference != transposition
                    )
                    if (
                        agreement < config.motif_minimum_length - 1
                        or not mismatches
                        or len(mismatches) > config.motif_maximum_mismatches
                    ):
                        continue
                    matches.append(
                        _MotifMatch(
                            left=left,
                            right=right,
                            transposition=transposition,
                            agreement=agreement,
                            mismatches=mismatches,
                            left_start=left_start,
                            right_start=right_start,
                        )
                    )
        if not matches:
            continue
        match = min(
            matches,
            key=lambda item: (
                -len(item.left),
                len(item.mismatches),
                -item.agreement,
                item.left_start,
                item.right_start,
                abs(item.transposition),
                item.transposition,
            ),
        )
        for mismatch in match.mismatches:
            target = match.right[mismatch]
            expected = match.left[mismatch].pitch + match.transposition
            if (
                not 0 <= expected <= 127
                or expected == target.pitch
                or abs(expected - target.pitch) > 12
            ):
                continue
            confidence = min(
                0.92,
                0.64
                + 0.06 * match.agreement
                - 0.025 * (len(match.mismatches) - 1),
            )
            item = _suggestion(
                clip,
                target,
                SingleSuggestionCategory.MOTIF_INCONSISTENCY,
                confidence,
                (
                    "Possible repeated-motif inconsistency. This "
                    f"position differs from a {len(match.left)}-note rhythmic "
                    "match elsewhere in the same voice; variation may "
                    "be intentional."
                ),
                (expected,),
                config,
                related=(
                    match.left[mismatch].id,
                    *(
                        note.id
                        for note in (*match.left, *match.right)
                        if note.id
                        not in (match.left[mismatch].id, target.id)
                    ),
                ),
            )
            if item is not None:
                suggestions.append(item)
    return tuple(suggestions)


def _deduplicate_and_sort(
    suggestions: Iterable[SingleClipSuggestion],
    maximum: int,
) -> tuple[SingleClipSuggestion, ...]:
    best: dict[str, SingleClipSuggestion] = {}
    for suggestion in suggestions:
        existing = best.get(suggestion.suggestion_id)
        if existing is None or (
            suggestion.confidence,
            tuple(-abs(pitch - suggestion.original_pitch) for pitch in suggestion.alternatives),
        ) > (
            existing.confidence,
            tuple(-abs(pitch - existing.original_pitch) for pitch in existing.alternatives),
        ):
            best[suggestion.suggestion_id] = suggestion
    ordered = sorted(
        best.values(),
        key=lambda suggestion: (
            suggestion.onset_ticks,
            _CATEGORY_ORDER[suggestion.category],
            suggestion.target_note_id,
            suggestion.related_note_ids,
            suggestion.alternatives,
        ),
    )
    return tuple(ordered[:maximum])


def _category_score(
    suggestions: tuple[SingleClipSuggestion, ...],
    category: SingleSuggestionCategory,
) -> float:
    evidence = sum(
        suggestion.confidence
        for suggestion in suggestions
        if suggestion.category is category
    )
    return max(0.0, min(100.0, 100.0 - 24.0 * evidence))


def analyze_single_clip(
    clip: MidiClip,
    *,
    config: SingleAnalysisConfig = DEFAULT_SINGLE_ANALYSIS_CONFIG,
) -> SingleClipAnalysis:
    """Return deterministic, qualified review suggestions for one MIDI clip.

    Chromatic notes, suspensions, passing tones, and intentional tension are
    not removed or declared erroneous.  Short stepwise chromatic connectors
    remain secondary suggestions, while stronger evidence is exposed in the
    primary review list.
    """

    if not isinstance(clip, MidiClip):
        raise TypeError("clip must be a MidiClip")
    if not isinstance(config, SingleAnalysisConfig):
        raise TypeError("config must be a SingleAnalysisConfig")

    key = estimate_key(clip)
    suggestions = _deduplicate_and_sort(
        (
            *_harmonic_suggestions(clip, key, config),
            *_melodic_suggestions(clip, key, config),
            *_voice_leading_suggestions(clip, config),
            *_duplicate_suggestions(clip, key, config),
            *_register_suggestions(clip, config),
            *_bass_suggestions(clip, key, config),
            *_motif_suggestions(clip, config),
        ),
        config.maximum_suggestions,
    )
    scores = (
        _category_score(
            suggestions,
            SingleSuggestionCategory.HARMONIC_CONFLICT,
        ),
        _category_score(
            suggestions,
            SingleSuggestionCategory.MELODIC_LEAP,
        ),
        _category_score(
            suggestions,
            SingleSuggestionCategory.VOICE_LEADING,
        ),
        _category_score(
            suggestions,
            SingleSuggestionCategory.DUPLICATE_OVERLAP,
        ),
        _category_score(
            suggestions,
            SingleSuggestionCategory.REGISTER_CROWDING,
        ),
        _category_score(
            suggestions,
            SingleSuggestionCategory.BASS_CONFLICT,
        ),
        _category_score(
            suggestions,
            SingleSuggestionCategory.MOTIF_INCONSISTENCY,
        ),
    )
    overall = sum(
        score * weight
        for score, weight in zip(
            scores,
            config.component_weights,
            strict=True,
        )
    )
    return SingleClipAnalysis(
        key=key,
        harmonic_score=scores[0],
        melodic_score=scores[1],
        voice_leading_score=scores[2],
        overlap_score=scores[3],
        register_score=scores[4],
        bass_score=scores[5],
        motif_score=scores[6],
        internal_consistency_score=max(0.0, min(100.0, overall)),
        suggestions=suggestions,
        high_confidence_threshold=config.high_confidence_threshold,
        analyzed_clip=clip,
        analysis_config=config,
    )


# A shorter alias is convenient for orchestration code.
analyze_single = analyze_single_clip


__all__ = [
    "analyze_single",
    "analyze_single_clip",
]
