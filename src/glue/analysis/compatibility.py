"""Independently testable compatibility component scorers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from itertools import pairwise
from math import exp, floor, sqrt
from typing import TypeAlias

from glue.models import MidiClip, MidiNote

from .config import DEFAULT_ANALYSIS_CONFIG, AnalysisConfig
from .results import (
    ChordQuality,
    KeyCandidate,
    KeyEstimate,
    LocalHarmonyCandidate,
)

KeyLike: TypeAlias = KeyCandidate | KeyEstimate | None

MAJOR_SCALE_INTERVALS = (0, 2, 4, 5, 7, 9, 11)
MINOR_SCALE_INTERVALS = (0, 2, 3, 5, 7, 8, 10)

# This table is intentionally symmetric.  It is a coarse perceptual prior, not
# an assertion that an interval is always consonant or dissonant in context.
INTERVAL_COMPATIBILITY = (
    1.00,  # unison / octave
    0.15,  # minor second / major seventh
    0.40,  # major second / minor seventh
    0.85,  # minor third / major sixth
    0.90,  # major third / minor sixth
    0.90,  # perfect fourth / fifth
    0.10,  # tritone
    0.90,
    0.90,
    0.85,
    0.40,
    0.15,
)

_EPSILON = 1e-9


@dataclass(frozen=True, slots=True)
class _WeightedNote:
    note: MidiNote
    onset_beat: float
    end_beat: float
    overlap_beats: float
    evidence_weight: float
    attacked: bool


@dataclass(frozen=True, slots=True)
class _ChordTemplate:
    root_pc: int
    pitch_classes: frozenset[int]
    quality: ChordQuality


@dataclass(frozen=True, slots=True)
class _WindowContext:
    start_beat: float
    end_beat: float
    pitched_a: tuple[_WeightedNote, ...]
    pitched_b: tuple[_WeightedNote, ...]
    pitch_classes_a: tuple[float, ...]
    pitch_classes_b: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class _WindowEvidence:
    start_beat: float
    end_beat: float
    segments: tuple[_WindowContext, ...]
    pitched_a: tuple[_WeightedNote, ...]
    pitched_b: tuple[_WeightedNote, ...]
    pitch_classes_a: tuple[float, ...]
    pitch_classes_b: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class _ScoredChord:
    template: _ChordTemplate
    probability: float
    coverage: float
    completeness: float


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, value))


def _clamp_unit_interval(value: float) -> float:
    """Bound a mathematically unit-interval calculation against float drift."""

    return max(0.0, min(1.0, value))


def _resolve_key(key: KeyLike) -> KeyCandidate | None:
    return key.top if isinstance(key, KeyEstimate) else key


def scale_pitch_classes(key: KeyCandidate) -> frozenset[int]:
    """Return the seven pitch classes in a major or natural-minor key.

    Natural minor is a deliberate V0.1 simplification; harmonic and melodic
    minor alterations are not inferred globally.
    """

    intervals = (
        MAJOR_SCALE_INTERVALS if key.mode == "major" else MINOR_SCALE_INTERVALS
    )
    return frozenset((key.tonic_pc + interval) % 12 for interval in intervals)


def _resolve_end_beat(
    clip_a: MidiClip,
    clip_b: MidiClip,
    start_beat: float,
    end_beat: float | None,
) -> float:
    if start_beat < 0:
        raise ValueError("start_beat must be non-negative")
    resolved = (
        max(
            float(clip_a.duration_quarter_notes),
            float(clip_b.duration_quarter_notes),
            start_beat + 1.0,
        )
        if end_beat is None
        else end_beat
    )
    if resolved <= start_beat:
        raise ValueError("end_beat must be greater than start_beat")
    return resolved


def _is_attacked(onset: float, start_beat: float, end_beat: float) -> bool:
    # The epsilon makes a mathematically exact boundary robust to float
    # conversion while retaining half-open window semantics.
    return onset >= start_beat - _EPSILON and onset < end_beat - _EPSILON


def _active_pitched_notes(
    clip: MidiClip,
    start_beat: float,
    end_beat: float,
    config: AnalysisConfig,
) -> tuple[_WeightedNote, ...]:
    weighted: list[_WeightedNote] = []
    for note in clip.notes:
        if note.is_percussion or note.duration_ticks <= 0:
            continue
        onset = note.onset_ticks / clip.ticks_per_beat
        note_end = note.end_ticks / clip.ticks_per_beat
        overlap = min(note_end, end_beat) - max(onset, start_beat)
        if overlap <= _EPSILON:
            continue
        attacked = _is_attacked(onset, start_beat, end_beat)
        on_quarter_downbeat = attacked and abs(onset - round(onset)) <= _EPSILON
        accent = (
            1.0
            + (config.attack_accent if attacked else 0.0)
            + (config.downbeat_accent if on_quarter_downbeat else 0.0)
        )
        # Velocity is a modest accent cue; duration overlap remains dominant.
        velocity_factor = 0.75 + 0.50 * (note.velocity / 127.0)
        weighted.append(
            _WeightedNote(
                note=note,
                onset_beat=onset,
                end_beat=note_end,
                overlap_beats=overlap,
                evidence_weight=overlap * accent * velocity_factor,
                attacked=attacked,
            )
        )
    return tuple(weighted)


def _pitch_class_vector(notes: tuple[_WeightedNote, ...]) -> tuple[float, ...]:
    vector = [0.0] * 12
    for item in notes:
        vector[item.note.pitch % 12] += item.evidence_weight
    return tuple(vector)


def _window_context(
    clip_a: MidiClip,
    clip_b: MidiClip,
    start_beat: float,
    end_beat: float,
    config: AnalysisConfig,
) -> _WindowContext:
    pitched_a = _active_pitched_notes(clip_a, start_beat, end_beat, config)
    pitched_b = _active_pitched_notes(clip_b, start_beat, end_beat, config)
    return _WindowContext(
        start_beat=start_beat,
        end_beat=end_beat,
        pitched_a=pitched_a,
        pitched_b=pitched_b,
        pitch_classes_a=_pitch_class_vector(pitched_a),
        pitch_classes_b=_pitch_class_vector(pitched_b),
    )


def _event_boundaries(
    clip_a: MidiClip,
    clip_b: MidiClip,
    start_beat: float,
    end_beat: float,
    *,
    pitched_only: bool,
) -> tuple[float, ...]:
    boundaries = [start_beat, end_beat]
    for clip in (clip_a, clip_b):
        for note in clip.notes:
            if note.duration_ticks <= 0 or (pitched_only and note.is_percussion):
                continue
            onset = note.onset_ticks / clip.ticks_per_beat
            note_end = note.end_ticks / clip.ticks_per_beat
            if note_end <= start_beat + _EPSILON or onset >= end_beat - _EPSILON:
                continue
            boundaries.extend(
                (
                    max(start_beat, onset),
                    min(end_beat, note_end),
                )
            )

    ordered: list[float] = []
    for boundary in sorted(boundaries):
        if not ordered or boundary - ordered[-1] > _EPSILON:
            ordered.append(boundary)
    return tuple(ordered)


def _combine_segment_notes(
    segments: tuple[_WindowContext, ...],
    *,
    use_clip_a: bool,
) -> tuple[_WeightedNote, ...]:
    combined: dict[int, _WeightedNote] = {}
    for segment in segments:
        notes = segment.pitched_a if use_clip_a else segment.pitched_b
        for item in notes:
            existing = combined.get(item.note.id)
            if existing is None:
                combined[item.note.id] = item
                continue
            combined[item.note.id] = _WeightedNote(
                note=item.note,
                onset_beat=item.onset_beat,
                end_beat=item.end_beat,
                overlap_beats=existing.overlap_beats + item.overlap_beats,
                evidence_weight=existing.evidence_weight + item.evidence_weight,
                attacked=existing.attacked or item.attacked,
            )
    return tuple(
        sorted(
            combined.values(),
            key=lambda item: (
                item.note.onset_ticks,
                item.note.track,
                item.note.id,
            ),
        )
    )


def _sum_pitch_class_vectors(
    segments: tuple[_WindowContext, ...],
    *,
    use_clip_a: bool,
) -> tuple[float, ...]:
    return tuple(
        sum(
            (
                segment.pitch_classes_a
                if use_clip_a
                else segment.pitch_classes_b
            )[pitch_class]
            for segment in segments
        )
        for pitch_class in range(12)
    )


def _window_evidence(
    clip_a: MidiClip,
    clip_b: MidiClip,
    start_beat: float,
    end_beat: float,
    config: AnalysisConfig,
) -> _WindowEvidence:
    segments: list[_WindowContext] = []
    boundaries = _event_boundaries(
        clip_a,
        clip_b,
        start_beat,
        end_beat,
        pitched_only=True,
    )
    for segment_start, segment_end in pairwise(boundaries):
        if segment_end - segment_start <= _EPSILON:
            continue
        context = _window_context(
            clip_a,
            clip_b,
            segment_start,
            segment_end,
            config,
        )
        if context.pitched_a and context.pitched_b:
            segments.append(context)

    resolved_segments = tuple(segments)
    return _WindowEvidence(
        start_beat=start_beat,
        end_beat=end_beat,
        segments=resolved_segments,
        pitched_a=_combine_segment_notes(resolved_segments, use_clip_a=True),
        pitched_b=_combine_segment_notes(resolved_segments, use_clip_a=False),
        pitch_classes_a=_sum_pitch_class_vectors(
            resolved_segments,
            use_clip_a=True,
        ),
        pitch_classes_b=_sum_pitch_class_vectors(
            resolved_segments,
            use_clip_a=False,
        ),
    )


def _segment_weighted_score(
    evidence: _WindowEvidence,
    scorer: Callable[[_WindowContext], float],
) -> float:
    total_duration = sum(
        segment.end_beat - segment.start_beat for segment in evidence.segments
    )
    if total_duration <= _EPSILON:
        return 100.0
    return _clamp_score(
        sum(
            scorer(segment) * (segment.end_beat - segment.start_beat)
            for segment in evidence.segments
        )
        / total_duration
    )


def _has_active_note(
    clip: MidiClip,
    start_beat: float,
    end_beat: float,
) -> bool:
    return any(
        note.duration_ticks > 0
        and note.end_ticks / clip.ticks_per_beat > start_beat + _EPSILON
        and note.onset_ticks / clip.ticks_per_beat < end_beat - _EPSILON
        for note in clip.notes
    )


def _simultaneous_activity_fraction(
    clip_a: MidiClip,
    clip_b: MidiClip,
    start_beat: float,
    end_beat: float,
) -> float:
    """Return the fraction with any positive-duration activity in both clips."""

    boundaries = _event_boundaries(
        clip_a,
        clip_b,
        start_beat,
        end_beat,
        pitched_only=False,
    )
    simultaneous = sum(
        segment_end - segment_start
        for segment_start, segment_end in pairwise(boundaries)
        if _has_active_note(clip_a, segment_start, segment_end)
        and _has_active_note(clip_b, segment_start, segment_end)
    )
    return max(0.0, min(1.0, simultaneous / (end_beat - start_beat)))


def _normalized(vector: tuple[float, ...]) -> tuple[float, ...]:
    total = sum(vector)
    if total <= _EPSILON:
        return tuple(0.0 for _ in vector)
    return tuple(value / total for value in vector)


def _vertical_compatibility(
    pitch_classes_a: tuple[float, ...],
    pitch_classes_b: tuple[float, ...],
) -> float:
    normalized_a = _normalized(pitch_classes_a)
    normalized_b = _normalized(pitch_classes_b)
    if sum(normalized_a) <= _EPSILON or sum(normalized_b) <= _EPSILON:
        return 1.0
    return sum(
        weight_a
        * weight_b
        * INTERVAL_COMPATIBILITY[(pitch_class_b - pitch_class_a) % 12]
        for pitch_class_a, weight_a in enumerate(normalized_a)
        for pitch_class_b, weight_b in enumerate(normalized_b)
    )


_CHORD_QUALITIES: dict[frozenset[int], ChordQuality] = {
    frozenset((0, 4, 7)): "major",
    frozenset((0, 3, 7)): "minor",
    frozenset((0, 3, 6)): "diminished",
    frozenset((0, 4, 8)): "augmented",
    frozenset((0, 4, 7, 11)): "major seventh",
    frozenset((0, 4, 7, 10)): "dominant seventh",
    frozenset((0, 3, 7, 10)): "minor seventh",
    frozenset((0, 3, 6, 10)): "half-diminished seventh",
    frozenset((0, 3, 6, 9)): "diminished seventh",
}


def _chord_quality(
    root_pc: int,
    pitch_classes: frozenset[int],
) -> ChordQuality:
    intervals = frozenset((pitch_class - root_pc) % 12 for pitch_class in pitch_classes)
    return _CHORD_QUALITIES.get(intervals, "other")


def _diatonic_chords(key: KeyCandidate) -> tuple[_ChordTemplate, ...]:
    scale = tuple(
        (key.tonic_pc + interval) % 12
        for interval in (
            MAJOR_SCALE_INTERVALS
            if key.mode == "major"
            else MINOR_SCALE_INTERVALS
        )
    )
    chords: list[_ChordTemplate] = []
    for degree in range(7):
        triad = frozenset(scale[index % 7] for index in (degree, degree + 2, degree + 4))
        seventh = frozenset(
            scale[index % 7]
            for index in (degree, degree + 2, degree + 4, degree + 6)
        )
        chords.append(
            _ChordTemplate(
                root_pc=scale[degree],
                pitch_classes=triad,
                quality=_chord_quality(scale[degree], triad),
            )
        )
        chords.append(
            _ChordTemplate(
                root_pc=scale[degree],
                pitch_classes=seventh,
                quality=_chord_quality(scale[degree], seventh),
            )
        )
    return tuple(chords)


def _scored_chords(
    pitch_classes: tuple[float, ...],
    chords: tuple[_ChordTemplate, ...],
    config: AnalysisConfig,
) -> tuple[_ScoredChord, ...]:
    normalized = _normalized(pitch_classes)
    if sum(normalized) <= _EPSILON:
        probability = 1.0 / len(chords)
        return tuple(
            _ScoredChord(
                template=chord,
                probability=probability,
                coverage=0.0,
                completeness=0.0,
            )
            for chord in chords
        )

    observed = frozenset(
        pitch_class
        for pitch_class, weight in enumerate(pitch_classes)
        if weight > _EPSILON
    )
    likelihoods = []
    evidence: list[tuple[float, float]] = []
    for chord in chords:
        # This is mathematically at most one, but ordinary humanized velocity
        # weights can make the floating-point sum 1.0000000000000002.
        coverage = _clamp_unit_interval(
            sum(normalized[pitch_class] for pitch_class in chord.pitch_classes)
        )
        completeness = len(observed & chord.pitch_classes) / len(chord.pitch_classes)
        root_mass = normalized[chord.root_pc]
        likelihoods.append(
            exp(
                config.chord_coverage_weight * coverage
                + config.chord_completeness_weight * completeness
                + config.chord_root_weight * root_mass
            )
        )
        evidence.append((coverage, completeness))
    total = sum(likelihoods)
    return tuple(
        _ScoredChord(
            template=chord,
            probability=likelihood / total,
            coverage=coverage,
            completeness=completeness,
        )
        for chord, likelihood, (coverage, completeness) in zip(
            chords,
            likelihoods,
            evidence,
            strict=True,
        )
    )


def _local_harmony_candidates(
    pitch_classes: tuple[float, ...],
    key: KeyCandidate | None,
    config: AnalysisConfig,
) -> tuple[LocalHarmonyCandidate, ...]:
    if key is None or sum(pitch_classes) <= _EPSILON:
        return ()
    scored = _scored_chords(pitch_classes, _diatonic_chords(key), config)
    if max(item.coverage for item in scored) <= _EPSILON:
        return ()
    ranked = sorted(
        scored,
        key=lambda item: (
            -item.probability,
            -item.coverage,
            -item.completeness,
            len(item.template.pitch_classes),
            item.template.root_pc,
            item.template.quality,
        ),
    )
    return tuple(
        LocalHarmonyCandidate(
            root_pc=item.template.root_pc,
            quality=item.template.quality,
            pitch_classes=tuple(sorted(item.template.pitch_classes)),
            probability=item.probability,
            coverage=item.coverage,
            completeness=item.completeness,
        )
        for item in ranked[: config.local_harmony_candidate_count]
    )


def infer_local_harmony_candidates(
    clip: MidiClip,
    key: KeyLike,
    *,
    start_beat: float = 0.0,
    end_beat: float | None = None,
    config: AnalysisConfig = DEFAULT_ANALYSIS_CONFIG,
) -> tuple[LocalHarmonyCandidate, ...]:
    """Return ranked, qualified local chord interpretations for one clip."""

    if start_beat < 0:
        raise ValueError("start_beat must be non-negative")
    resolved_end = (
        max(float(clip.duration_quarter_notes), start_beat + 1.0)
        if end_beat is None
        else end_beat
    )
    if resolved_end <= start_beat:
        raise ValueError("end_beat must be greater than start_beat")
    notes = _active_pitched_notes(clip, start_beat, resolved_end, config)
    return _local_harmony_candidates(
        _pitch_class_vector(notes),
        _resolve_key(key),
        config,
    )


def _joint_chord_fit(
    pitch_classes_a: tuple[float, ...],
    pitch_classes_b: tuple[float, ...],
    chords: tuple[_ChordTemplate, ...],
) -> float:
    union = tuple(
        left + right
        for left, right in zip(
            pitch_classes_a,
            pitch_classes_b,
            strict=True,
        )
    )
    normalized = _normalized(union)
    if sum(normalized) <= _EPSILON:
        return 1.0
    return _clamp_unit_interval(
        max(
            sum(normalized[pitch_class] for pitch_class in chord.pitch_classes)
            for chord in chords
        )
    )


def _harmonic_from_context(
    context: _WindowContext,
    key: KeyCandidate | None,
    config: AnalysisConfig,
) -> float:
    if not context.pitched_a or not context.pitched_b:
        return 100.0

    vertical = _vertical_compatibility(
        context.pitch_classes_a,
        context.pitch_classes_b,
    )
    if key is None:
        return _clamp_score(vertical * 100.0)

    scale = scale_pitch_classes(key)
    total_evidence = sum(context.pitch_classes_a) + sum(context.pitch_classes_b)
    in_scale_evidence = sum(
        context.pitch_classes_a[pitch_class] + context.pitch_classes_b[pitch_class]
        for pitch_class in scale
    )
    scale_fit = (
        in_scale_evidence / total_evidence if total_evidence > _EPSILON else 1.0
    )
    chords = _diatonic_chords(key)
    distribution_a = _scored_chords(context.pitch_classes_a, chords, config)
    distribution_b = _scored_chords(context.pitch_classes_b, chords, config)
    chord_agreement = sum(
        sqrt(left.probability * right.probability)
        for left, right in zip(distribution_a, distribution_b, strict=True)
    )
    joint_fit = _joint_chord_fit(
        context.pitch_classes_a,
        context.pitch_classes_b,
        chords,
    )
    return _clamp_score(
        100.0
        * (
            config.harmonic_vertical_weight * vertical
            + config.harmonic_scale_weight * scale_fit
            + config.harmonic_chord_agreement_weight * chord_agreement
            + config.harmonic_joint_fit_weight * joint_fit
        )
    )


def score_harmonic_compatibility(
    clip_a: MidiClip,
    clip_b: MidiClip,
    key: KeyLike = None,
    *,
    start_beat: float = 0.0,
    end_beat: float | None = None,
    config: AnalysisConfig = DEFAULT_ANALYSIS_CONFIG,
) -> float:
    """Score pitch-class, scale, and inferred local-chord compatibility."""

    resolved_end = _resolve_end_beat(clip_a, clip_b, start_beat, end_beat)
    evidence = _window_evidence(
        clip_a,
        clip_b,
        start_beat,
        resolved_end,
        config,
    )
    resolved_key = _resolve_key(key)
    return _segment_weighted_score(
        evidence,
        lambda context: _harmonic_from_context(context, resolved_key, config),
    )


def _lowest_note(notes: tuple[_WeightedNote, ...]) -> _WeightedNote:
    return min(
        notes,
        key=lambda item: (
            item.note.pitch,
            -item.overlap_beats,
            item.note.onset_ticks,
            item.note.id,
        ),
    )


def _expected_bass_support(
    bass_pc: int,
    key: KeyCandidate,
    chords: tuple[_ChordTemplate, ...],
    distribution: tuple[_ScoredChord, ...],
) -> float:
    scale = scale_pitch_classes(key)
    expected = 0.0
    for chord, scored in zip(chords, distribution, strict=True):
        if bass_pc == chord.root_pc:
            support = 1.0
        elif (bass_pc - chord.root_pc) % 12 == 7:
            support = 0.90
        elif bass_pc in chord.pitch_classes:
            support = 0.82
        elif bass_pc in scale:
            support = 0.55
        else:
            support = 0.20
        expected += scored.probability * support
    return expected


def _bass_from_context(
    context: _WindowContext,
    key: KeyCandidate | None,
    config: AnalysisConfig,
) -> float:
    if not context.pitched_a or not context.pitched_b:
        return 100.0

    bass_a = _lowest_note(context.pitched_a).note.pitch % 12
    bass_b = _lowest_note(context.pitched_b).note.pitch % 12
    interval = INTERVAL_COMPATIBILITY[(bass_b - bass_a) % 12]
    if key is None:
        return _clamp_score(interval * 100.0)

    chords = _diatonic_chords(key)
    union = tuple(
        left + right
        for left, right in zip(
            context.pitch_classes_a,
            context.pitch_classes_b,
            strict=True,
        )
    )
    distribution = _scored_chords(union, chords, config)
    support_a = _expected_bass_support(bass_a, key, chords, distribution)
    support_b = _expected_bass_support(bass_b, key, chords, distribution)
    return _clamp_score(
        100.0 * (0.50 * interval + 0.25 * support_a + 0.25 * support_b)
    )


def score_bass_compatibility(
    clip_a: MidiClip,
    clip_b: MidiClip,
    key: KeyLike = None,
    *,
    start_beat: float = 0.0,
    end_beat: float | None = None,
    config: AnalysisConfig = DEFAULT_ANALYSIS_CONFIG,
) -> float:
    """Score the two lowest active pitches with probabilistic root support."""

    resolved_end = _resolve_end_beat(clip_a, clip_b, start_beat, end_beat)
    evidence = _window_evidence(
        clip_a,
        clip_b,
        start_beat,
        resolved_end,
        config,
    )
    resolved_key = _resolve_key(key)
    return _segment_weighted_score(
        evidence,
        lambda context: _bass_from_context(context, resolved_key, config),
    )


def _representative_bass_pitch(
    evidence: _WindowEvidence,
    *,
    use_clip_a: bool,
) -> int | None:
    durations: dict[int, float] = {}
    for segment in evidence.segments:
        notes = segment.pitched_a if use_clip_a else segment.pitched_b
        if not notes:
            continue
        pitch = _lowest_note(notes).note.pitch
        durations[pitch] = (
            durations.get(pitch, 0.0)
            + segment.end_beat
            - segment.start_beat
        )
    if not durations:
        return None
    return min(durations, key=lambda pitch: (-durations[pitch], pitch))


def _absolute_pitch_distribution(
    notes: tuple[_WeightedNote, ...],
) -> dict[int, float]:
    weights: dict[int, float] = {}
    for item in notes:
        weights[item.note.pitch] = (
            weights.get(item.note.pitch, 0.0) + item.evidence_weight
        )
    total = sum(weights.values())
    if total <= _EPSILON:
        return {}
    return {pitch: weight / total for pitch, weight in weights.items()}


def _register_proximity(distance: int) -> float:
    if distance <= 2:
        return 1.0
    if distance <= 5:
        return 0.75
    if distance <= 9:
        return 0.35
    if distance <= 12:
        return 0.10
    return 0.0


def _register_from_context(context: _WindowContext) -> float:
    distribution_a = _absolute_pitch_distribution(context.pitched_a)
    distribution_b = _absolute_pitch_distribution(context.pitched_b)
    if not distribution_a or not distribution_b:
        return 100.0

    proximity = sum(
        weight_a * weight_b * _register_proximity(abs(pitch_a - pitch_b))
        for pitch_a, weight_a in distribution_a.items()
        for pitch_b, weight_b in distribution_b.items()
    )
    crowding = max(
        0.0,
        min(1.0, (len(distribution_a) + len(distribution_b) - 2) / 4.0),
    )
    return _clamp_score(100.0 * (1.0 - proximity * crowding))


def score_register_compatibility(
    clip_a: MidiClip,
    clip_b: MidiClip,
    *,
    start_beat: float = 0.0,
    end_beat: float | None = None,
    config: AnalysisConfig = DEFAULT_ANALYSIS_CONFIG,
) -> float:
    """Score dense simultaneous occupation of nearby absolute registers."""

    resolved_end = _resolve_end_beat(clip_a, clip_b, start_beat, end_beat)
    evidence = _window_evidence(
        clip_a,
        clip_b,
        start_beat,
        resolved_end,
        config,
    )
    return _segment_weighted_score(evidence, _register_from_context)


def _attack_bins(
    clip: MidiClip,
    start_beat: float,
    end_beat: float,
    subdivisions: int,
) -> tuple[int, ...]:
    bins = [0] * subdivisions
    window_length = end_beat - start_beat
    for note in clip.notes:
        onset = note.onset_ticks / clip.ticks_per_beat
        if not _is_attacked(onset, start_beat, end_beat):
            continue
        relative = (onset - start_beat) / window_length
        index = max(0, min(subdivisions - 1, floor(relative * subdivisions)))
        bins[index] += 1
    return tuple(bins)


def _rhythm_score(
    clip_a: MidiClip,
    clip_b: MidiClip,
    start_beat: float,
    end_beat: float,
    config: AnalysisConfig,
) -> float:
    attacks_a = _attack_bins(
        clip_a,
        start_beat,
        end_beat,
        config.rhythm_subdivisions,
    )
    attacks_b = _attack_bins(
        clip_b,
        start_beat,
        end_beat,
        config.rhythm_subdivisions,
    )
    total_a = sum(attacks_a)
    total_b = sum(attacks_b)
    if not total_a or not total_b:
        return 100.0
    coincidence = sum(
        min(left, right)
        for left, right in zip(attacks_a, attacks_b, strict=True)
    ) / min(total_a, total_b)
    density_gate = max(0.0, min(1.0, (total_a + total_b - 2) / 6.0))
    return _clamp_score(100.0 * (1.0 - coincidence * density_gate))


def score_rhythm_compatibility(
    clip_a: MidiClip,
    clip_b: MidiClip,
    *,
    start_beat: float = 0.0,
    end_beat: float | None = None,
    config: AnalysisConfig = DEFAULT_ANALYSIS_CONFIG,
) -> float:
    """Score dense note-attack competition, including percussion attacks."""

    resolved_end = _resolve_end_beat(clip_a, clip_b, start_beat, end_beat)
    return _rhythm_score(clip_a, clip_b, start_beat, resolved_end, config)


def _score_components(
    clip_a: MidiClip,
    clip_b: MidiClip,
    key: KeyCandidate | None,
    start_beat: float,
    end_beat: float,
    config: AnalysisConfig,
) -> tuple[float, float, float, float, _WindowEvidence]:
    """Score all components while sharing the expensive window evidence."""

    evidence = _window_evidence(clip_a, clip_b, start_beat, end_beat, config)
    return (
        _segment_weighted_score(
            evidence,
            lambda context: _harmonic_from_context(context, key, config),
        ),
        _segment_weighted_score(
            evidence,
            lambda context: _bass_from_context(context, key, config),
        ),
        _segment_weighted_score(evidence, _register_from_context),
        _rhythm_score(clip_a, clip_b, start_beat, end_beat, config),
        evidence,
    )
