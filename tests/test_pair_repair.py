from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

import glue.fixes.pair as pair_module
from glue.analysis import AnalysisConfig, PairAnalysis, analyze_pair
from glue.fixes import (
    ClipRepairConstraints,
    EditingStrategy,
    JointObjectiveWeights,
    JointSearchBounds,
    RepairConstraintError,
    RepairPreset,
    generate_pair_repair,
    generate_repair,
    normalize_preservation,
    pair_repair_config_for,
)
from glue.models import MidiClip, MidiNote, TimeSignatureChange
from scripts.generate_fixtures import fixture_clips


def _assert_pitch_only(original: MidiClip, repaired: MidiClip) -> None:
    assert original.ticks_per_beat == repaired.ticks_per_beat
    assert original.tempo_changes == repaired.tempo_changes
    assert original.time_signature_changes == repaired.time_signature_changes
    assert original.tracks == repaired.tracks
    assert original.length_ticks == repaired.length_ticks
    assert original.name == repaired.name
    assert original.midi_type == repaired.midi_type
    original_by_id = {note.id: note for note in original.notes}
    assert original_by_id.keys() == {note.id for note in repaired.notes}
    for candidate in repaired.notes:
        source = original_by_id[candidate.id]
        assert (
            candidate.onset_ticks,
            candidate.duration_ticks,
            candidate.velocity,
            candidate.release_velocity,
            candidate.track,
            candidate.channel,
        ) == (
            source.onset_ticks,
            source.duration_ticks,
            source.velocity,
            source.release_velocity,
            source.track,
            source.channel,
        )
        assert 0 <= candidate.pitch <= 127
        assert candidate.duration_ticks >= 0


def _new_same_voice_collisions(original: MidiClip, repaired: MidiClip) -> list[tuple[int, int]]:
    original_by_id = {note.id: note for note in original.notes}
    collisions: list[tuple[int, int]] = []
    for index, left in enumerate(repaired.notes):
        for right in repaired.notes[index + 1 :]:
            if (
                left.track == right.track
                and left.channel == right.channel
                and left.pitch == right.pitch
                and left.onset_ticks < right.end_ticks
                and right.onset_ticks < left.end_ticks
                and original_by_id[left.id].pitch != original_by_id[right.id].pitch
            ):
                collisions.append((left.id, right.id))
    return collisions


def test_constraint_and_strategy_models_are_typed_bounded_and_immutable() -> None:
    constraints = ClipRepairConstraints(
        preservation=0.75,
        max_note_changes=2,
    )

    assert constraints.preservation_percent == 75
    assert not constraints.is_locked
    assert normalize_preservation(85) == pytest.approx(0.85)
    assert normalize_preservation(0.85) == pytest.approx(0.85)
    with pytest.raises(FrozenInstanceError):
        constraints.preservation = 0.5  # type: ignore[misc]
    with pytest.raises(ValueError, match="between 0 and 1"):
        ClipRepairConstraints(preservation=1.01)
    with pytest.raises(ValueError, match="not supported"):
        ClipRepairConstraints(preservation=0.5, allow_rhythm_edits=True)
    with pytest.raises(ValueError, match="between 0 and 1 or 0 and 100"):
        normalize_preservation(101)
    with pytest.raises(ValueError, match="between 0 and 1 or 0 and 100"):
        pair_repair_config_for("preserve-a", preservation_a=-1)
    with pytest.raises(TypeError, match="preservation"):
        normalize_preservation(True)
    with pytest.raises(ValueError, match="maximum_change_fraction"):
        JointSearchBounds(maximum_change_fraction=1.01)
    with pytest.raises(ValueError, match="paired_options_per_clip"):
        JointSearchBounds(paired_options_per_clip=0)
    with pytest.raises(ValueError, match="coordinated_options_per_clip"):
        JointSearchBounds(coordinated_options_per_clip=0)


@pytest.mark.parametrize("value", (float("nan"), float("inf"), float("-inf")))
def test_joint_objective_weights_reject_non_finite_values(value: float) -> None:
    with pytest.raises(ValueError, match="edit_count must be finite"):
        JointObjectiveWeights(edit_count=value)


