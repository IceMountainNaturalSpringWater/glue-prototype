from __future__ import annotations

from dataclasses import replace

import pytest

import glue.fixes.single as single_module
from glue.analysis import (
    KeyEstimate,
    SingleAnalysisConfig,
    SingleClipAnalysis,
    SingleClipSuggestion,
    SingleSuggestionCategory,
    analyze_single_clip,
)
from glue.fixes import (
    RepairPreset,
    generate_single_repair,
    single_repair_config_for,
)
from glue.models import (
    MidiClip,
    MidiNote,
    TempoChange,
    TimeSignatureChange,
    TrackInfo,
)
from scripts.generate_fixtures import fixture_clips

TICKS_PER_BEAT = 480


def _clip(note_count: int) -> MidiClip:
    return MidiClip(
        ticks_per_beat=TICKS_PER_BEAT,
        notes=tuple(
            MidiNote(
                id=index,
                pitch=60 + index * 2,
                onset_ticks=index * TICKS_PER_BEAT,
                duration_ticks=TICKS_PER_BEAT,
                velocity=70 + index,
                release_velocity=index,
                track=0,
                channel=1,
            )
            for index in range(note_count)
        ),
        tempo_changes=(TempoChange(0, 510_000),),
        time_signature_changes=(TimeSignatureChange(0, 3, 4),),
        tracks=(TrackInfo(0, "Single repair test", note_count * TICKS_PER_BEAT),),
        length_ticks=note_count * TICKS_PER_BEAT,
        name="single-repair-test",
        midi_type=1,
    )


def _suggestion(
    note: MidiNote,
    *,
    suggestion_id: str | None = None,
    alternatives: tuple[int, ...] | None = None,
    confidence: float = 0.90,
) -> SingleClipSuggestion:
    return SingleClipSuggestion(
        suggestion_id=suggestion_id or f"test:{note.id}",
        target_note_id=note.id,
        related_note_ids=(),
        original_pitch=note.pitch,
        onset_ticks=note.onset_ticks,
        duration_ticks=note.duration_ticks,
        track=note.track,
        channel=note.channel,
        onset_beats=note.onset_ticks / TICKS_PER_BEAT,
        duration_beats=note.duration_ticks / TICKS_PER_BEAT,
        category=SingleSuggestionCategory.HARMONIC_CONFLICT,
        confidence=confidence,
        explanation="Possible harmonic conflict.",
        alternatives=alternatives or (note.pitch + 1,),
    )


def _analysis(
    score: float,
    suggestions: tuple[SingleClipSuggestion, ...],
) -> SingleClipAnalysis:
    return SingleClipAnalysis(
        key=KeyEstimate.unknown(),
        harmonic_score=score,
        melodic_score=score,
        voice_leading_score=score,
        overlap_score=score,
        register_score=score,
        bass_score=score,
        motif_score=score,
        internal_consistency_score=score,
        suggestions=suggestions,
    )


def _install_linear_scorer(
    monkeypatch: pytest.MonkeyPatch,
    original: MidiClip,
    suggestions: tuple[SingleClipSuggestion, ...],
    *,
    gain_per_edit: float = 10.0,
) -> SingleClipAnalysis:
    original_pitch = {note.id: note.pitch for note in original.notes}

    def score(
        candidate: MidiClip,
        *,
        config: SingleAnalysisConfig,
    ) -> SingleClipAnalysis:
        del config
        changed = sum(
            note.pitch != original_pitch[note.id] for note in candidate.notes
        )
        return _analysis(20.0 + gain_per_edit * changed, suggestions)

    monkeypatch.setattr(single_module, "analyze_single_clip", score)
    return score(original, config=SingleAnalysisConfig())


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
    for repaired_note in repaired.notes:
        source = original_by_id[repaired_note.id]
        assert repaired_note == replace(source, pitch=repaired_note.pitch)


