from __future__ import annotations

from dataclasses import replace

import pytest

from glue.analysis import DEFAULT_ANALYSIS_CONFIG, analyze_pair
from glue.models import MidiClip, MidiNote, TimeSignatureChange
from scripts.generate_fixtures import fixture_clips

TICKS_PER_BEAT = 480


def _attack_clip(onsets: tuple[int, ...], *, pitch: int) -> MidiClip:
    return MidiClip(
        ticks_per_beat=TICKS_PER_BEAT,
        notes=tuple(
            MidiNote(
                id=index,
                pitch=pitch,
                onset_ticks=onset,
                duration_ticks=60,
                velocity=90,
                track=0,
                channel=0,
            )
            for index, onset in enumerate(onsets)
        ),
    )


def test_identical_fixture_scores_high_and_weighting_is_transparent() -> None:
    clips = fixture_clips()

    result = analyze_pair(clips["identical_a"], clips["identical_b"])

    expected = (
        result.harmonic_score * DEFAULT_ANALYSIS_CONFIG.harmonic_weight
        + result.bass_score * DEFAULT_ANALYSIS_CONFIG.bass_weight
        + result.register_score * DEFAULT_ANALYSIS_CONFIG.register_weight
        + result.rhythm_score * DEFAULT_ANALYSIS_CONFIG.rhythm_weight
    )
    assert result.overall_score == pytest.approx(expected)
    assert result.overall_score > 85
    assert result.harmonic_score > 95
    assert len(result.windows) == 4
    assert all(
        0 <= score <= 100
        for window in result.windows
        for score in (
            window.harmonic_score,
            window.bass_score,
            window.register_score,
            window.rhythm_score,
            window.overall_score,
        )
    )
    assert result == analyze_pair(clips["identical_a"], clips["identical_b"])


def test_same_global_material_can_still_show_local_harmonic_conflict() -> None:
    clips = fixture_clips()
    result = analyze_pair(clips["local_harmony_a"], clips["local_harmony_b"])
    compatible = analyze_pair(clips["identical_a"], clips["identical_b"])

    assert result.key_a.label == result.key_b.label
    assert max(window.harmonic_score for window in result.windows) < 75
    assert compatible.harmonic_score - result.harmonic_score > 15


def test_fixture_pairs_isolate_register_and_rhythm_components() -> None:
    clips = fixture_clips()

    register_collision = analyze_pair(
        clips["register_a"],
        clips["register_collision_b"],
    )
    register_separated = analyze_pair(
        clips["register_a"],
        clips["register_separated_b"],
    )
    rhythm_aligned = analyze_pair(clips["rhythm_a"], clips["rhythm_aligned_b"])
    rhythm_staggered = analyze_pair(clips["rhythm_a"], clips["rhythm_staggered_b"])

    assert register_collision.register_score < 45
    assert register_separated.register_score > 85
    assert register_separated.overall_score > register_collision.overall_score + 5
    assert rhythm_aligned.rhythm_score < 35
    assert rhythm_staggered.rhythm_score > 90
    assert rhythm_staggered.overall_score > rhythm_aligned.overall_score + 5


def test_out_of_key_window_has_specific_reason_and_lower_harmony() -> None:
    clips = fixture_clips()

    result = analyze_pair(
        clips["out_of_key_context"],
        clips["out_of_key_melody"],
    )

    f_sharp_window = result.windows[2]
    assert f_sharp_window.harmonic_score < result.windows[0].harmonic_score - 20
    assert any(
        reason.component == "harmonic" and "F#" in reason.message
        for reason in f_sharp_window.reasons
    )


def test_silent_tail_does_not_inflate_aggregate_compatibility() -> None:
    clips = fixture_clips()
    left = clips["local_harmony_a"]
    right = clips["local_harmony_b"]
    extended_left = replace(left, length_ticks=left.length_ticks + 20 * TICKS_PER_BEAT)
    extended_right = replace(right, length_ticks=right.length_ticks + 20 * TICKS_PER_BEAT)

    original = analyze_pair(left, right)
    extended = analyze_pair(extended_left, extended_right)

    assert extended.overall_score == pytest.approx(original.overall_score)
    assert extended.component_scores == pytest.approx(original.component_scores)
    assert len(extended.windows) > len(original.windows)


def test_half_open_windows_assign_boundary_attacks_once() -> None:
    onsets = (TICKS_PER_BEAT,) * 4
    left = _attack_clip(onsets, pitch=60)
    right = _attack_clip(onsets, pitch=67)
    left = replace(left, length_ticks=2 * TICKS_PER_BEAT)
    right = replace(right, length_ticks=2 * TICKS_PER_BEAT)

    result = analyze_pair(left, right)

    assert result.windows[0].rhythm_score == 100
    assert result.windows[1].rhythm_score < 35


def test_bar_summaries_use_quarter_note_meter_length() -> None:
    clips = fixture_clips()
    left = replace(
        clips["identical_a"],
        time_signature_changes=(TimeSignatureChange(0, 3, 4),),
    )

    result = analyze_pair(left, clips["identical_b"])

    assert [(bar.start_beat, bar.end_beat) for bar in result.bars] == [
        (0.0, 3.0),
        (3.0, 4.0),
    ]
    assert result.bars[0].window_indices == (0, 1, 2)
    assert result.bars[1].window_indices == (3,)


def test_odd_meter_windows_split_at_bar_boundaries() -> None:
    clips = fixture_clips()
    seven_beat_notes = tuple(
        replace(
            note,
            id=index,
            onset_ticks=index * TICKS_PER_BEAT,
        )
        for index, note in enumerate(clips["identical_a"].notes + clips["identical_a"].notes[:3])
    )
    left = replace(
        clips["identical_a"],
        notes=seven_beat_notes,
        length_ticks=7 * TICKS_PER_BEAT,
        time_signature_changes=(TimeSignatureChange(0, 7, 8),),
    )
    right = replace(left, name="odd_meter_b")

    result = analyze_pair(left, right)

    assert [(bar.start_beat, bar.end_beat) for bar in result.bars] == [
        (0.0, 3.5),
        (3.5, 7.0),
    ]
    assert [(window.start_beat, window.end_beat) for window in result.windows] == [
        (0.0, 1.0),
        (1.0, 2.0),
        (2.0, 3.0),
        (3.0, 3.5),
        (3.5, 4.0),
        (4.0, 5.0),
        (5.0, 6.0),
        (6.0, 7.0),
    ]
    assert result.bars[0].window_indices == (0, 1, 2, 3)
    assert result.bars[1].window_indices == (4, 5, 6, 7)


def test_c_minor_fixtures_are_compatible_with_qualified_key_estimates() -> None:
    clips = fixture_clips()

    result = analyze_pair(clips["c_minor_melody"], clips["c_minor_chords"])

    assert result.key_a.label == "C minor"
    assert result.key_b.label == "C minor"
    assert result.combined_key.label == "C minor"
    assert 0 < result.key_a.confidence <= 1
    assert result.harmonic_score > 75
    assert result.overall_score > 75


def test_octave_equivalent_fixtures_keep_tonal_and_register_compatibility() -> None:
    clips = fixture_clips()

    result = analyze_pair(clips["octave_original"], clips["octave_up"])

    assert result.key_a == result.key_b
    assert result.combined_key.label == "C major"
    assert result.harmonic_score > 95
    assert result.register_score > 90
    assert result.overall_score > 90
