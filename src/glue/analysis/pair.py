"""Windowed pair analysis and interpretable score aggregation."""

from __future__ import annotations

from itertools import pairwise
from math import sqrt

from glue.models import DEFAULT_TIME_SIGNATURE, MidiClip

from .compatibility import (
    _EPSILON,
    KeyLike,
    _attack_bins,
    _resolve_end_beat,
    _resolve_key,
    _score_components,
    _WindowContext,
    scale_pitch_classes,
)
from .config import DEFAULT_ANALYSIS_CONFIG, AnalysisConfig
from .key import estimate_combined_key, estimate_key
from .results import (
    PITCH_CLASS_NAMES,
    BarAnalysis,
    ConflictReason,
    KeyCandidate,
    PairAnalysis,
    WindowAnalysis,
)


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, value))


def _pitch_class_summary(vector: tuple[float, ...]) -> str:
    ranked = sorted(
        (
            (weight, pitch_class)
            for pitch_class, weight in enumerate(vector)
            if weight > _EPSILON
        ),
        key=lambda item: (-item[0], item[1]),
    )
    return "/".join(PITCH_CLASS_NAMES[pitch_class] for _, pitch_class in ranked[:3]) or "none"


def _midi_pitch_label(pitch: int) -> str:
    octave = pitch // 12 - 1
    return f"{PITCH_CLASS_NAMES[pitch % 12]}{octave}"


def _reason_for_harmony(
    score: float,
    index: int,
    context: _WindowContext,
    key: KeyCandidate | None,
) -> ConflictReason:
    if key is not None:
        scale = scale_pitch_classes(key)
        outside = sorted(
            {
                pitch_class
                for pitch_class in range(12)
                if pitch_class not in scale
                and (
                    context.pitch_classes_a[pitch_class]
                    + context.pitch_classes_b[pitch_class]
                )
                > _EPSILON
            }
        )
    else:
        outside = []
    if outside:
        pitch_names = ", ".join(PITCH_CLASS_NAMES[pitch_class] for pitch_class in outside)
        detail = (
            f"{pitch_names} fall outside the estimated {key.label}; "
            "the key estimate may itself be ambiguous"
        )
    else:
        detail = (
            f"local pitch groups {_pitch_class_summary(context.pitch_classes_a)} and "
            f"{_pitch_class_summary(context.pitch_classes_b)} imply different harmony"
        )
    message = (
        f"Beats {context.start_beat:.2f}-{context.end_beat:.2f}: possible harmonic "
        f"tension ({score:.1f}/100); {detail}."
    )
    return ConflictReason("harmonic", score, index, message)


def _reason_for_bass(
    score: float,
    index: int,
    context: _WindowContext,
) -> ConflictReason:
    lowest_a = min(item.note.pitch for item in context.pitched_a)
    lowest_b = min(item.note.pitch for item in context.pitched_b)
    message = (
        f"Beats {context.start_beat:.2f}-{context.end_beat:.2f}: lowest active notes "
        f"{_midi_pitch_label(lowest_a)} and {_midi_pitch_label(lowest_b)} provide "
        f"uncertain shared-root support ({score:.1f}/100)."
    )
    return ConflictReason("bass", score, index, message)


def _reason_for_register(
    score: float,
    index: int,
    context: _WindowContext,
) -> ConflictReason:
    pitches_a = [item.note.pitch for item in context.pitched_a]
    pitches_b = [item.note.pitch for item in context.pitched_b]
    message = (
        f"Beats {context.start_beat:.2f}-{context.end_beat:.2f}: possible register "
        f"crowding between {_midi_pitch_label(min(pitches_a))}-"
        f"{_midi_pitch_label(max(pitches_a))} and {_midi_pitch_label(min(pitches_b))}-"
        f"{_midi_pitch_label(max(pitches_b))} ({score:.1f}/100)."
    )
    return ConflictReason("register", score, index, message)


def _reason_for_rhythm(
    score: float,
    index: int,
    clip_a: MidiClip,
    clip_b: MidiClip,
    context: _WindowContext,
    config: AnalysisConfig,
) -> ConflictReason:
    bins_a = _attack_bins(
        clip_a,
        context.start_beat,
        context.end_beat,
        config.rhythm_subdivisions,
    )
    bins_b = _attack_bins(
        clip_b,
        context.start_beat,
        context.end_beat,
        config.rhythm_subdivisions,
    )
    coincident = sum(
        min(left, right) for left, right in zip(bins_a, bins_b, strict=True)
    )
    message = (
        f"Beats {context.start_beat:.2f}-{context.end_beat:.2f}: {coincident} "
        f"dense attacks share timing bins, suggesting possible rhythmic competition "
        f"({score:.1f}/100)."
    )
    return ConflictReason("rhythm", score, index, message)


