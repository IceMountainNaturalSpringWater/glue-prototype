from __future__ import annotations

from dataclasses import replace

import pytest

from glue.analysis import analyze_pair
from glue.fixes import (
    EditingStrategy,
    PairRepairResult,
    RepairPreset,
    generate_pair_repair,
    pair_repair_config_for,
)
from glue.models import MidiClip
from scripts.generate_fixtures import fixture_clips


def _assert_pitch_only(original: MidiClip, repaired: MidiClip) -> None:
    assert (
        repaired.ticks_per_beat,
        repaired.tempo_changes,
        repaired.time_signature_changes,
        repaired.tracks,
        repaired.length_ticks,
        repaired.name,
        repaired.midi_type,
    ) == (
        original.ticks_per_beat,
        original.tempo_changes,
        original.time_signature_changes,
        original.tracks,
        original.length_ticks,
        original.name,
        original.midi_type,
    )
    original_by_id = {note.id: note for note in original.notes}
    assert [note.id for note in repaired.notes] == [note.id for note in original.notes]
    for repaired_note in repaired.notes:
        original_note = original_by_id[repaired_note.id]
        assert (
            repaired_note.id,
            repaired_note.onset_ticks,
            repaired_note.duration_ticks,
            repaired_note.velocity,
            repaired_note.release_velocity,
            repaired_note.track,
            repaired_note.channel,
        ) == (
            original_note.id,
            original_note.onset_ticks,
            original_note.duration_ticks,
            original_note.velocity,
            original_note.release_velocity,
            original_note.track,
            original_note.channel,
        )
        assert repaired_note == replace(
            original_note,
            pitch=repaired_note.pitch,
        )


def _assert_pair_pitch_only(
    original_a: MidiClip,
    original_b: MidiClip,
    repaired_a: MidiClip,
    repaired_b: MidiClip,
) -> None:
    _assert_pitch_only(original_a, repaired_a)
    _assert_pitch_only(original_b, repaired_b)


def test_custom_presets_form_a_strict_edit_and_score_ladder() -> None:
    clips = fixture_clips()
    clip_a = clips["local_harmony_a"]
    clip_b = clips["local_harmony_b"]

    results = tuple(
        generate_pair_repair(
            clip_a,
            clip_b,
            strategy=EditingStrategy.CUSTOM,
            preset=preset,
            preservation_a=100,
            preservation_b=0,
        )
        for preset in RepairPreset
    )

    edit_counts = [result.changed_note_count for result in results]
    repaired_scores = [result.repaired_score for result in results]
    assert edit_counts[0] < edit_counts[1] < edit_counts[2]
    assert repaired_scores[0] < repaired_scores[1] < repaired_scores[2]
    assert all(result.has_improvement for result in results)
    assert all(result.changed_note_count_a == 0 for result in results)
    assert all(result.repaired_clip_a is clip_a for result in results)
    for result in results:
        assert result.after_analysis == analyze_pair(
            result.repaired_clip_a,
            result.repaired_clip_b,
        )
        _assert_pair_pitch_only(
            clip_a,
            clip_b,
            result.repaired_clip_a,
            result.repaired_clip_b,
        )


def test_creative_low_preservation_is_more_aggressive_and_scores_better() -> None:
    clips = fixture_clips()
    clip_a = clips["local_harmony_a"]
    clip_b = clips["local_harmony_b"]

    low = generate_pair_repair(
        clip_a,
        clip_b,
        strategy=EditingStrategy.CUSTOM,
        preset=RepairPreset.CREATIVE,
        preservation_a=100,
        preservation_b=0,
    )
    high = generate_pair_repair(
        clip_a,
        clip_b,
        strategy=EditingStrategy.CUSTOM,
        preset=RepairPreset.CREATIVE,
        preservation_a=100,
        preservation_b=85,
    )

    assert low.has_improvement
    assert high.has_improvement
    assert low.changed_note_count_b > high.changed_note_count_b
    assert low.repaired_score > high.repaired_score
    assert low.changed_note_count_a == high.changed_note_count_a == 0
    assert low.repaired_clip_a is high.repaired_clip_a is clip_a
    for result in (low, high):
        assert result.after_analysis == analyze_pair(
            result.repaired_clip_a,
            result.repaired_clip_b,
        )
        _assert_pair_pitch_only(
            clip_a,
            clip_b,
            result.repaired_clip_a,
            result.repaired_clip_b,
        )


