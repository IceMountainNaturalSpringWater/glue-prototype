from __future__ import annotations

from dataclasses import replace

import pytest

from glue.analysis import (
    DEFAULT_SINGLE_ANALYSIS_CONFIG,
    SingleAnalysisConfig,
    SingleClipAnalysis,
    SingleClipSuggestion,
    SingleSuggestionCategory,
    analyze_single,
    analyze_single_clip,
)
from glue.models import MidiClip, MidiNote
from scripts.generate_fixtures import fixture_clips


def _suggestions_for(
    fixture: str,
    category: SingleSuggestionCategory,
) -> tuple[SingleClipSuggestion, ...]:
    result = analyze_single_clip(fixture_clips()[fixture])
    return tuple(
        suggestion
        for suggestion in result.suggestions
        if suggestion.category is category
    )


@pytest.mark.parametrize(
    ("fixture", "category", "target_pitch"),
    (
        (
            "single_obvious_accidental",
            SingleSuggestionCategory.HARMONIC_CONFLICT,
            78,
        ),
        (
            "single_awkward_leap",
            SingleSuggestionCategory.MELODIC_LEAP,
            79,
        ),
        (
            "single_poor_voice_leading",
            SingleSuggestionCategory.VOICE_LEADING,
            79,
        ),
        (
            "single_duplicate_overlap",
            SingleSuggestionCategory.DUPLICATE_OVERLAP,
            60,
        ),
        (
            "single_register_crowding",
            SingleSuggestionCategory.REGISTER_CROWDING,
            60,
        ),
        (
            "single_bass_conflict",
            SingleSuggestionCategory.BASS_CONFLICT,
            49,
        ),
        (
            "single_motif_inconsistency",
            SingleSuggestionCategory.MOTIF_INCONSISTENCY,
            65,
        ),
    ),
)
def test_required_single_clip_categories_are_detected_at_expected_notes(
    fixture: str,
    category: SingleSuggestionCategory,
    target_pitch: int,
) -> None:
    suggestions = _suggestions_for(fixture, category)

    assert suggestions
    assert any(suggestion.original_pitch == target_pitch for suggestion in suggestions)
    assert all(0 <= suggestion.confidence <= 1 for suggestion in suggestions)
    assert all(suggestion.alternatives for suggestion in suggestions)


def test_single_analysis_is_deterministic_typed_and_stably_ordered() -> None:
    clip = fixture_clips()["single_coordinated_repair"]

    first = analyze_single_clip(clip)
    second = analyze_single(clip)

    assert isinstance(first, SingleClipAnalysis)
    assert first == second
    assert len({suggestion.id for suggestion in first.suggestions}) == len(
        first.suggestions
    )
    category_order = {
        category: index for index, category in enumerate(SingleSuggestionCategory)
    }
    assert first.suggestions == tuple(
        sorted(
            first.suggestions,
            key=lambda suggestion: (
                suggestion.onset_ticks,
                category_order[suggestion.category],
                suggestion.target_note_id,
                suggestion.related_note_ids,
                suggestion.alternatives,
            ),
        )
    )


def test_suggestions_expose_traceable_location_and_neutral_language() -> None:
    clips = fixture_clips()
    forbidden = ("wrong", "mistake", "incorrect", "bad note", "must change")

    for name in (
        "single_obvious_accidental",
        "single_awkward_leap",
        "single_poor_voice_leading",
        "single_duplicate_overlap",
        "single_register_crowding",
        "single_bass_conflict",
        "single_motif_inconsistency",
    ):
        clip = clips[name]
        notes_by_id = {note.id: note for note in clip.notes}
        for suggestion in analyze_single_clip(clip).suggestions:
            note = notes_by_id[suggestion.target_note_id]
            assert suggestion.location == (
                note.track,
                note.channel,
                note.onset_ticks,
                note.duration_ticks,
            )
            assert suggestion.original_pitch == note.pitch
            assert suggestion.onset_beats == pytest.approx(
                note.onset_ticks / clip.ticks_per_beat
            )
            assert suggestion.duration_beats == pytest.approx(
                note.duration_ticks / clip.ticks_per_beat
            )
            assert suggestion.explanation.startswith("Possible ")
            assert not any(
                phrase in suggestion.explanation.lower() for phrase in forbidden
            )
            assert all(
                0 <= pitch <= 127 and pitch != note.pitch
                for pitch in suggestion.alternatives
            )