def _window_reasons(
    scores: tuple[float, float, float, float],
    index: int,
    clip_a: MidiClip,
    clip_b: MidiClip,
    context: _WindowContext,
    key: KeyCandidate | None,
    config: AnalysisConfig,
) -> tuple[ConflictReason, ...]:
    harmonic, bass, register, rhythm = scores
    reasons: list[ConflictReason] = []
    if harmonic < config.reason_threshold and context.pitched_a and context.pitched_b:
        reasons.append(_reason_for_harmony(harmonic, index, context, key))
    if bass < config.reason_threshold and context.pitched_a and context.pitched_b:
        reasons.append(_reason_for_bass(bass, index, context))
    if register < config.reason_threshold and context.pitched_a and context.pitched_b:
        reasons.append(_reason_for_register(register, index, context))
    if rhythm < config.reason_threshold:
        reasons.append(
            _reason_for_rhythm(
                rhythm,
                index,
                clip_a,
                clip_b,
                context,
                config,
            )
        )
    return tuple(sorted(reasons, key=lambda reason: (reason.score, reason.component)))


def _activity_fraction(
    clip: MidiClip,
    start_beat: float,
    end_beat: float,
) -> float:
    window_length = end_beat - start_beat
    active_duration = 0.0
    for note in clip.notes:
        onset = note.onset_ticks / clip.ticks_per_beat
        note_end = note.end_ticks / clip.ticks_per_beat
        active_duration += max(
            0.0,
            min(note_end, end_beat) - max(onset, start_beat),
        )
    return min(1.0, active_duration / window_length)


def _activity_weight(
    clip_a: MidiClip,
    clip_b: MidiClip,
    start_beat: float,
    end_beat: float,
) -> float:
    """Weight only windows in which both clips provide musical activity.

    Percussion durations are included so percussion-only rhythm comparisons
    remain represented in the aggregate score.
    """

    fraction_a = _activity_fraction(clip_a, start_beat, end_beat)
    fraction_b = _activity_fraction(clip_b, start_beat, end_beat)
    return sqrt(fraction_a * fraction_b)


def analyze_window(
    clip_a: MidiClip,
    clip_b: MidiClip,
    key: KeyLike = None,
    *,
    start_beat: float = 0.0,
    end_beat: float | None = None,
    index: int = 0,
    bar_index: int = 0,
    config: AnalysisConfig = DEFAULT_ANALYSIS_CONFIG,
) -> WindowAnalysis:
    """Analyze one half-open musical-time window."""

    if index < 0 or bar_index < 0:
        raise ValueError("index and bar_index must be non-negative")
    resolved_end = _resolve_end_beat(clip_a, clip_b, start_beat, end_beat)
    resolved_key = _resolve_key(key)
    harmonic, bass, register, rhythm, context = _score_components(
        clip_a,
        clip_b,
        resolved_key,
        start_beat,
        resolved_end,
        config,
    )
    overall = _clamp_score(
        harmonic * config.harmonic_weight
        + bass * config.bass_weight
        + register * config.register_weight
        + rhythm * config.rhythm_weight
    )
    scores = (harmonic, bass, register, rhythm)
    return WindowAnalysis(
        index=index,
        start_beat=start_beat,
        end_beat=resolved_end,
        harmonic_score=harmonic,
        bass_score=bass,
        register_score=register,
        rhythm_score=rhythm,
        overall_score=overall,
        activity_weight=_activity_weight(
            clip_a,
            clip_b,
            start_beat,
            resolved_end,
        ),
        reasons=_window_reasons(
            scores,
            index,
            clip_a,
            clip_b,
            context,
            resolved_key,
            config,
        ),
        bar_index=bar_index,
    )


def _meter_reference(clip_a: MidiClip, clip_b: MidiClip) -> MidiClip:
    # Clip A is the deterministic authority if both provide contradictory
    # meters.  V0.1 reports compatibility; it does not realign meter maps.
    return clip_a if clip_a.time_signature_changes else clip_b


def _bar_spans(
    clip_a: MidiClip,
    clip_b: MidiClip,
    analysis_end: float,
) -> tuple[tuple[float, float], ...]:
    if analysis_end <= _EPSILON:
        return ()
    reference = _meter_reference(clip_a, clip_b)
    changes_by_beat: dict[float, tuple[int, int]] = {}
    for change in reference.time_signature_changes:
        changes_by_beat[change.tick / reference.ticks_per_beat] = (
            change.numerator,
            change.denominator,
        )
    changes = sorted(changes_by_beat.items())
    signature = DEFAULT_TIME_SIGNATURE
    change_index = 0
    while change_index < len(changes) and changes[change_index][0] <= _EPSILON:
        signature = changes[change_index][1]
        change_index += 1

    spans: list[tuple[float, float]] = []
    cursor = 0.0
    while cursor < analysis_end - _EPSILON:
        while (
            change_index < len(changes)
            and changes[change_index][0] <= cursor + _EPSILON
        ):
            signature = changes[change_index][1]
            change_index += 1
        bar_length = signature[0] * 4.0 / signature[1]
        bar_end = min(cursor + bar_length, analysis_end)
        if change_index < len(changes):
            next_change = changes[change_index][0]
            if cursor + _EPSILON < next_change < bar_end - _EPSILON:
                bar_end = next_change
        spans.append((cursor, bar_end))
        cursor = bar_end
    return tuple(spans)