@pytest.mark.parametrize(
    "field",
    ("maximum_change_fraction", "minimum_score_improvement"),
)
@pytest.mark.parametrize("value", (float("nan"), float("inf"), float("-inf")))
def test_joint_search_bounds_reject_non_finite_floats(
    field: str,
    value: float,
) -> None:
    with pytest.raises(ValueError, match=rf"{field} must be finite"):
        JointSearchBounds(**{field: value})


def test_presets_have_meaningfully_distinct_joint_search_budgets() -> None:
    configs = [
        pair_repair_config_for(
            EditingStrategy.CUSTOM,
            preset,
            preservation_a=0,
            preservation_b=0,
        )
        for preset in RepairPreset
    ]

    assert [config.search.maximum_total_edits for config in configs] == [2, 8, 16]
    assert [config.clip_a.max_note_changes for config in configs] == [2, 4, 8]
    assert [config.search.maximum_evaluations for config in configs] == [800, 2000, 5000]
    assert [config.search.candidate_pitches_per_note for config in configs] == [
        6,
        10,
        20,
    ]
    assert [config.search.candidate_notes_per_clip for config in configs] == [
        8,
        10,
        14,
    ]
    assert [config.search.beam_width for config in configs] == [8, 10, 14]
    assert [config.search.maximum_iterations for config in configs] == [4, 8, 16]
    assert [config.search.paired_options_per_clip for config in configs] == [3, 5, 8]
    assert [config.search.coordinated_options_per_clip for config in configs] == [
        2,
        4,
        8,
    ]
    assert [config.search.maximum_change_fraction for config in configs] == [
        0.25,
        0.60,
        1.0,
    ]


def test_preserve_a_matches_v02_and_preserve_b_keeps_canonical_orientation() -> None:
    clips = fixture_clips()
    clip_a = clips["out_of_key_context"]
    clip_b = clips["out_of_key_melody"]

    legacy = generate_repair(clip_a, clip_b)
    preserve_a = generate_pair_repair(
        clip_a,
        clip_b,
        strategy=EditingStrategy.PRESERVE_A,
    )
    preserve_b = generate_pair_repair(
        clip_a,
        clip_b,
        strategy=EditingStrategy.PRESERVE_B,
    )

    assert preserve_a.changed_note_count_a == 0
    assert preserve_a.repaired_clip_a is clip_a
    assert preserve_a.repaired_clip_b == legacy.repaired_clip
    assert preserve_a.edits_b == legacy.edits
    assert preserve_a.before_analysis == legacy.before_analysis
    assert preserve_a.after_analysis == legacy.after_analysis

    assert preserve_b.changed_note_count_b == 0
    assert preserve_b.repaired_clip_b is clip_b
    assert preserve_b.before_analysis == analyze_pair(clip_a, clip_b)
    assert preserve_b.after_analysis == analyze_pair(
        preserve_b.repaired_clip_a,
        clip_b,
    )


def test_preserve_b_optimizes_the_canonical_pair_with_mismatched_meters() -> None:
    def clip(
        notes: list[tuple[int, int, int]],
        numerator: int,
        denominator: int,
    ) -> MidiClip:
        return MidiClip(
            ticks_per_beat=480,
            notes=tuple(
                MidiNote(
                    id=index,
                    pitch=pitch,
                    onset_ticks=onset,
                    duration_ticks=duration,
                    velocity=90,
                    track=0,
                    channel=0,
                )
                for index, (pitch, onset, duration) in enumerate(notes)
            ),
            time_signature_changes=(
                TimeSignatureChange(0, numerator, denominator),
            ),
        )

    clip_a = clip(
        [(56, 0, 720), (70, 240, 720), (72, 480, 240), (70, 720, 240)],
        3,
        8,
    )
    clip_b = clip(
        [
            (69, 0, 480),
            (68, 240, 480),
            (61, 480, 720),
            (51, 720, 480),
            (54, 960, 240),
            (68, 1200, 240),
        ],
        4,
        4,
    )

    result = generate_pair_repair(clip_a, clip_b, strategy="preserve-b")

    assert result.repaired_score >= result.original_score
    assert result.after_analysis == analyze_pair(result.repaired_clip_a, clip_b)
    assert result.repaired_clip_b is clip_b


