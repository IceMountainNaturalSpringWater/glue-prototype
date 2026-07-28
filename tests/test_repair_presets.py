from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import mido
import pytest

from glue.analysis import DEFAULT_ANALYSIS_CONFIG, analyze_pair
from glue.fixes import (
    ALLOWED_MINIMAL_DELTAS,
    DEFAULT_MINIMAL_REPAIR_CONFIG,
    MinimalRepairConfig,
    OctavePolicy,
    RepairPreset,
    generate_minimal_repair,
    generate_repair,
    repair_config_for,
)
from glue.io import load_midi, write_midi
from glue.models import MidiClip, MidiNote
from scripts.generate_fixtures import fixture_clips

TICKS_PER_BEAT = 480


def test_preset_configs_are_typed_bounded_and_preservation_scaled() -> None:
    minimal = repair_config_for(RepairPreset.MINIMAL)
    balanced = repair_config_for("BALANCED")
    creative = repair_config_for(RepairPreset.CREATIVE)

    assert minimal == DEFAULT_MINIMAL_REPAIR_CONFIG
    assert minimal.preset is RepairPreset.MINIMAL
    assert balanced.preset is RepairPreset.BALANCED
    assert creative.preset is RepairPreset.CREATIVE
    assert minimal.octave_policy is OctavePolicy.REGISTER_CONFLICT
    assert balanced.octave_policy is OctavePolicy.ALWAYS
    assert creative.octave_policy is OctavePolicy.ALWAYS
    assert not minimal.use_local_harmony_candidates
    assert not balanced.use_local_harmony_candidates
    assert creative.use_local_harmony_candidates
    assert set(minimal.nearby_deltas) < set(balanced.nearby_deltas)
    assert set(balanced.nearby_deltas) < set(creative.nearby_deltas)
    assert (
        minimal.edit_penalty
        > balanced.edit_penalty
        > creative.edit_penalty
    )
    assert repair_config_for("minimal", 0).preservation_scale == pytest.approx(0.25)
    assert repair_config_for("minimal", 50).preservation_scale == pytest.approx(1.0)
    assert repair_config_for("minimal", 100).preservation_scale == pytest.approx(1.75)

    with pytest.raises(ValueError, match="preset must be one of"):
        repair_config_for("unknown")
    with pytest.raises(ValueError, match="preservation"):
        repair_config_for("minimal", -1)
    with pytest.raises(ValueError, match="preservation"):
        repair_config_for("minimal", 101)
    with pytest.raises(ValueError, match="nearby_deltas"):
        MinimalRepairConfig(nearby_deltas=(-1, -1))
    with pytest.raises(ValueError, match="maximum_candidate_pitches_per_note"):
        MinimalRepairConfig(maximum_candidate_pitches_per_note=0)


def test_generic_minimal_at_midpoint_exactly_matches_v01_wrapper() -> None:
    clips = fixture_clips()
    locked = clips["out_of_key_context"]
    unlocked = clips["out_of_key_melody"]

    legacy = generate_minimal_repair(locked, unlocked)
    generic = generate_repair(
        locked,
        unlocked,
        repair_config=repair_config_for(RepairPreset.MINIMAL, 50),
    )

    assert generic == legacy
    assert generic.preset is RepairPreset.MINIMAL
    assert generic.preservation == 50
    assert generic.repair_config == DEFAULT_MINIMAL_REPAIR_CONFIG
    assert generic.analysis_config == DEFAULT_ANALYSIS_CONFIG
    assert generic.changed_note_count == 1
    assert (
        generic.edits[0].note_id,
        generic.edits[0].original_pitch,
        generic.edits[0].repaired_pitch,
    ) == (2, 66, 64)
    assert generic.edits[0].delta in ALLOWED_MINIMAL_DELTAS


def test_repair_handles_humanized_chord_coverage_roundoff() -> None:
    humanized_c_major = MidiClip(
        ticks_per_beat=480,
        notes=tuple(
            MidiNote(index, pitch, 0, 480, velocity, 0, 0)
            for index, (pitch, velocity) in enumerate(
                ((60, 96), (64, 98), (67, 107))
            )
        ),
    )

    result = generate_minimal_repair(humanized_c_major, humanized_c_major)

    assert result.changed_note_count == 0
    assert result.repaired_clip is humanized_c_major
    assert result.before_analysis == result.after_analysis
    assert all(
        candidate.coverage <= 1.0
        for window in result.before_analysis.windows
        for candidate in (*window.local_harmony_a, *window.local_harmony_b)
    )