def _bar_index_at(start_beat: float, spans: tuple[tuple[float, float], ...]) -> int:
    for index, (bar_start, bar_end) in enumerate(spans):
        if bar_start - _EPSILON <= start_beat < bar_end - _EPSILON:
            return index
    return max(0, len(spans) - 1)


def _window_spans(
    analysis_end: float,
    window_beats: float,
    bar_spans: tuple[tuple[float, float], ...],
) -> tuple[tuple[float, float], ...]:
    """Return regular analysis windows split at notated bar boundaries."""

    if analysis_end <= _EPSILON:
        return ()

    boundaries = [0.0, analysis_end]
    regular_boundary = window_beats
    while regular_boundary < analysis_end - _EPSILON:
        boundaries.append(regular_boundary)
        regular_boundary += window_beats
    for bar_start, bar_end in bar_spans:
        if _EPSILON < bar_start < analysis_end - _EPSILON:
            boundaries.append(bar_start)
        if _EPSILON < bar_end < analysis_end - _EPSILON:
            boundaries.append(bar_end)

    ordered: list[float] = []
    for boundary in sorted(boundaries):
        if not ordered or boundary - ordered[-1] > _EPSILON:
            ordered.append(boundary)
    return tuple(
        (start, end)
        for start, end in pairwise(ordered)
        if end - start > _EPSILON
    )


def _weighted_average(
    windows: tuple[WindowAnalysis, ...],
    attribute: str,
) -> float:
    total_weight = sum(window.activity_weight for window in windows)
    if total_weight <= _EPSILON:
        return 100.0
    return _clamp_score(
        sum(
            getattr(window, attribute) * window.activity_weight for window in windows
        )
        / total_weight
    )


def _bar_analyses(
    spans: tuple[tuple[float, float], ...],
    windows: tuple[WindowAnalysis, ...],
) -> tuple[BarAnalysis, ...]:
    bars: list[BarAnalysis] = []
    for index, (start, end) in enumerate(spans):
        members = tuple(window for window in windows if window.bar_index == index)
        bars.append(
            BarAnalysis(
                index=index,
                start_beat=start,
                end_beat=end,
                overall_score=_weighted_average(members, "overall_score"),
                window_indices=tuple(window.index for window in members),
            )
        )
    return tuple(bars)


def analyze_pair(
    clip_a: MidiClip,
    clip_b: MidiClip,
    *,
    config: AnalysisConfig = DEFAULT_ANALYSIS_CONFIG,
) -> PairAnalysis:
    """Analyze two clips without modifying either source.

    Scores are transparent heuristics from 0 to 100.  A score of 100 for clips
    with no overlapping active window means "no detected clash", not proof of
    musical compatibility.
    """

    key_a = estimate_key(clip_a)
    key_b = estimate_key(clip_b)
    combined_key = estimate_combined_key(clip_a, clip_b)
    analysis_end = max(
        float(clip_a.duration_quarter_notes),
        float(clip_b.duration_quarter_notes),
    )
    spans = _bar_spans(clip_a, clip_b, analysis_end)
    analysis_spans = _window_spans(analysis_end, config.window_beats, spans)
    windows_list: list[WindowAnalysis] = []
    for index, (start, end) in enumerate(analysis_spans):
        windows_list.append(
            analyze_window(
                clip_a,
                clip_b,
                combined_key,
                start_beat=start,
                end_beat=end,
                index=index,
                bar_index=_bar_index_at(start, spans),
                config=config,
            )
        )
    windows = tuple(windows_list)
    harmonic = _weighted_average(windows, "harmonic_score")
    bass = _weighted_average(windows, "bass_score")
    register = _weighted_average(windows, "register_score")
    rhythm = _weighted_average(windows, "rhythm_score")
    overall = _clamp_score(
        harmonic * config.harmonic_weight
        + bass * config.bass_weight
        + register * config.register_weight
        + rhythm * config.rhythm_weight
    )
    reasons = tuple(
        sorted(
            (reason for window in windows for reason in window.reasons),
            key=lambda reason: (
                reason.score,
                reason.window_index,
                reason.component,
            ),
        )[: config.maximum_reasons]
    )
    return PairAnalysis(
        key_a=key_a,
        key_b=key_b,
        combined_key=combined_key,
        harmonic_score=harmonic,
        bass_score=bass,
        register_score=register,
        rhythm_score=rhythm,
        overall_score=overall,
        windows=windows,
        reasons=reasons,
        bars=_bar_analyses(spans, windows),
    )


analyze_compatibility = analyze_pair
