from __future__ import annotations

import pytest

from glue.analysis import (
    KeyCandidate,
    analyze_pair,
    analyze_window,
    infer_local_harmony_candidates,
    score_bass_compatibility,
    score_harmonic_compatibility,
)
from glue.models import MidiClip, MidiNote

TICKS_PER_BEAT = 480
C_MAJOR = KeyCandidate(tonic_pc=0, mode="major", correlation=1.0)
NoteSpec = tuple[int, int, int, int]


def _clip(
    specs: list[NoteSpec],
    *,
    ticks_per_beat: int = TICKS_PER_BEAT,
    length_ticks: int = 0,
) -> MidiClip:
    return MidiClip(
        ticks_per_beat=ticks_per_beat,
        notes=tuple(
            MidiNote(
                id=index,
                pitch=pitch,
                onset_ticks=onset,
                duration_ticks=duration,
                velocity=velocity,
                track=0,
                channel=0,
            )
            for index, (pitch, onset, duration, velocity) in enumerate(specs)
        ),
        length_ticks=length_ticks,
    )


def _chord(
    pitches: tuple[int, ...],
    *,
    onset: int = 0,
    duration: int = TICKS_PER_BEAT,
    velocity: int = 88,
) -> MidiClip:
    return _clip(
        [(pitch, onset, duration, velocity) for pitch in pitches],
        length_ticks=TICKS_PER_BEAT,
    )


def _progression(
    chords: list[tuple[int, ...]],
    *,
    onset_offset: int,
    duration: int,
) -> MidiClip:
    specs = [
        (pitch, window * TICKS_PER_BEAT + onset_offset, duration, 88)
        for window, chord in enumerate(chords)
        for pitch in chord
    ]
    return _clip(specs, length_ticks=len(chords) * TICKS_PER_BEAT)


