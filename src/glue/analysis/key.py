"""Deterministic duration-weighted major/minor key estimation."""

from __future__ import annotations

from collections.abc import Iterable
from math import sqrt

from glue.models import MidiClip

from .results import KeyCandidate, KeyEstimate

# Krumhansl-Kessler probe-tone profiles.  They are intentionally constants:
# V0.1 reports a heuristic match and its ambiguity rather than learned truth.
MAJOR_PROFILE = (
    6.35,
    2.23,
    3.48,
    2.33,
    4.38,
    4.09,
    2.52,
    5.19,
    2.39,
    3.66,
    2.29,
    2.88,
)
MINOR_PROFILE = (
    6.33,
    2.68,
    3.52,
    5.38,
    2.60,
    3.53,
    2.54,
    4.75,
    3.98,
    2.69,
    3.34,
    3.17,
)


def duration_weighted_histogram(clips: Iterable[MidiClip]) -> tuple[float, ...]:
    """Return a 12-bin pitch-class histogram weighted by quarter-note duration.

    General MIDI channel 10 (zero-based channel 9) is percussion by convention,
    so it is omitted from pitched analysis.  Zero-duration notes provide no
    tonal evidence.
    """

    histogram = [0.0] * 12
    for clip in clips:
        for note in clip.notes:
            if note.is_percussion or note.duration_ticks <= 0:
                continue
            duration_beats = note.duration_ticks / clip.ticks_per_beat
            histogram[note.pitch % 12] += duration_beats
    return tuple(histogram)


def _pearson_correlation(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    left_centered = tuple(value - left_mean for value in left)
    right_centered = tuple(value - right_mean for value in right)
    denominator = sqrt(
        sum(value * value for value in left_centered)
        * sum(value * value for value in right_centered)
    )
    if denominator <= 1e-12:
        return 0.0
    value = sum(a * b for a, b in zip(left_centered, right_centered, strict=True))
    return max(-1.0, min(1.0, value / denominator))


def _rotated_profile(profile: tuple[float, ...], tonic_pc: int) -> tuple[float, ...]:
    return tuple(profile[(pitch_class - tonic_pc) % 12] for pitch_class in range(12))


def estimate_key_from_histogram(
    histogram: tuple[float, ...],
    *,
    candidate_count: int = 5,
) -> KeyEstimate:
    """Estimate a key from a duration histogram.

    Confidence is a deliberately conservative margin measure.  It is reduced
    for material containing fewer than five distinct pitch classes, because a
    sustained single pitch should not be presented as a certain key.
    """

    if len(histogram) != 12:
        raise ValueError("histogram must contain exactly 12 pitch classes")
    if candidate_count <= 0:
        raise ValueError("candidate_count must be positive")
    if any(value < 0 for value in histogram):
        raise ValueError("histogram weights must be non-negative")
    if sum(histogram) <= 1e-12 or max(histogram) - min(histogram) <= 1e-12:
        return KeyEstimate.unknown()

    ranked: list[KeyCandidate] = []
    for mode, profile in (("major", MAJOR_PROFILE), ("minor", MINOR_PROFILE)):
        for tonic_pc in range(12):
            correlation = _pearson_correlation(
                histogram,
                _rotated_profile(profile, tonic_pc),
            )
            ranked.append(
                KeyCandidate(
                    tonic_pc=tonic_pc,
                    mode=mode,
                    correlation=correlation,
                )
            )

    mode_order = {"major": 0, "minor": 1}
    ranked.sort(
        key=lambda item: (
            -item.correlation,
            mode_order[item.mode],
            item.tonic_pc,
        )
    )
    margin = max(0.0, ranked[0].correlation - ranked[1].correlation)
    distinct_pitch_classes = sum(value > 1e-12 for value in histogram)
    evidence_factor = min(1.0, distinct_pitch_classes / 5.0)
    confidence = min(1.0, margin / 0.25) * evidence_factor
    return KeyEstimate(
        candidates=tuple(ranked[: min(candidate_count, len(ranked))]),
        confidence=confidence,
    )


def estimate_key(clip: MidiClip, *, candidate_count: int = 5) -> KeyEstimate:
    """Estimate the global major/minor key of one MIDI clip."""

    return estimate_key_from_histogram(
        duration_weighted_histogram((clip,)),
        candidate_count=candidate_count,
    )


def estimate_combined_key(
    clip_a: MidiClip,
    clip_b: MidiClip,
    *,
    candidate_count: int = 5,
) -> KeyEstimate:
    """Estimate a shared key from both clips' duration-weighted material."""

    return estimate_key_from_histogram(
        duration_weighted_histogram((clip_a, clip_b)),
        candidate_count=candidate_count,
    )