def test_shared_compromise_edits_both_and_beats_one_sided_fixture() -> None:
    clips = fixture_clips()
    clip_a = clips["shared_better_a"]
    clip_b = clips["shared_better_b"]

    preserve_a = generate_pair_repair(clip_a, clip_b, strategy="preserve-a")
    preserve_b = generate_pair_repair(clip_a, clip_b, strategy="preserve-b")
    shared = generate_pair_repair(clip_a, clip_b, strategy="shared")

    assert shared.original_score == pytest.approx(53.73660086965387)
    assert shared.changed_note_count_a == 1
    assert shared.changed_note_count_b == 1
    assert [(edit.original_pitch, edit.repaired_pitch) for edit in shared.edits_a] == [
        (66, 64)
    ]
    assert [(edit.original_pitch, edit.repaired_pitch) for edit in shared.edits_b] == [
        (66, 64)
    ]
    assert shared.repaired_score > preserve_a.repaired_score
    assert shared.repaired_score > preserve_b.repaired_score
    assert shared.after_analysis == analyze_pair(
        shared.repaired_clip_a,
        shared.repaired_clip_b,
    )
    assert shared.objective_gain > 0


def test_shared_search_accepts_only_jointly_beneficial_atomic_edits() -> None:
    def chord(pitches: tuple[int, ...]) -> MidiClip:
        return MidiClip(
            ticks_per_beat=480,
            notes=tuple(
                MidiNote(index, pitch, 0, 480, 90, 0, 0)
                for index, pitch in enumerate(pitches)
            ),
        )

    clip_a = chord((49, 60, 65))
    clip_b = chord((49, 60))
    before = analyze_pair(clip_a, clip_b)
    a_only = clip_a.with_notes(
        replace(note, pitch=61) if note.id == 1 else note
        for note in clip_a.notes
    )
    b_only = clip_b.with_notes(
        replace(note, pitch=61) if note.id == 1 else note
        for note in clip_b.notes
    )

    assert analyze_pair(a_only, clip_b).overall_score < before.overall_score
    assert analyze_pair(clip_a, b_only).overall_score < before.overall_score

    repair_config = pair_repair_config_for(
        "shared",
        RepairPreset.MINIMAL,
        preservation_a=0,
        preservation_b=0,
    )
    repair_config = replace(
        repair_config,
        clip_a=replace(
            repair_config.clip_a,
            allow_octave_edits=False,
        ),
        clip_b=replace(
            repair_config.clip_b,
            allow_octave_edits=False,
        ),
    )
    result = generate_pair_repair(clip_a, clip_b, repair_config=repair_config)

    assert [(edit.original_pitch, edit.repaired_pitch) for edit in result.edits_a] == [
        (60, 61)
    ]
    assert [(edit.original_pitch, edit.repaired_pitch) for edit in result.edits_b] == [
        (60, 61)
    ]
    assert result.repaired_score == pytest.approx(84.7277119948137)
    assert result.after_analysis == analyze_pair(
        result.repaired_clip_a,
        result.repaired_clip_b,
    )
    assert result.objective_gain == pytest.approx(6.592470763225359)
    assert all(edit.score_improvement > 0 for edit in result.edits)
    assert result.states_evaluated <= result.repair_config.search.maximum_evaluations


def test_shared_search_is_deterministic_and_explicitly_evaluation_bounded() -> None:
    clips = fixture_clips()
    config = pair_repair_config_for("shared", RepairPreset.BALANCED)

    first = generate_pair_repair(
        clips["shared_better_a"],
        clips["shared_better_b"],
        repair_config=config,
    )
    second = generate_pair_repair(
        clips["shared_better_a"],
        clips["shared_better_b"],
        repair_config=config,
    )

    assert first == second
    assert first.states_evaluated <= config.search.maximum_evaluations
    with pytest.raises(FrozenInstanceError):
        first.repaired_clip_a = first.original_clip_a  # type: ignore[misc]