def test_non_overlapping_notes_do_not_create_vertical_conflicts() -> None:
    clip_a = _chord((60, 64, 67), duration=TICKS_PER_BEAT // 2)
    clip_b = _chord(
        (61, 66, 70),
        onset=TICKS_PER_BEAT // 2,
        duration=TICKS_PER_BEAT // 2,
    )

    result = analyze_window(clip_a, clip_b, C_MAJOR, end_beat=1.0)

    assert result.activity_weight == 0
    assert result.reasons == ()
    assert (
        result.harmonic_score,
        result.bass_score,
        result.register_score,
        result.overall_score,
    ) == (100, 100, 100, 100)


def test_brief_low_passing_note_does_not_replace_sustained_bass() -> None:
    c_bass = _chord((48,))
    sustained_g = _chord((43,))
    g_with_passing_c_sharp = _clip(
        [
            (43, 0, TICKS_PER_BEAT, 88),
            (37, TICKS_PER_BEAT // 2, TICKS_PER_BEAT // 16, 88),
        ],
        length_ticks=TICKS_PER_BEAT,
    )

    control = score_bass_compatibility(
        c_bass,
        sustained_g,
        C_MAJOR,
        end_beat=1.0,
    )
    with_passing_note = score_bass_compatibility(
        c_bass,
        g_with_passing_c_sharp,
        C_MAJOR,
        end_beat=1.0,
    )

    assert 80 <= control <= 100
    assert 75 <= with_passing_note <= 100
    assert control - with_passing_note < 15


def test_bass_reason_names_clips_roots_and_strong_interval() -> None:
    result = analyze_window(
        _chord((48,)),
        _chord((49,)),
        C_MAJOR,
        end_beat=1.0,
    )

    message = next(
        reason.message for reason in result.reasons if reason.component == "bass"
    )
    assert "Clip A's sustained bass C3" in message
    assert "Clip B's C#3 form a semitone" in message
    assert "Clip A suggests C major" in message
    assert "Clip B's local root is unresolved" in message


def test_complete_em_triad_is_ranked_above_unsupported_c_major_seventh() -> None:
    candidates = infer_local_harmony_candidates(
        _chord((64, 67, 71)),
        C_MAJOR,
        end_beat=1.0,
    )

    assert candidates[0].label == "E minor"
    assert candidates[0].completeness == 1
    c_major_seventh = next(
        candidate
        for candidate in candidates
        if candidate.label == "C major seventh"
    )
    assert candidates[0].probability > c_major_seventh.probability
    assert candidates[0].completeness > c_major_seventh.completeness


def test_humanized_chord_coverage_roundoff_stays_in_unit_interval() -> None:
    # These ordinary velocities produce normalized evidence whose floating-point
    # sum is 1.0000000000000002 even though chord coverage is mathematically one.
    humanized_c_major = _clip(
        [
            (60, 0, TICKS_PER_BEAT, 96),
            (64, 0, TICKS_PER_BEAT, 98),
            (67, 0, TICKS_PER_BEAT, 107),
        ],
        length_ticks=TICKS_PER_BEAT,
    )

    candidates = infer_local_harmony_candidates(
        humanized_c_major,
        C_MAJOR,
        end_beat=1.0,
    )
    pair = analyze_pair(humanized_c_major, humanized_c_major)

    assert candidates[0].label == "C major"
    assert candidates[0].coverage == 1.0
    assert all(
        0.0 <= value <= 1.0
        for candidate in candidates
        for value in (
            candidate.probability,
            candidate.coverage,
            candidate.completeness,
        )
    )
    assert pair.windows[0].local_harmony_a[0].coverage == 1.0
    assert pair.windows[0].local_harmony_b[0].coverage == 1.0


def test_zero_coverage_out_of_key_pitch_has_unresolved_harmony_reason() -> None:
    c_context = _chord((48, 52, 55))
    f_sharp = _chord((66,))

    assert (
        infer_local_harmony_candidates(
            f_sharp,
            C_MAJOR,
            end_beat=1.0,
        )
        == ()
    )

    result = analyze_window(c_context, f_sharp, C_MAJOR, end_beat=1.0)
    message = next(
        reason.message
        for reason in result.reasons
        if reason.component == "harmonic"
    )

    assert result.local_harmony_b == ()
    assert "Clip B's local harmony is unresolved from F#" in message
    assert "Clip B suggests" not in message
    assert "Clip B's F# falls outside the estimated C major" in message
    assert "C-F# forms a tritone" in message


def test_compound_seventh_readings_remain_compatible() -> None:
    c_with_em = score_harmonic_compatibility(
        _chord((60, 64, 67)),
        _chord((64, 67, 71)),
        C_MAJOR,
        end_beat=1.0,
    )
    g_with_b_diminished = score_harmonic_compatibility(
        _chord((67, 71, 74)),
        _chord((71, 74, 77)),
        C_MAJOR,
        end_beat=1.0,
    )

    assert 80 <= c_with_em <= 95
    assert 75 <= g_with_b_diminished <= 95


def test_long_accented_tension_outweighs_short_passing_tone() -> None:
    c_context = _chord((48, 52, 55))
    passing_tone = _clip(
        [
            (67, 0, TICKS_PER_BEAT, 88),
            (66, TICKS_PER_BEAT // 2, TICKS_PER_BEAT // 8, 88),
        ],
        length_ticks=TICKS_PER_BEAT,
    )
    accented_tension = _clip(
        [
            (67, 0, TICKS_PER_BEAT // 8, 88),
            (66, 0, TICKS_PER_BEAT, 127),
        ],
        length_ticks=TICKS_PER_BEAT,
    )

    passing_score = score_harmonic_compatibility(
        c_context,
        passing_tone,
        C_MAJOR,
        end_beat=1.0,
    )
    accented_score = score_harmonic_compatibility(
        c_context,
        accented_tension,
        C_MAJOR,
        end_beat=1.0,
    )

    assert 80 <= passing_score <= 100
    assert 30 <= accented_score <= 65
    assert passing_score - accented_score > 25


def test_same_key_hidden_conflict_names_chords_and_tension_intervals() -> None:
    doubled_c = (48, 60, 64, 67)
    e_minor = (52, 55, 59)
    b_diminished = (59, 62, 65)
    clip_a = _progression(
        [doubled_c, doubled_c, doubled_c, e_minor, b_diminished, doubled_c],
        onset_offset=0,
        duration=TICKS_PER_BEAT,
    )
    clip_b = _progression(
        [
            (72, 84, 88, 91),
            (72, 84, 88, 91),
            (72, 84, 88, 91),
            (83, 86, 89),
            (88, 91, 95),
            (72, 84, 88, 91),
        ],
        onset_offset=TICKS_PER_BEAT // 8,
        duration=7 * TICKS_PER_BEAT // 8,
    )

    result = analyze_pair(clip_a, clip_b)

    assert result.key_a.label == result.key_b.label == "C major"
    assert result.key_a.confidence > 0.75
    clean_windows = result.windows[:3] + result.windows[5:]
    conflict_windows = result.windows[3:5]
    assert all(90 <= window.harmonic_score <= 100 for window in clean_windows)
    assert all(50 <= window.harmonic_score < 65 for window in conflict_windows)
    assert all(window.bass_score > 80 for window in conflict_windows)
    assert all(window.register_score > 95 for window in conflict_windows)
    for window in conflict_windows:
        message = next(
            reason.message
            for reason in window.reasons
            if reason.component == "harmonic"
        )
        assert "E minor" in message
        assert "B diminished" in message
        assert "E-F forms a semitone" in message
        assert "B-F forms a tritone" in message


def test_pair_scores_are_symmetric_and_ppq_invariant() -> None:
    left_480 = _chord((60, 64, 67))
    right_480 = _chord((62, 65, 69))
    left_960 = _clip(
        [(pitch, 0, 960, 88) for pitch in (60, 64, 67)],
        ticks_per_beat=960,
        length_ticks=960,
    )
    right_960 = _clip(
        [(pitch, 0, 960, 88) for pitch in (62, 65, 69)],
        ticks_per_beat=960,
        length_ticks=960,
    )

    forward = analyze_pair(left_480, right_480)
    reverse = analyze_pair(right_480, left_480)
    scaled = analyze_pair(left_960, right_960)

    assert reverse.component_scores == pytest.approx(forward.component_scores)
    assert reverse.overall_score == pytest.approx(forward.overall_score)
    assert scaled.component_scores == pytest.approx(forward.component_scores)
    assert scaled.overall_score == pytest.approx(forward.overall_score)