def test_single_presets_have_strict_edit_budgets_and_rescore_complete_clip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clip = _clip(6)
    suggestions = tuple(_suggestion(note) for note in clip.notes)
    before = _install_linear_scorer(monkeypatch, clip, suggestions)

    results = tuple(
        generate_single_repair(
            clip,
            analysis=before,
            preset=preset,
            preservation=0,
        )
        for preset in RepairPreset
    )

    assert [result.changed_note_count for result in results] == [1, 3, 6]
    assert [result.repaired_score for result in results] == [30.0, 50.0, 80.0]
    assert all(result.has_improvement for result in results)
    assert all(result.states_evaluated > 1 for result in results)
    for result in results:
        _assert_pitch_only(clip, result.repaired_clip)
        assert result.after_analysis.internal_consistency_score == (
            20.0 + 10.0 * result.changed_note_count
        )


def test_lower_preservation_broadens_creative_and_100_percent_hard_locks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clip = _clip(6)
    suggestions = tuple(_suggestion(note) for note in clip.notes)
    before = _install_linear_scorer(
        monkeypatch,
        clip,
        suggestions,
        gain_per_edit=12.0,
    )

    low = generate_single_repair(
        clip,
        analysis=before,
        preset=RepairPreset.CREATIVE,
        preservation=0,
    )
    high = generate_single_repair(
        clip,
        analysis=before,
        preset=RepairPreset.CREATIVE,
        preservation=85,
    )
    locked = generate_single_repair(
        clip,
        analysis=before,
        preset=RepairPreset.CREATIVE,
        preservation=100,
    )

    assert low.changed_note_count == 6
    assert high.changed_note_count == 2
    assert locked.changed_note_count == 0
    assert locked.repaired_clip is clip
    assert not locked.has_improvement
    assert locked.no_improvement_reason == (
        "Preservation is 100%; no edits are allowed."
    )


def test_only_enabled_suggestion_targets_and_alternatives_can_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clip = _clip(3)
    suggestions = tuple(_suggestion(note) for note in clip.notes)
    before = _install_linear_scorer(monkeypatch, clip, suggestions)

    result = generate_single_repair(
        clip,
        analysis=before,
        enabled_suggestion_ids={suggestions[1].suggestion_id},
        preset=RepairPreset.CREATIVE,
        preservation=0,
    )
    none_enabled = generate_single_repair(
        clip,
        analysis=before,
        enabled_suggestion_ids=set(),
        preset=RepairPreset.CREATIVE,
        preservation=0,
    )

    assert [edit.note_id for edit in result.edits] == [1]
    assert result.edits[0].repaired_pitch == suggestions[1].alternatives[0]
    assert result.suggestion_ids_for_edit(1) == (
        suggestions[1].suggestion_id,
    )
    assert none_enabled.changed_note_count == 0
    assert "No suggestions are enabled" in none_enabled.stop_reason

    with pytest.raises(ValueError, match="unknown enabled suggestion id"):
        generate_single_repair(
            clip,
            analysis=before,
            enabled_suggestion_ids={"missing"},
            preservation=0,
        )


def test_creative_finds_coordinated_pair_when_atomic_edits_are_worse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clip = _clip(2)
    suggestions = tuple(_suggestion(note) for note in clip.notes)
    target_pitch = {
        note.id: suggestion.alternatives[0]
        for note, suggestion in zip(clip.notes, suggestions, strict=True)
    }

    def synergistic_score(
        candidate: MidiClip,
        *,
        config: SingleAnalysisConfig,
    ) -> SingleClipAnalysis:
        del config
        changed = sum(
            note.pitch == target_pitch[note.id] for note in candidate.notes
        )
        score = {0: 50.0, 1: 49.0, 2: 75.0}[changed]
        return _analysis(score, suggestions)

    monkeypatch.setattr(
        single_module,
        "analyze_single_clip",
        synergistic_score,
    )
    before = synergistic_score(clip, config=SingleAnalysisConfig())

    minimal = generate_single_repair(
        clip,
        analysis=before,
        preset=RepairPreset.MINIMAL,
        preservation=0,
    )
    creative = generate_single_repair(
        clip,
        analysis=before,
        preset=RepairPreset.CREATIVE,
        preservation=0,
    )

    assert minimal.changed_note_count == 0
    assert creative.changed_note_count == 2
    assert creative.repaired_score == 75.0
    assert creative.score_improvement == 25.0
    for edit in creative.edits:
        partial = _replace_one(clip, edit.note_id, edit.repaired_pitch)
        assert synergistic_score(
            partial,
            config=SingleAnalysisConfig(),
        ).internal_consistency_score < before.internal_consistency_score


