from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import mido
import pytest

import glue.fixes.minimal as minimal_module
from glue.analysis import AnalysisConfig, PairAnalysis, analyze_pair
from glue.fixes import (
    ALLOWED_MINIMAL_DELTAS,
    MinimalRepairConfig,
    generate_minimal_repair,
)
from glue.io import load_midi, write_midi
from glue.models import MidiClip, MidiNote
from scripts.generate_fixtures import fixture_clips, generate_fixtures

TICKS_PER_BEAT = 480


def _repeated_conflict(note_count: int) -> tuple[MidiClip, MidiClip]:
    locked = MidiClip(
        ticks_per_beat=TICKS_PER_BEAT,
        notes=tuple(
            MidiNote(
                id=index,
                pitch=pitch,
                onset_ticks=0,
                duration_ticks=note_count * TICKS_PER_BEAT,
                velocity=96,
                track=0,
                channel=0,
            )
            for index, pitch in enumerate((48, 52, 55))
        ),
    )
    unlocked = MidiClip(
        ticks_per_beat=TICKS_PER_BEAT,
        notes=tuple(
            MidiNote(
                id=index,
                pitch=66,
                onset_ticks=index * TICKS_PER_BEAT,
                duration_ticks=TICKS_PER_BEAT,
                velocity=90,
                track=0,
                channel=0,
            )
            for index in range(note_count)
        ),
    )
    return locked, unlocked


def test_minimal_repair_improves_obvious_out_of_key_note() -> None:
    clips = fixture_clips()

    result = generate_minimal_repair(
        clips["out_of_key_context"],
        clips["out_of_key_melody"],
    )

    assert result.changed_note_count == 1
    assert result.score_improvement > 5
    assert result.repaired_score > result.original_score
    assert result.after_analysis == analyze_pair(
        clips["out_of_key_context"],
        result.repaired_clip,
    )
    edit = result.edits[0]
    assert (edit.note_id, edit.original_pitch, edit.repaired_pitch) == (2, 66, 64)
    assert edit.objective_gain > 0
    assert result.objective_gain > 0


def test_minimal_repair_is_deterministic_and_result_models_are_immutable() -> None:
    clips = fixture_clips()
    locked = clips["out_of_key_context"]
    unlocked = clips["out_of_key_melody"]

    first = generate_minimal_repair(locked, unlocked)
    second = generate_minimal_repair(locked, unlocked)

    assert first == second
    assert first.original_clip == unlocked
    assert unlocked == clips["out_of_key_melody"]
    with pytest.raises(FrozenInstanceError):
        first.edits[0].repaired_pitch = 65  # type: ignore[misc]


def test_repair_changes_only_pitch_and_uses_allowed_deltas() -> None:
    clips = fixture_clips()
    unlocked = clips["local_harmony_b"]

    result = generate_minimal_repair(clips["local_harmony_a"], unlocked)

    # Six pitched notes at the default 25% fraction have a floor-based cap of
    # one edit (while clips shorter than four notes still receive a one-note
    # minimum when the configured fraction is positive).
    assert result.changed_note_count == 1
    assert {edit.delta for edit in result.edits} <= set(ALLOWED_MINIMAL_DELTAS)
    original_by_id = {note.id: note for note in unlocked.notes}
    edited_ids = {edit.note_id for edit in result.edits}
    for repaired_note in result.repaired_clip.notes:
        original = original_by_id[repaired_note.id]
        assert (
            repaired_note.onset_ticks,
            repaired_note.duration_ticks,
            repaired_note.velocity,
            repaired_note.release_velocity,
            repaired_note.track,
            repaired_note.channel,
        ) == (
            original.onset_ticks,
            original.duration_ticks,
            original.velocity,
            original.release_velocity,
            original.track,
            original.channel,
        )
        assert (repaired_note.pitch != original.pitch) == (
            repaired_note.id in edited_ids
        )
    assert (
        result.repaired_clip.tempo_changes,
        result.repaired_clip.time_signature_changes,
        result.repaired_clip.tracks,
        result.repaired_clip.length_ticks,
        result.repaired_clip.ticks_per_beat,
        result.repaired_clip.midi_type,
    ) == (
        unlocked.tempo_changes,
        unlocked.time_signature_changes,
        unlocked.tracks,
        unlocked.length_ticks,
        unlocked.ticks_per_beat,
        unlocked.midi_type,
    )


