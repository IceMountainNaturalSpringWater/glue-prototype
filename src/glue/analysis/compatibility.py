"""Independently testable compatibility component scorers."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, floor, sqrt
from typing import TypeAlias

from glue.models import MidiClip, MidiNote

from .config import DEFAULT_ANALYSIS_CONFIG, AnalysisConfig
from .results import KeyCandidate, KeyEstimate

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
class _ChordCandidate:
    root_pc: int
    pitch_classes: frozenset[int]


@dataclass(frozen=True, slots=True)
class _WindowContext:
    start_beat: float
    end_beat: float
    pitched_a: tuple[_WeightedNote, ...]
    pitched_b: tuple[_WeightedNote, ...]
    pitch_classes_a: tuple[float, ...]
    pitch_classes_b: tuple[float, ...]


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, value))


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


def _diatonic_chords(key: KeyCandidate) -> tuple[_ChordCandidate, ...]:
    scale = tuple(
        (key.tonic_pc + interval) % 12
        for interval in (
            MAJOR_SCALE_INTERVALS
            if key.mode == "major"
            else MINOR_SCALE_INTERVALS
        )
    )
    chords: list[_ChordCandidate] = []
    for degree in range(7):
        triad = frozenset(scale[index % 7] for index in (degree, degree + 2, degree + 4))
        seventh = frozenset(
            scale[index % 7]
            for index in (degree, degree + 2, degree + 4, degree + 6)
        )
        chords.append(_ChordCandidate(root_pc=scale[degree], pitch_classes=triad))
        chords.append(_ChordCandidate(root_pc=scale[degree], pitch_classes=seventh))
    return tuple(chords)


def _chord_distribution(
    pitch_classes: tuple[float, ...],
    chords: tuple[_ChordCandidate, ...],
) -> tuple[float, ...]:
    normalized = _normalized(pitch_classes)
    if sum(normalized) <= _EPSILON:
        return tuple(1.0 / len(chords) for _ in chords)
    likelihoods = []
    for chord in chords:
        coverage = sum(normalized[pitch_class] for pitch_class in chord.pitch_classes)
        # Equivalent to exp(4*coverage - 3*(1-coverage)); the shared exp(-3)
        # is omitted because normalization cancels it.
        likelihoods.append(exp(7.0 * coverage))
    total = sum(likelihoods)
    return tuple(value / total for value in likelihoods)


def _harmonic_from_context(
    context: _WindowContext,
    key: KeyCandidate | None,
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
    distribution_a = _chord_distribution(context.pitch_classes_a, chords)
    distribution_b = _chord_distribution(context.pitch_classes_b, chords)
    chord_agreement = sum(
        sqrt(left * right)
        for left, right in zip(distribution_a, distribution_b, strict=True)
    )
    return _clamp_score(
        100.0 * (0.50 * vertical + 0.30 * scale_fit + 0.20 * chord_agreement)
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
    context = _window_context(clip_a, clip_b, start_beat, resolved_end, config)
    return _harmonic_from_context(context, _resolve_key(key))


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
    chords: tuple[_ChordCandidate, ...],
    distribution: tuple[float, ...],
) -> float:
    scale = scale_pitch_classes(key)
    expected = 0.0
    for chord, probability in zip(chords, distribution, strict=True):
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
        expected += probability * support
    return expected


def _bass_from_context(
    context: _WindowContext,
    key: KeyCandidate | None,
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
    distribution = _chord_distribution(union, chords)
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
    context = _window_context(clip_a, clip_b, start_beat, resolved_end, config)
    return _bass_from_context(context, _resolve_key(key))


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
    context = _window_context(clip_a, clip_b, start_beat, resolved_end, config)
    return _register_from_context(context)


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
) -> tuple[float, float, float, float, _WindowContext]:
    """Score all components while sharing the expensive window evidence."""

    context = _window_context(clip_a, clip_b, start_beat, end_beat, config)
    return (
        _harmonic_from_context(context, key),
        _bass_from_context(context, key),
        _register_from_context(context),
        _rhythm_score(clip_a, clip_b, start_beat, end_beat, config),
        context,
    )
