from __future__ import annotations

import pytest

from glue.analysis import analyze_pair
from glue.fixes import (
    EditingStrategy,
    RepairPreset,
    generate_pair_repair,
    pair_repair_config_for,
    repair_config_for,
)
from glue.models import MidiClip
from scripts.generate_fixtures import fixture_clips


@pytest.mark.parametrize(
    ("preset", "expected_pitch"),
    (
        (RepairPreset.MINIMAL, 40),
        (RepairPreset.BALANCED, 40),
        (RepairPreset.CREATIVE, 40),
    ),
)
def test_one_note_regression_searches_the_complete_preset_vocabulary(
    preset: RepairPreset,
    expected_pitch: int,
) -> None:
    clips = fixture_clips()
    clip_a = clips["repair_one_note_context"]
    clip_b = clips["repair_one_note_source"]

    result = generate_pair_repair(
        clip_a,
        clip_b,
        strategy=EditingStrategy.CUSTOM,
        preset=preset,
        preservation_a=1.0,
        preservation_b=0.0,
    )

    assert [(edit.note_id, edit.original_pitch, edit.repaired_pitch) for edit in result.edits_b] == [
        (0, 52, expected_pitch)
    ]
    assert result.repaired_clip_a is clip_a
    assert result.repaired_clip_b.notes[0].pitch == expected_pitch
    assert result.has_improvement
    assert result.is_improving
    assert result.no_improvement_reason is None
    assert result.repaired_score > result.original_score
    assert result.after_analysis == analyze_pair(
        result.repaired_clip_a,
        result.repaired_clip_b,
    )


@pytest.mark.parametrize(
    ("preset", "expected_pitch"),
    (
        (RepairPreset.BALANCED, 60),
        (RepairPreset.CREATIVE, 64),
    ),
)
def test_two_note_regression_changes_both_wrong_notes_and_improves_full_pair(
    preset: RepairPreset,
    expected_pitch: int,
) -> None:
    clips = fixture_clips()
    clip_a = clips["repair_two_note_context"]
    clip_b = clips["repair_two_note_source"]

    result = generate_pair_repair(
        clip_a,
        clip_b,
        strategy=EditingStrategy.CUSTOM,
        preset=preset,
        preservation_a=1.0,
        preservation_b=0.0,
    )

    assert [(edit.note_id, edit.original_pitch, edit.repaired_pitch) for edit in result.edits_b] == [
        (0, 57, expected_pitch),
        (2, 57, expected_pitch),
    ]
    assert [note.pitch for note in result.repaired_clip_b.notes] == [
        expected_pitch,
        60,
        expected_pitch,
        60,
    ]
    assert result.changed_note_count == 2
    assert result.has_improvement
    assert result.score_improvement > 7.0
    assert result.after_analysis == analyze_pair(
        result.repaired_clip_a,
        result.repaired_clip_b,
    )


def test_preset_search_budgets_expand_in_every_relevant_dimension() -> None:
    one_sided = [repair_config_for(preset) for preset in RepairPreset]
    joint = [
        pair_repair_config_for(
            EditingStrategy.CUSTOM,
            preset,
            preservation_a=0,
            preservation_b=0,
        )
        for preset in RepairPreset
    ]

    assert [config.maximum_changes for config in one_sided] == [4, 8, 12]
    assert [config.maximum_change_fraction for config in one_sided] == [
        0.25,
        0.50,
        0.75,
    ]
    assert [config.maximum_candidate_pitches_per_note for config in one_sided] == [
        6,
        10,
        24,
    ]
    assert [config.search.maximum_total_edits for config in joint] == [2, 8, 16]
    assert [config.search.maximum_evaluations for config in joint] == [
        800,
        2_000,
        5_000,
    ]
    assert [config.search.candidate_pitches_per_note for config in joint] == [
        6,
        10,
        20,
    ]


def test_no_valid_pitch_edit_is_a_clear_unsuccessful_search_outcome() -> None:
    empty = MidiClip(ticks_per_beat=480, notes=())

    result = generate_pair_repair(
        empty,
        empty,
        strategy=EditingStrategy.CUSTOM,
        preservation_a=1.0,
        preservation_b=0.0,
    )

    assert result.changed_note_count == 0
    assert result.repaired_clip_a is empty
    assert result.repaired_clip_b is empty
    assert not result.has_improvement
    assert result.no_improvement_reason is not None
    assert "No improving candidate found" in result.no_improvement_reason
    assert "no valid pitch edit improved" in result.no_improvement_reason


def test_high_preservation_no_improvement_explains_the_constraint() -> None:
    clips = fixture_clips()

    result = generate_pair_repair(
        clips["repair_one_note_context"],
        clips["repair_one_note_source"],
        strategy=EditingStrategy.CUSTOM,
        preset=RepairPreset.CREATIVE,
        preservation_a=1.0,
        preservation_b=0.95,
    )

    assert result.changed_note_count == 0
    assert not result.has_improvement
    assert result.no_improvement_reason is not None
    assert "Preservation may be too high" in result.no_improvement_reason