def test_register_conflict_can_consider_a_pitch_class_preserving_octave_move() -> None:
    clips = fixture_clips()
    zero_penalty_config = MinimalRepairConfig(
        maximum_changes=1,
        maximum_change_fraction=1.0,
        edit_penalty=0.0,
        semitone_distance_penalty=0.0,
        contour_penalty=0.0,
        octave_penalty=0.0,
    )

    result = generate_minimal_repair(
        clips["register_a"],
        clips["register_collision_b"],
        repair_config=zero_penalty_config,
    )

    assert result.changed_note_count == 1
    assert result.edits[0].delta in {-12, 12}
    assert result.edits[0].is_octave_move
    assert result.repaired_score > result.original_score


def test_rhythmic_only_clash_does_not_trigger_pitch_edits() -> None:
    clips = fixture_clips()
    unlocked = clips["rhythm_aligned_b"]

    result = generate_minimal_repair(clips["rhythm_a"], unlocked)

    assert result.before_analysis.rhythm_score < 35
    assert min(
        result.before_analysis.harmonic_score,
        result.before_analysis.bass_score,
        result.before_analysis.register_score,
    ) > 65
    assert result.changed_note_count == 0
    assert result.repaired_clip is unlocked
    assert result.before_analysis == result.after_analysis
    assert result.objective_gain == 0


def test_repair_rejects_new_nested_equal_pitch_overlap() -> None:
    locked = MidiClip(
        ticks_per_beat=TICKS_PER_BEAT,
        notes=tuple(
            MidiNote(
                id=index,
                pitch=pitch,
                onset_ticks=0,
                duration_ticks=TICKS_PER_BEAT,
                velocity=96,
                track=0,
                channel=0,
            )
            for index, pitch in enumerate((48, 52, 55))
        ),
    )
    unlocked = MidiClip(
        ticks_per_beat=TICKS_PER_BEAT,
        notes=(
            MidiNote(0, 60, 0, TICKS_PER_BEAT, 90, 0, 0),
            MidiNote(1, 61, 120, 120, 90, 0, 0),
        ),
    )
    zero_penalty = MinimalRepairConfig(
        weak_window_threshold=100.0,
        maximum_changes=1,
        maximum_change_fraction=1.0,
        edit_penalty=0.0,
        semitone_distance_penalty=0.0,
        contour_penalty=0.0,
        octave_penalty=0.0,
    )

    result = generate_minimal_repair(
        locked,
        unlocked,
        repair_config=zero_penalty,
    )

    assert result.changed_note_count == 1
    # C# -> C would create an equal-pitch interval nested inside the existing
    # C note.  Such a file cannot retain the two intended note-off identities.
    assert not any(
        edit.note_id == 1 and edit.repaired_pitch == 60 for edit in result.edits
    )
    repaired_by_id = {note.id: note for note in result.repaired_clip.notes}
    assert not (
        repaired_by_id[0].pitch == repaired_by_id[1].pitch
        and repaired_by_id[0].onset_ticks < repaired_by_id[1].end_ticks
        and repaired_by_id[1].onset_ticks < repaired_by_id[0].end_ticks
    )


def test_local_window_objective_repairs_a_32_beat_repeated_conflict() -> None:
    locked, unlocked = _repeated_conflict(32)

    result = generate_minimal_repair(locked, unlocked)

    assert 0 < result.changed_note_count <= 4
    assert result.repaired_score >= result.original_score
    assert result.score_improvement > 0
    assert result.objective_gain == pytest.approx(
        sum(edit.objective_gain for edit in result.edits)
    )
    for edit in result.edits:
        assert edit.objective_gain == pytest.approx(
            edit.score_improvement - edit.penalty
        )


