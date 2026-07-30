from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

import glue.analysis as analysis_module
import glue.fixes as fixes_module
from glue.analysis import analyze_pair
from glue.fixes import BalanceSuggestion, suggest_preservation_balance
from scripts.generate_fixtures import fixture_clips


def test_clear_asymmetric_fixture_gets_a_confident_cautious_direction() -> None:
    clips = fixture_clips()
    clip_a = clips["demo_preset_context"]
    clip_b = clips["demo_preset_source"]
    analysis = analyze_pair(clip_a, clip_b)

    suggestion = suggest_preservation_balance(clip_a, clip_b, analysis)

    assert (suggestion.preservation_a, suggestion.preservation_b) == (95, 65)
    assert suggestion.is_confident
    assert suggestion.confidence_label == "confident"
    assert suggestion.confidence >= 0.60
    assert "Clip A receives higher preservation" in suggestion.explanation
    assert "not objective musical blame" in suggestion.explanation


def test_swapping_clips_swaps_the_direction_and_preserves_confidence() -> None:
    clips = fixture_clips()
    clip_a = clips["demo_preset_context"]
    clip_b = clips["demo_preset_source"]

    forward = suggest_preservation_balance(
        clip_a,
        clip_b,
        analyze_pair(clip_a, clip_b),
    )
    reverse = suggest_preservation_balance(
        clip_b,
        clip_a,
        analyze_pair(clip_b, clip_a),
    )

    assert (reverse.preservation_a, reverse.preservation_b) == (
        forward.preservation_b,
        forward.preservation_a,
    )
    assert reverse.confidence == pytest.approx(forward.confidence)
    assert reverse.is_confident
    assert "Clip B receives higher preservation" in reverse.explanation


def test_identical_or_ambiguous_evidence_keeps_the_neutral_balance() -> None:
    clips = fixture_clips()
    clip_a = clips["identical_a"]
    clip_b = clips["identical_b"]

    suggestion = suggest_preservation_balance(
        clip_a,
        clip_b,
        analyze_pair(clip_a, clip_b),
    )

    assert (suggestion.preservation_a, suggestion.preservation_b) == (50, 50)
    assert not suggestion.is_confident
    assert suggestion.confidence_label == "low confidence"
    assert suggestion.explanation.startswith("No strong recommendation:")


def test_no_overlapping_activity_returns_an_honest_neutral_suggestion() -> None:
    clips = fixture_clips()
    clip_a = clips["identical_a"]
    clip_b = clips["identical_b"].with_notes(
        replace(
            note,
            onset_ticks=note.onset_ticks + 8 * note.duration_ticks,
        )
        for note in clips["identical_b"].notes
    )
    analysis = analyze_pair(clip_a, clip_b)

    suggestion = suggest_preservation_balance(clip_a, clip_b, analysis)

    assert sum(window.activity_weight for window in analysis.windows) == 0
    assert (suggestion.preservation_a, suggestion.preservation_b) == (50, 50)
    assert suggestion.confidence == 0
    assert not suggestion.is_confident
    assert "no comparable overlapping activity" in suggestion.explanation


def test_suggestion_is_deterministic_and_uses_only_the_provided_analysis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clips = fixture_clips()
    clip_a = clips["demo_preset_context"]
    clip_b = clips["demo_preset_source"]
    cached_analysis = analyze_pair(clip_a, clip_b)

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("suggestion must not analyze or generate a repair")

    monkeypatch.setattr(analysis_module, "analyze_pair", forbidden)
    monkeypatch.setattr(fixes_module, "generate_pair_repair", forbidden)

    first = suggest_preservation_balance(clip_a, clip_b, cached_analysis)
    second = suggest_preservation_balance(clip_a, clip_b, cached_analysis)

    assert first == second


def test_suggestion_is_bounded_immutable_and_does_not_mutate_clips() -> None:
    clips = fixture_clips()
    clip_a = clips["demo_preset_context"]
    clip_b = clips["demo_preset_source"]
    original_a = clip_a
    original_b = clip_b

    suggestion = suggest_preservation_balance(
        clip_a,
        clip_b,
        analyze_pair(clip_a, clip_b),
    )

    assert 0 <= suggestion.preservation_a < 100
    assert 0 <= suggestion.preservation_b < 100
    assert 0 <= suggestion.confidence <= 1
    assert clip_a == original_a
    assert clip_b == original_b
    with pytest.raises(FrozenInstanceError):
        suggestion.preservation_a = 50  # type: ignore[misc]

    with pytest.raises(ValueError, match="never hard-lock"):
        BalanceSuggestion(100, 85, 0.5, "invalid")
    with pytest.raises(ValueError, match="between 0 and 1"):
        BalanceSuggestion(85, 85, 1.1, "invalid")
    with pytest.raises(ValueError, match="must not be empty"):
        BalanceSuggestion(85, 85, 0.0, "   ")