def test_obvious_accidental_is_primary_but_stepwise_chromatic_note_is_secondary() -> None:
    clips = fixture_clips()
    accidental = analyze_single_clip(clips["single_obvious_accidental"])
    chromatic = analyze_single_clip(clips["single_intentional_chromatic"])

    obvious = next(
        suggestion
        for suggestion in accidental.high_confidence_suggestions
        if suggestion.original_pitch == 78
    )
    passing = next(
        suggestion
        for suggestion in chromatic.secondary_suggestions
        if suggestion.original_pitch == 63
    )

    assert {77, 79} <= set(obvious.alternatives)
    assert passing.id not in chromatic.default_enabled_suggestion_ids
    assert all(
        suggestion.original_pitch != 63
        for suggestion in chromatic.high_confidence_suggestions
    )
    assert "intentional chromatic motion" in passing.explanation


def test_motif_analysis_finds_exact_inconsistent_positions_and_coordinated_pair() -> None:
    one = _suggestions_for(
        "single_motif_inconsistency",
        SingleSuggestionCategory.MOTIF_INCONSISTENCY,
    )
    coordinated = _suggestions_for(
        "single_coordinated_repair",
        SingleSuggestionCategory.MOTIF_INCONSISTENCY,
    )

    assert [(item.original_pitch, item.alternatives) for item in one] == [
        (65, (64,))
    ]
    assert [(item.original_pitch, item.alternatives) for item in coordinated] == [
        (63, (62,)),
        (65, (64,)),
    ]


def test_duplicate_overlap_names_both_source_notes_without_requesting_deletion() -> None:
    suggestion = _suggestions_for(
        "single_duplicate_overlap",
        SingleSuggestionCategory.DUPLICATE_OVERLAP,
    )[0]

    assert len(suggestion.affected_note_ids) == 2
    assert suggestion.target_note_id not in suggestion.related_note_ids
    assert suggestion.confidence > 0.9
    assert all(isinstance(pitch, int) for pitch in suggestion.alternatives)


def test_component_weighting_and_clean_material_are_transparent() -> None:
    clean = analyze_single_clip(fixture_clips()["single_no_improvement"])
    weighted = sum(
        score * weight
        for score, weight in zip(
            clean.component_scores.values(),
            DEFAULT_SINGLE_ANALYSIS_CONFIG.component_weights,
            strict=True,
        )
    )

    assert clean.suggestions == ()
    assert clean.high_confidence_suggestions == ()
    assert clean.secondary_suggestions == ()
    assert clean.default_enabled_suggestion_ids == frozenset()
    assert clean.internal_consistency_score == pytest.approx(weighted)
    assert clean.score == clean.overall_score == 100
    assert clean.key_estimate == clean.estimated_key == clean.key


def test_percussion_is_ignored_by_single_pitch_analysis() -> None:
    clip = MidiClip(
        ticks_per_beat=480,
        notes=tuple(
            MidiNote(
                id=index,
                pitch=pitch,
                onset_ticks=0,
                duration_ticks=480,
                velocity=100,
                track=0,
                channel=9,
            )
            for index, pitch in enumerate((36, 38, 42, 46))
        ),
    )

    result = analyze_single_clip(clip)

    assert result.key.label == "Unknown"
    assert result.suggestions == ()
    assert result.score == 100


@pytest.mark.parametrize(
    ("changes", "message"),
    (
        ({"high_confidence_threshold": 1.1}, "between 0 and 1"),
        ({"window_beats": float("nan")}, "positive"),
        ({"window_beats": float("inf")}, "positive"),
        ({"maximum_alternatives": 0}, "positive"),
        ({"motif_minimum_length": 5}, "must not exceed"),
        ({"harmonic_weight": 0.31}, "sum to 1"),
        ({"harmonic_weight": float("nan")}, "finite"),
    ),
)
def test_single_analysis_config_rejects_invalid_policy(
    changes: dict[str, object],
    message: str,
) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        replace(DEFAULT_SINGLE_ANALYSIS_CONFIG, **changes)


def test_single_analysis_rejects_non_clip_input() -> None:
    with pytest.raises(TypeError, match="MidiClip"):
        analyze_single_clip(object())  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="SingleAnalysisConfig"):
        analyze_single_clip(
            fixture_clips()["single_no_improvement"],
            config=object(),  # type: ignore[arg-type]
        )


def test_custom_confidence_threshold_controls_primary_secondary_partition() -> None:
    config = SingleAnalysisConfig(high_confidence_threshold=0.9)
    clip = fixture_clips()["single_obvious_accidental"]
    result = analyze_single_clip(clip, config=config)

    assert result.high_confidence_suggestions == ()
    assert result.secondary_suggestions == result.suggestions
    assert result.default_enabled_suggestion_ids == frozenset()
    assert result.analyzed_clip is clip
    assert result.analysis_config == config