def test_candidate_shortlist_is_validated_and_bounds_full_pair_analyses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="maximum_candidate_notes_per_step"):
        MinimalRepairConfig(maximum_candidate_notes_per_step=0)

    locked, unlocked = _repeated_conflict(8)
    repair_config = MinimalRepairConfig(
        weak_window_threshold=100.0,
        maximum_changes=1,
        maximum_change_fraction=1.0,
        maximum_candidate_notes_per_step=2,
        edit_penalty=0.0,
        semitone_distance_penalty=0.0,
        contour_penalty=0.0,
        octave_penalty=0.0,
    )
    original_analyze_pair = minimal_module.analyze_pair
    analysis_calls = 0

    def counted_analyze_pair(
        left: MidiClip,
        right: MidiClip,
        *,
        config: AnalysisConfig,
    ) -> PairAnalysis:
        nonlocal analysis_calls
        analysis_calls += 1
        return original_analyze_pair(left, right, config=config)

    monkeypatch.setattr(minimal_module, "analyze_pair", counted_analyze_pair)

    first = generate_minimal_repair(
        locked,
        unlocked,
        repair_config=repair_config,
    )
    first_call_count = analysis_calls
    analysis_calls = 0
    second = generate_minimal_repair(
        locked,
        unlocked,
        repair_config=repair_config,
    )

    # One initial analysis plus at most six pitch deltas for each shortlisted
    # note.  This proves a bound without asserting wall-clock timing.
    maximum_calls = 1 + 2 * len(ALLOWED_MINIMAL_DELTAS)
    assert 1 < first_call_count <= maximum_calls
    assert 1 < analysis_calls <= maximum_calls
    assert first == second


def test_contour_penalty_ignores_other_tracks_and_channels() -> None:
    notes = (
        MidiNote(0, 36, 0, 120, 90, 1, 0),
        MidiNote(1, 60, 480, 120, 90, 0, 0),
        MidiNote(2, 96, 960, 120, 90, 0, 1),
    )

    assert minimal_module._contour_disruption(notes, 1, 62) == 0


def _message_dicts(path: Path) -> tuple[tuple[dict[str, object], ...], ...]:
    midi = mido.MidiFile(filename=path)
    return tuple(tuple(message.dict() for message in track) for track in midi.tracks)


def test_repaired_clip_exports_and_reloads_with_source_timing_intact(
    tmp_path: Path,
) -> None:
    generated = generate_fixtures(tmp_path / "fixtures")
    locked_document = load_midi(generated["out_of_key_context"])
    unlocked_document = load_midi(generated["out_of_key_melody"])
    result = generate_minimal_repair(
        locked_document.clip,
        unlocked_document.clip,
    )
    output = tmp_path / "repaired.mid"

    write_midi(result.repaired_clip, output, template=unlocked_document)

    reloaded = load_midi(output)
    assert reloaded.clip.notes == result.repaired_clip.notes
    assert reloaded.clip.tempo_changes == result.repaired_clip.tempo_changes
    assert reloaded.clip.time_signature_changes == result.repaired_clip.time_signature_changes
    assert reloaded.clip.tracks == result.repaired_clip.tracks
    assert analyze_pair(
        locked_document.clip,
        reloaded.clip,
    ).overall_score == pytest.approx(result.repaired_score)

    source_messages = _message_dicts(generated["out_of_key_melody"])
    repaired_messages = _message_dicts(output)
    changed_fields: list[set[str]] = []
    for source_track, repaired_track in zip(
        source_messages,
        repaired_messages,
        strict=True,
    ):
        for source_message, repaired_message in zip(
            source_track,
            repaired_track,
            strict=True,
        ):
            differences = {
                key
                for key in source_message.keys() | repaired_message.keys()
                if source_message.get(key) != repaired_message.get(key)
            }
            if differences:
                changed_fields.append(differences)

    assert changed_fields == [{"note"}, {"note"}]