def test_creative_finds_a_deterministic_same_side_coordinated_repair() -> None:
    clips = fixture_clips()
    clip_a = clips["coordinated_same_side_a"]
    clip_b = clips["coordinated_same_side_b"]

    def generate() -> PairRepairResult:
        return generate_pair_repair(
            clip_a,
            clip_b,
            strategy=EditingStrategy.CUSTOM,
            preset=RepairPreset.CREATIVE,
            preservation_a=100,
            preservation_b=0,
        )

    result = generate()

    assert result == generate()
    assert result.changed_note_count_a == 0
    assert result.changed_note_count_b == 2
    assert result.repaired_clip_a is clip_a
    assert result.has_improvement
    for edit in result.edits_b:
        partial_b = clip_b.with_notes(
            replace(note, pitch=edit.repaired_pitch)
            if note.id == edit.note_id
            else note
            for note in clip_b.notes
        )
        assert analyze_pair(clip_a, partial_b).overall_score <= (
            result.original_score + 1e-9
        )
    assert result.after_analysis == analyze_pair(
        result.repaired_clip_a,
        result.repaired_clip_b,
    )
    _assert_pair_pitch_only(
        clip_a,
        clip_b,
        result.repaired_clip_a,
        result.repaired_clip_b,
    )


@pytest.mark.parametrize("preset", tuple(RepairPreset))
def test_preservation_calibrates_bounds_and_exactly_locks_at_100(
    preset: RepairPreset,
) -> None:
    configs = {
        preservation: pair_repair_config_for(
            EditingStrategy.CUSTOM,
            preset,
            preservation_a=100,
            preservation_b=preservation,
        )
        for preservation in (0, 50, 85, 100)
    }

    assert configs[0].clip_b.max_note_changes > configs[50].clip_b.max_note_changes
    assert configs[50].clip_b.max_note_changes >= configs[85].clip_b.max_note_changes
    assert configs[85].clip_b.max_note_changes > 0
    for field in (
        "maximum_change_fraction",
        "candidate_notes_per_clip",
        "candidate_pitches_per_note",
        "beam_width",
        "maximum_iterations",
        "maximum_total_edits",
        "successors_per_state",
        "maximum_evaluations",
    ):
        low = getattr(configs[0].search, field)
        midpoint = getattr(configs[50].search, field)
        high = getattr(configs[85].search, field)
        assert low > midpoint >= high, field
    assert configs[100].clip_a.is_locked
    assert configs[100].clip_b.is_locked
    assert configs[100].clip_a.max_note_changes == 0
    assert configs[100].clip_b.max_note_changes == 0
    assert configs[100].search.maximum_total_edits == 0


def test_presets_keep_materially_distinct_calibrated_bounds() -> None:
    configs = tuple(
        pair_repair_config_for(
            EditingStrategy.CUSTOM,
            preset,
            preservation_a=100,
            preservation_b=50,
        )
        for preset in RepairPreset
    )

    per_side_budgets = [config.clip_b.max_note_changes for config in configs]
    assert per_side_budgets == sorted(set(per_side_budgets))
    for field in (
        "maximum_total_edits",
        "maximum_change_fraction",
        "candidate_notes_per_clip",
        "candidate_pitches_per_note",
        "beam_width",
        "maximum_iterations",
        "coordinated_options_per_clip",
        "maximum_evaluations",
    ):
        values = [getattr(config.search, field) for config in configs]
        assert values == sorted(set(values)), field
