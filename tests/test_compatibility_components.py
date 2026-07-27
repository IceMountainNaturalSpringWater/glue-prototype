from __future__ import annotations

from glue.analysis import (
    KeyCandidate,
    score_bass_compatibility,
    score_harmonic_compatibility,
    score_register_compatibility,
    score_rhythm_compatibility,
)
from glue.models import MidiClip, MidiNote

TICKS_PER_BEAT = 480
C_MAJOR = KeyCandidate(tonic_pc=0, mode="major", correlation=1.0)


def _notes_clip(
    pitches: tuple[int, ...],
    *,
    onset: int = 0,
    duration: int = TICKS_PER_BEAT,
    channel: int = 0,
) -> MidiClip:
    return MidiClip(
        ticks_per_beat=TICKS_PER_BEAT,
        notes=tuple(
            MidiNote(
                id=index,
                pitch=pitch,
                onset_ticks=onset,
                duration_ticks=duration,
                velocity=96,
                track=0,
                channel=channel,
            )
            for index, pitch in enumerate(pitches)
        ),
    )


def _attack_clip(
    onsets: tuple[int, ...],
    *,
    pitch: int = 60,
    channel: int = 0,
) -> MidiClip:
    return MidiClip(
        ticks_per_beat=TICKS_PER_BEAT,
        notes=tuple(
            MidiNote(
                id=index,
                pitch=pitch,
                onset_ticks=onset,
                duration_ticks=TICKS_PER_BEAT // 16,
                velocity=88,
                track=0,
                channel=channel,
            )
            for index, onset in enumerate(onsets)
        ),
    )


def test_harmonic_score_rewards_shared_chord_and_detects_local_conflict() -> None:
    c_shell = _notes_clip((60, 64))
    c_completion = _notes_clip((67, 72))
    c_triad = _notes_clip((60, 64, 67))
    d_minor = _notes_clip((62, 65, 69))

    compatible = score_harmonic_compatibility(c_shell, c_completion, C_MAJOR)
    conflicting = score_harmonic_compatibility(c_triad, d_minor, C_MAJOR)

    assert compatible > 80
    assert conflicting < 75
    assert compatible - conflicting > 15


def test_out_of_scale_tritone_lowers_harmonic_score() -> None:
    c_context = _notes_clip((48, 52, 55))
    chord_tone = _notes_clip((60,))
    f_sharp = _notes_clip((66,))

    compatible = score_harmonic_compatibility(c_context, chord_tone, C_MAJOR)
    out_of_key = score_harmonic_compatibility(c_context, f_sharp, C_MAJOR)

    assert compatible > 85
    assert out_of_key < 60
    assert compatible - out_of_key > 25


def test_bass_score_accepts_fifths_and_inversions_but_flags_semitones() -> None:
    c_bass = _notes_clip((48,))
    g_bass = _notes_clip((43,))
    e_bass = _notes_clip((52,))
    c_sharp_bass = _notes_clip((49,))

    fifth = score_bass_compatibility(c_bass, g_bass, C_MAJOR)
    inversion = score_bass_compatibility(c_bass, e_bass, C_MAJOR)
    contradiction = score_bass_compatibility(c_bass, c_sharp_bass, C_MAJOR)

    assert fifth > 75
    assert inversion > 75
    assert contradiction < 45
    assert min(fifth, inversion) - contradiction > 30


def test_register_score_only_penalizes_dense_nearby_material() -> None:
    chord = _notes_clip((60, 64, 67))
    collision = _notes_clip((60, 64, 67))
    separated = _notes_clip((84, 88, 91))
    single_a = _notes_clip((60,))
    single_b = _notes_clip((61,))

    collision_score = score_register_compatibility(chord, collision)
    separated_score = score_register_compatibility(chord, separated)

    assert collision_score < 45
    assert separated_score > 85
    assert separated_score - collision_score > 40
    assert score_register_compatibility(single_a, single_b) > 90


def test_rhythm_score_distinguishes_dense_aligned_and_interlocked_attacks() -> None:
    aligned_onsets = (0, 120, 240, 360)
    interlocked_onsets = (60, 180, 300, 420)
    left = _attack_clip(aligned_onsets)
    aligned = _attack_clip(aligned_onsets, pitch=67)
    interlocked = _attack_clip(interlocked_onsets, pitch=67)
    sparse_left = _attack_clip((0,))
    sparse_right = _attack_clip((0,), pitch=67)

    assert score_rhythm_compatibility(left, aligned, end_beat=1.0) < 35
    assert score_rhythm_compatibility(left, interlocked, end_beat=1.0) > 90
    assert score_rhythm_compatibility(
        sparse_left,
        sparse_right,
        end_beat=1.0,
    ) > 90


def test_percussion_is_neutral_for_pitch_components_but_kept_for_rhythm() -> None:
    onsets = (0, 120, 240, 360)
    drums_a = _attack_clip(onsets, pitch=36, channel=9)
    drums_b = _attack_clip(onsets, pitch=42, channel=9)

    assert score_harmonic_compatibility(drums_a, drums_b, C_MAJOR) == 100
    assert score_bass_compatibility(drums_a, drums_b, C_MAJOR) == 100
    assert score_register_compatibility(drums_a, drums_b) == 100
    assert score_rhythm_compatibility(drums_a, drums_b, end_beat=1.0) < 35