def test_every_shared_child_is_rescored_as_a_complete_canonical_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clips = fixture_clips()
    clip_a = clips["shared_better_a"]
    clip_b = clips["shared_better_b"]
    original_analyze_pair = pair_module.analyze_pair
    analyzed_pairs: list[tuple[MidiClip, MidiClip]] = []

    def counted(
        left: MidiClip,
        right: MidiClip,
        *,
        config: AnalysisConfig,
    ) -> PairAnalysis:
        analyzed_pairs.append((left, right))
        return original_analyze_pair(left, right, config=config)

    monkeypatch.setattr(pair_module, "analyze_pair", counted)
    result = generate_pair_repair(clip_a, clip_b, strategy="shared")

    assert len(analyzed_pairs) == result.states_evaluated
    assert analyzed_pairs[0] == (clip_a, clip_b)
    assert analyzed_pairs[-1][0].ticks_per_beat == clip_a.ticks_per_beat
    assert analyzed_pairs[-1][1].ticks_per_beat == clip_b.ticks_per_beat
    assert result.after_analysis == original_analyze_pair(
        result.repaired_clip_a,
        result.repaired_clip_b,
    )


def test_custom_preservation_predictably_moves_the_edit_to_cheaper_clip() -> None:
    clips = fixture_clips()
    clip_a = clips["preservation_bias_a"]
    clip_b = clips["preservation_bias_b"]

    favor_a = generate_pair_repair(
        clip_a,
        clip_b,
        strategy="custom",
        preservation_a=0.10,
        preservation_b=0.90,
    )
    favor_b = generate_pair_repair(
        clip_a,
        clip_b,
        strategy="custom",
        preservation_a=0.90,
        preservation_b=0.10,
    )

    assert (favor_a.changed_note_count_a, favor_a.changed_note_count_b) == (1, 0)
    assert (favor_b.changed_note_count_a, favor_b.changed_note_count_b) == (0, 1)
    assert favor_a.repaired_score == pytest.approx(favor_b.repaired_score)
    assert favor_a.preservation_a == pytest.approx(0.10)
    assert favor_b.preservation_b == pytest.approx(0.10)


def test_full_preservation_is_a_hard_lock_and_both_locked_is_clear() -> None:
    clips = fixture_clips()
    clip_a = clips["both_locked_a"]
    clip_b = clips["both_locked_b"]

    only_b = generate_pair_repair(
        clip_a,
        clip_b,
        strategy="custom",
        preservation_a=1.0,
        preservation_b=0.10,
    )

    assert only_b.changed_note_count_a == 0
    assert only_b.repaired_clip_a is clip_a
    assert only_b.changed_note_count_b > 0
    with pytest.raises(RepairConstraintError, match="Both clips are fully preserved"):
        generate_pair_repair(
            clip_a,
            clip_b,
            strategy="custom",
            preservation_a=100,
            preservation_b=100,
        )


@pytest.mark.parametrize("preset", tuple(RepairPreset))
def test_custom_full_preservation_hard_locks_each_side_for_every_preset(
    preset: RepairPreset,
) -> None:
    clips = fixture_clips()
    context = clips["repair_one_note_context"]
    source = clips["repair_one_note_source"]

    keep_a = generate_pair_repair(
        context,
        source,
        strategy=EditingStrategy.CUSTOM,
        preset=preset,
        preservation_a=100,
        preservation_b=0,
    )
    keep_b = generate_pair_repair(
        source,
        context,
        strategy=EditingStrategy.CUSTOM,
        preset=preset,
        preservation_a=0,
        preservation_b=100,
    )

    assert keep_a.changed_note_count_a == 0
    assert keep_a.edits_a == ()
    assert keep_a.repaired_clip_a is context
    assert keep_a.changed_note_count_b > 0
    assert keep_a.has_improvement

    assert keep_b.changed_note_count_b == 0
    assert keep_b.edits_b == ()
    assert keep_b.repaired_clip_b is context
    assert keep_b.changed_note_count_a > 0
    assert keep_b.has_improvement


