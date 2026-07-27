from __future__ import annotations

import pytest

from glue.analysis import (
    duration_weighted_histogram,
    estimate_combined_key,
    estimate_key,
    estimate_key_from_histogram,
)
from glue.models import MidiClip, MidiNote


def _clip(
    pitches_and_durations: tuple[tuple[int, int], ...],
    *,
    channel: int = 0,
    ticks_per_beat: int = 480,
) -> MidiClip:
    notes = tuple(
        MidiNote(
            id=index,
            pitch=pitch,
            onset_ticks=sum(duration for _, duration in pitches_and_durations[:index]),
            duration_ticks=duration,
            velocity=90,
            track=0,
            channel=channel,
        )
        for index, (pitch, duration) in enumerate(pitches_and_durations)
    )
    return MidiClip(ticks_per_beat=ticks_per_beat, notes=notes)


def test_duration_weighted_key_estimation_finds_tonicized_c_major() -> None:
    clip = _clip(
        (
            (60, 1_920),
            (64, 960),
            (67, 960),
            (62, 480),
            (65, 480),
            (69, 480),
            (71, 480),
            (72, 1_920),
        )
    )

    estimate = estimate_key(clip)

    assert estimate.label == "C major"
    assert estimate.tonic_pc == 0
    assert estimate.mode == "major"
    assert 0 < estimate.confidence <= 1
    assert len(estimate.candidates) == 5
    assert [candidate.correlation for candidate in estimate.candidates] == sorted(
        (candidate.correlation for candidate in estimate.candidates),
        reverse=True,
    )


def test_octave_transposition_preserves_histogram_and_estimate() -> None:
    original = _clip(((60, 960), (63, 480), (67, 960), (68, 480), (70, 480)))
    transposed = _clip(((72, 960), (75, 480), (79, 960), (80, 480), (82, 480)))

    assert duration_weighted_histogram((original,)) == duration_weighted_histogram(
        (transposed,)
    )
    assert estimate_key(original) == estimate_key(transposed)


def test_single_pitch_is_reported_as_ambiguous() -> None:
    estimate = estimate_key(_clip(((60, 1_920),)))

    assert estimate.top is not None
    assert estimate.confidence < 0.25


def test_empty_uniform_and_percussion_only_material_are_unknown() -> None:
    assert estimate_key(MidiClip(ticks_per_beat=480)).label == "Unknown"
    assert estimate_key_from_histogram((1.0,) * 12).label == "Unknown"
    assert estimate_key(_clip(((60, 480), (64, 480)), channel=9)).label == "Unknown"


def test_combined_key_normalizes_different_ppq_resolutions() -> None:
    left = _clip(((60, 480), (64, 480), (67, 480)), ticks_per_beat=480)
    right = _clip(((72, 960), (76, 960), (79, 960)), ticks_per_beat=960)

    estimate = estimate_combined_key(left, right)

    assert estimate.label == "C major"


def test_histogram_validation_is_explicit() -> None:
    with pytest.raises(ValueError, match="12 pitch classes"):
        estimate_key_from_histogram((1.0,) * 11)
    with pytest.raises(ValueError, match="non-negative"):
        estimate_key_from_histogram((-1.0,) + (0.0,) * 11)