def test_preservation_changes_penalty_without_changing_minimal_search_policy() -> None:
    clips = fixture_clips()
    locked = clips["register_a"]
    unlocked = clips["register_collision_b"]

    low = generate_repair(
        locked,
        unlocked,
        repair_config=repair_config_for(RepairPreset.MINIMAL, 0),
    )
    midpoint = generate_repair(
        locked,
        unlocked,
        repair_config=repair_config_for(RepairPreset.MINIMAL, 50),
    )
    high = generate_repair(
        locked,
        unlocked,
        repair_config=repair_config_for(RepairPreset.MINIMAL, 100),
    )

    assert low.changed_note_count == 1
    assert low.edits[0].is_octave_move
    assert low.repaired_score > low.original_score
    assert midpoint.changed_note_count == 0
    assert high.changed_note_count == 0
    assert midpoint.repaired_clip is unlocked
    assert high.repaired_clip is unlocked
    assert low.edits[0].penalty < 3.0


def test_balanced_preset_performs_an_actual_octave_repair() -> None:
    clips = fixture_clips()

    result = generate_repair(
        clips["register_a"],
        clips["register_collision_b"],
        repair_config=repair_config_for(RepairPreset.BALANCED),
    )

    assert result.changed_note_count == 1
    assert result.edits[0].is_octave_move
    assert result.edits[0].delta in {-12, 12}
    assert result.repaired_score > result.original_score


@pytest.mark.parametrize("preset", tuple(RepairPreset))
def test_rhythmic_only_clash_remains_pitch_unchanged_for_every_preset(
    preset: RepairPreset,
) -> None:
    clips = fixture_clips()
    unlocked = clips["rhythm_aligned_b"]

    result = generate_repair(
        clips["rhythm_a"],
        unlocked,
        repair_config=repair_config_for(preset),
    )

    assert result.before_analysis.rhythm_score < 35
    assert min(
        result.before_analysis.harmonic_score,
        result.before_analysis.bass_score,
        result.before_analysis.register_score,
    ) > result.repair_config.weak_window_threshold
    assert result.changed_note_count == 0
    assert result.repaired_clip is unlocked
    assert result.before_analysis == result.after_analysis


@pytest.mark.parametrize("preset", tuple(RepairPreset))
def test_every_preset_is_deterministic_pitch_only_and_skips_percussion(
    preset: RepairPreset,
) -> None:
    clips = fixture_clips()
    locked = clips["out_of_key_context"]
    base = clips["out_of_key_melody"]
    percussion = MidiNote(
        id=max(note.id for note in base.notes) + 1,
        pitch=36,
        onset_ticks=0,
        duration_ticks=base.ticks_per_beat,
        velocity=100,
        track=0,
        channel=9,
    )
    unlocked = base.with_notes((*base.notes, percussion))
    config = repair_config_for(preset)

    first = generate_repair(locked, unlocked, repair_config=config)
    second = generate_repair(locked, unlocked, repair_config=config)

    assert first == second
    assert first.original_clip is unlocked
    assert first.preset is preset
    assert first.repair_config == config
    assert first.repaired_score >= first.original_score
    assert first.after_analysis == analyze_pair(locked, first.repaired_clip)

    original_by_id = {note.id: note for note in unlocked.notes}
    edited_ids = {edit.note_id for edit in first.edits}
    for repaired_note in first.repaired_clip.notes:
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
    assert first.repaired_clip.tempo_changes == unlocked.tempo_changes
    assert first.repaired_clip.time_signature_changes == unlocked.time_signature_changes
    assert first.repaired_clip.tracks == unlocked.tracks
    assert first.repaired_clip.length_ticks == unlocked.length_ticks
    assert next(
        note for note in first.repaired_clip.notes if note.id == percussion.id
    ) == percussion