def _replace_one(clip: MidiClip, note_id: int, pitch: int) -> MidiClip:
    return clip.with_notes(
        replace(note, pitch=pitch) if note.id == note_id else note
        for note in clip.notes
    )


def test_no_improving_candidate_is_not_reported_as_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clip = _clip(1)
    suggestions = (_suggestion(clip.notes[0]),)
    before = _analysis(80.0, suggestions)

    monkeypatch.setattr(
        single_module,
        "analyze_single_clip",
        lambda candidate, *, config: _analysis(80.0, suggestions),
    )
    result = generate_single_repair(
        clip,
        analysis=before,
        preset=RepairPreset.CREATIVE,
        preservation=0,
    )

    assert result.changed_note_count == 0
    assert result.repaired_clip is clip
    assert not result.has_improvement
    assert result.no_improvement_reason is not None
    assert "No improving candidate found" in result.no_improvement_reason
    assert "No valid pitch edit" in result.no_improvement_reason


def test_real_accidental_repairs_and_intentional_chromatic_default_stays(
) -> None:
    clips = fixture_clips()
    accidental = clips["single_obvious_accidental"]
    chromatic = clips["single_intentional_chromatic"]
    accidental_analysis = analyze_single_clip(accidental)
    chromatic_analysis = analyze_single_clip(chromatic)

    repaired = generate_single_repair(
        accidental,
        analysis=accidental_analysis,
        preset=RepairPreset.MINIMAL,
        preservation=0,
    )
    preserved = generate_single_repair(
        chromatic,
        analysis=chromatic_analysis,
        preset=RepairPreset.CREATIVE,
        preservation=0,
    )

    assert repaired.has_improvement
    assert [(edit.note_id, edit.original_pitch, edit.repaired_pitch) for edit in repaired.edits] == [
        (5, 78, 79)
    ]
    assert repaired.repaired_score > repaired.original_score
    assert preserved.changed_note_count == 0
    assert preserved.repaired_clip is chromatic
    assert [note.pitch for note in preserved.repaired_clip.notes] == [
        note.pitch for note in chromatic.notes
    ]


def test_single_configs_reuse_strict_shared_preset_calibration() -> None:
    configs = [
        single_repair_config_for(preset, preservation=0)
        for preset in RepairPreset
    ]

    assert [config.maximum_note_changes for config in configs] == [2, 4, 8]
    assert [config.search.maximum_evaluations for config in configs] == [
        800,
        2_000,
        5_000,
    ]
    assert [config.maximum_bundle_size for config in configs] == [1, 2, 8]
    assert all(
        single_repair_config_for(preset, 100).is_locked
        for preset in RepairPreset
    )

    zero_budget = replace(
        single_repair_config_for(RepairPreset.CREATIVE, 50),
        maximum_note_changes=0,
    )
    outcome = generate_single_repair(
        fixture_clips()["single_obvious_accidental"],
        repair_config=zero_budget,
    )
    assert outcome.changed_note_count == 0
    assert outcome.stop_reason == (
        "The configured repair budget is zero; no edits are allowed."
    )


def test_single_repair_rejects_stale_analysis_and_config_mismatch() -> None:
    clip = fixture_clips()["single_obvious_accidental"]
    analysis = analyze_single_clip(clip)
    altered = clip.with_notes(
        replace(note, pitch=note.pitch - 12) if note.id == 0 else note
        for note in clip.notes
    )

    with pytest.raises(ValueError, match="does not match"):
        generate_single_repair(
            altered,
            analysis=analysis,
            preset=RepairPreset.CREATIVE,
            preservation=0,
        )

    with pytest.raises(ValueError, match="different analysis configuration"):
        generate_single_repair(
            clip,
            analysis=analysis,
            analysis_config=SingleAnalysisConfig(
                high_confidence_threshold=0.9,
            ),
            preset=RepairPreset.CREATIVE,
            preservation=0,
        )

    with pytest.raises(TypeError, match="SingleRepairConfig"):
        generate_single_repair(
            clip,
            repair_config=object(),  # type: ignore[arg-type]
        )