def test_joint_repair_is_pitch_only_and_introduces_no_same_voice_collisions() -> None:
    clips = fixture_clips()
    clip_a = clips["shared_better_a"]
    clip_b = clips["shared_better_b"]

    result = generate_pair_repair(clip_a, clip_b, strategy="shared")

    _assert_pitch_only(clip_a, result.repaired_clip_a)
    _assert_pitch_only(clip_b, result.repaired_clip_b)
    assert _new_same_voice_collisions(clip_a, result.repaired_clip_a) == []
    assert _new_same_voice_collisions(clip_b, result.repaired_clip_b) == []
    assert result.total_pitch_displacement == 4
    assert result.retention_a == pytest.approx(0.75)
    assert result.retention_b == pytest.approx(0.75)


def test_unison_penalty_prevents_naive_parallel_line_collapse() -> None:
    clips = fixture_clips()
    clip_a = clips["unison_collapse_a"]
    clip_b = clips["unison_collapse_b"]
    guarded_config = pair_repair_config_for(
        "shared",
        RepairPreset.CREATIVE,
        preservation_a=0.20,
        preservation_b=0.20,
    )
    unguarded_config = replace(
        guarded_config,
        objective=replace(
            JointObjectiveWeights(),
            preservation=8.0,
            introduced_unison=0.0,
            convergence=0.0,
        ),
    )

    guarded = generate_pair_repair(clip_a, clip_b, repair_config=guarded_config)
    unguarded = generate_pair_repair(clip_a, clip_b, repair_config=unguarded_config)
    guarded_unisons = sum(
        note_a.pitch == note_b.pitch
        for note_a, note_b in zip(
            guarded.repaired_clip_a.notes,
            guarded.repaired_clip_b.notes,
            strict=True,
        )
    )
    unguarded_unisons = sum(
        note_a.pitch == note_b.pitch
        for note_a, note_b in zip(
            unguarded.repaired_clip_a.notes,
            unguarded.repaired_clip_b.notes,
            strict=True,
        )
    )

    assert unguarded_unisons == 4
    assert guarded_unisons == 0
    assert (
        guarded.changed_note_count_a
        <= guarded.repair_config.clip_a.max_note_changes
    )
    assert (
        guarded.changed_note_count_b
        <= guarded.repair_config.clip_b.max_note_changes
    )
    assert unguarded.repaired_score > guarded.repaired_score
    assert guarded.score_improvement > 0


def test_pair_result_rejects_misreported_or_untracked_edits() -> None:
    clips = fixture_clips()
    result = generate_pair_repair(
        clips["shared_better_a"],
        clips["shared_better_b"],
        strategy="shared",
    )
    untracked = result.original_clip_a.with_notes(
        replace(note, pitch=note.pitch + 1) if note.id == 0 else note
        for note in result.original_clip_a.notes
    )

    with pytest.raises(ValueError, match="without an edit"):
        replace(result, repaired_clip_a=untracked, edits_a=())


def test_pair_result_rejects_non_pitch_changes_on_an_edited_note() -> None:
    clips = fixture_clips()
    result = generate_pair_repair(
        clips["shared_better_a"],
        clips["shared_better_b"],
        strategy="shared",
    )
    edited_id = result.edits_a[0].note_id
    structurally_changed = result.repaired_clip_a.with_notes(
        replace(note, duration_ticks=note.duration_ticks + 1)
        if note.id == edited_id
        else note
        for note in result.repaired_clip_a.notes
    )

    with pytest.raises(ValueError, match="changed non-pitch fields"):
        replace(result, repaired_clip_a=structurally_changed)


def test_custom_constraints_can_disable_octaves_without_enabling_rhythm() -> None:
    clips = fixture_clips()
    constraints_a = ClipRepairConstraints(
        preservation=1.0,
        allow_pitch_edits=False,
        allow_octave_edits=False,
        max_note_changes=0,
    )
    constraints_b = ClipRepairConstraints(
        preservation=0.0,
        allow_octave_edits=False,
        max_note_changes=1,
    )

    result = generate_pair_repair(
        clips["register_a"],
        clips["register_collision_b"],
        strategy="custom",
        constraints_a=constraints_a,
        constraints_b=constraints_b,
    )

    assert result.changed_note_count_a == 0
    assert all(not edit.is_octave_move for edit in result.edits_b)