def test_presets_expand_search_and_creative_uses_local_harmony_targets() -> None:
    clips = fixture_clips()
    locked = clips["out_of_key_context"]
    unlocked = clips["out_of_key_melody"]

    minimal = generate_repair(
        locked,
        unlocked,
        repair_config=repair_config_for(RepairPreset.MINIMAL),
    )
    balanced = generate_repair(
        locked,
        unlocked,
        repair_config=repair_config_for(RepairPreset.BALANCED),
    )
    creative = generate_repair(
        locked,
        unlocked,
        repair_config=repair_config_for(RepairPreset.CREATIVE),
    )

    assert balanced.changed_note_count > minimal.changed_note_count
    assert balanced.repaired_score > minimal.repaired_score
    assert creative.repaired_score > balanced.repaired_score
    assert any(window.local_harmony_a for window in creative.before_analysis.windows)
    # Creative's fixed nearby search stops at seven semitones. A non-octave
    # 8-11 semitone move therefore proves a public local-harmony target entered
    # and won the deterministic candidate search.
    assert any(8 <= abs(edit.delta) <= 11 for edit in creative.edits)


@pytest.mark.parametrize("preset", tuple(RepairPreset))
def test_every_preset_rejects_new_overlapping_equal_pitch_collisions(
    preset: RepairPreset,
) -> None:
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
    config = replace(
        repair_config_for(preset),
        weak_window_threshold=100.0,
        maximum_changes=1,
        maximum_change_fraction=1.0,
        edit_penalty=0.0,
        semitone_distance_penalty=0.0,
        contour_penalty=0.0,
        octave_penalty=0.0,
    )

    result = generate_repair(locked, unlocked, repair_config=config)

    repaired_by_id = {note.id: note for note in result.repaired_clip.notes}
    outer = repaired_by_id[0]
    inner = repaired_by_id[1]
    assert not (
        outer.pitch == inner.pitch
        and outer.onset_ticks < inner.end_ticks
        and inner.onset_ticks < outer.end_ticks
    )


@pytest.mark.parametrize("preset", tuple(RepairPreset))
def test_every_preset_reloads_from_pitch_only_template_export(
    tmp_path: Path,
    preset: RepairPreset,
) -> None:
    clips = fixture_clips()
    locked_path = write_midi(
        clips["out_of_key_context"],
        tmp_path / "locked.mid",
    )
    unlocked_path = write_midi(
        clips["out_of_key_melody"],
        tmp_path / "unlocked.mid",
    )
    locked_document = load_midi(locked_path)
    unlocked_document = load_midi(unlocked_path)
    result = generate_repair(
        locked_document.clip,
        unlocked_document.clip,
        repair_config=repair_config_for(preset),
    )
    output = tmp_path / f"{preset.value}.mid"

    write_midi(result.repaired_clip, output, template=unlocked_document)

    reloaded = load_midi(output)
    assert reloaded.clip.notes == result.repaired_clip.notes
    assert reloaded.clip.tempo_changes == result.repaired_clip.tempo_changes
    assert reloaded.clip.time_signature_changes == result.repaired_clip.time_signature_changes
    assert analyze_pair(
        locked_document.clip,
        reloaded.clip,
    ).overall_score == pytest.approx(result.repaired_score)

    source_tracks = mido.MidiFile(filename=unlocked_path).tracks
    repaired_tracks = mido.MidiFile(filename=output).tracks
    changed_fields: list[set[str]] = []
    for source_track, repaired_track in zip(
        source_tracks,
        repaired_tracks,
        strict=True,
    ):
        for source_message, repaired_message in zip(
            source_track,
            repaired_track,
            strict=True,
        ):
            source = source_message.dict()
            repaired = repaired_message.dict()
            differences = {
                key
                for key in source.keys() | repaired.keys()
                if source.get(key) != repaired.get(key)
            }
            if differences:
                changed_fields.append(differences)
    assert changed_fields == [{"note"}] * (2 * result.changed_note_count)


def test_minimal_wrapper_rejects_nonminimal_configuration() -> None:
    clips = fixture_clips()

    with pytest.raises(ValueError, match="requires a Minimal"):
        generate_minimal_repair(
            clips["out_of_key_context"],
            clips["out_of_key_melody"],
            repair_config=repair_config_for(RepairPreset.BALANCED),
        )


def test_preservation_is_stored_even_when_config_is_replaced() -> None:
    clips = fixture_clips()
    config = replace(
        repair_config_for(RepairPreset.CREATIVE),
        preservation=73,
    )

    result = generate_repair(
        clips["out_of_key_context"],
        clips["out_of_key_melody"],
        repair_config=config,
    )

    assert result.repair_config is config
    assert result.preservation == 73
