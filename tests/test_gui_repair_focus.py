from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_OPENGL", "software")
os.environ.setdefault("QT_API", "pyside6")

from PySide6.QtWidgets import QApplication, QPushButton

import glue.ui.main_window as main_window_module
from glue.fixes import EditingStrategy
from glue.ui import MainWindow
from scripts.generate_fixtures import generate_fixtures


def test_repair_is_primary_auto_analyzes_and_reuses_cached_analysis(
    tmp_path: Path,
    monkeypatch,
) -> None:
    generated = generate_fixtures(tmp_path / "fixtures")
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    window.set_preservation_values(100, 70)

    analysis_observations: list[tuple[bool, bool, str]] = []
    repair_observations: list[tuple[bool, bool, str]] = []
    repair_arguments: list[dict[str, object]] = []
    original_analyze_pair = main_window_module.analyze_pair
    original_generate_pair_repair = main_window_module.generate_pair_repair

    def counted_analyze_pair(*args, **kwargs):
        analysis_observations.append(
            (
                window.is_busy,
                not window.busy_indicator.isHidden(),
                window.busy_status_label.text(),
            )
        )
        return original_analyze_pair(*args, **kwargs)

    def observed_repair(*args, **kwargs):
        repair_observations.append(
            (
                window.is_busy,
                not window.busy_indicator.isHidden(),
                window.busy_status_label.text(),
            )
        )
        repair_arguments.append(dict(kwargs))
        return original_generate_pair_repair(*args, **kwargs)

    monkeypatch.setattr(main_window_module, "analyze_pair", counted_analyze_pair)
    monkeypatch.setattr(
        main_window_module,
        "generate_pair_repair",
        observed_repair,
    )

    window.load_clip("A", generated["out_of_key_context"])
    window.load_clip("B", generated["out_of_key_melody"])
    application.processEvents()

    assert window.pair_analysis is None
    assert window.repair_button.isEnabled()
    assert "automatically" in window.repair_button.toolTip()
    assert not window.analysis_toggle_button.isChecked()
    assert window.analysis_details_panel.isHidden()
    assert window.analysis_details_panel.isAncestorOf(window.timeline)
    assert window.analysis_details_panel.isAncestorOf(window.diagnosis_list)
    assert window.analysis_details_panel.isAncestorOf(window.harmonic_score_label)
    assert window.analysis_details_panel.isAncestorOf(window.key_a_label)
    assert window.analysis_details_panel.isAncestorOf(window.key_b_label)
    assert not window.analysis_details_panel.isAncestorOf(window.overall_score_label)
    assert window.compatibility_estimate_group.isAncestorOf(window.analyze_button)
    assert window.compatibility_estimate_group.isAncestorOf(
        window.overall_score_label
    )
    assert window.compatibility_estimate_group.isAncestorOf(
        window.analysis_toggle_button
    )
    assert window.compatibility_estimate_group.isAncestorOf(
        window.busy_status_label
    )
    assert window.compatibility_estimate_group.isAncestorOf(window.busy_indicator)
    assert window.overall_score_label.isVisible()
    assert window.analyze_button.geometry().bottom() <= (
        window.overall_score_label.geometry().top()
    )
    assert window.overall_score_label.geometry().bottom() <= (
        window.analysis_toggle_button.geometry().top()
    )
    assert window.findChildren(
        QPushButton,
        "analysisDetailsToggle",
    ) == [window.analysis_toggle_button]
    root_layout = window.combine_page.layout()
    workspace = window.details_scroll_area.parentWidget()
    assert root_layout.indexOf(window.analysis_details_panel) < root_layout.indexOf(
        workspace
    )
    assert window.repair_group.objectName() == "repairWorkflowGroup"
    assert window.repair_group.isVisible()
    central_size = window.centralWidget().size()
    assert window.details_scroll_area.height() >= central_size.height() * 0.65
    assert window.details_scroll_area.width() >= central_size.width() * 0.25

    window.repair_button.click()
    application.processEvents()

    result = window.repair_result
    assert result is not None
    assert result.changed_note_count > 0
    assert result.score_improvement > 0
    assert len(analysis_observations) == 1
    assert analysis_observations[0][0:2] == (True, True)
    assert "Analyzing compatibility" in analysis_observations[0][2]
    assert len(repair_observations) == 1
    assert repair_observations[0][0:2] == (True, True)
    assert "Generating Minimal repair" in repair_observations[0][2]
    assert len(repair_arguments) == 1
    assert repair_arguments[0] == {
        "strategy": EditingStrategy.CUSTOM,
        "preset": result.preset,
        "preservation_a": 100,
        "preservation_b": 70,
    }
    assert not hasattr(window, "generate_strategy_comparison")
    assert window.busy_indicator.isHidden()
    assert window.busy_status_label.text() == "Ready"
    assert window.analysis_details_panel.isHidden()
    assert window.overall_score_label.isVisible()
    assert "before:" in window.repair_score_summary_label.text()
    assert "after:" in window.repair_score_summary_label.text()
    assert "improvement:" in window.repair_score_summary_label.text()

    first_analysis = window.pair_analysis
    window.analyze_button.click()
    window.analyze_button.click()
    application.processEvents()
    assert window.pair_analysis is first_analysis
    assert len(analysis_observations) == 1

    window.analysis_toggle_button.setChecked(True)
    application.processEvents()
    assert window.analysis_details_panel.isVisible()
    assert window.timeline.isVisible()
    assert window.diagnosis_list.isVisible()
    assert window.harmonic_score_label.isVisible()
    assert window.bass_score_label.isVisible()
    assert window.register_score_label.isVisible()
    assert window.rhythm_score_label.isVisible()
    assert window.overall_score_label.isVisible()
    assert window.analysis_toggle_button.text() == "Hide analysis details"
    window.analysis_toggle_button.setChecked(False)
    application.processEvents()
    assert window.analysis_details_panel.isHidden()
    assert window.overall_score_label.isVisible()
    window.close()


def test_zero_edit_result_is_explained_but_not_retained_or_exportable(
    tmp_path: Path,
) -> None:
    generated = generate_fixtures(tmp_path / "fixtures")
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.load_clip("A", generated["identical_a"])
    window.load_clip("B", generated["identical_b"])
    window.set_preservation_values(100, 70)

    result = window.repair_selected()
    application.processEvents()

    assert result.changed_note_count == 0
    assert result.score_improvement == 0
    assert window.repair_candidate_count == 0
    assert window.candidate_list.count() == 0
    assert window.repair_result is None
    assert window.repaired_slot is None
    assert not window.export_button.isEnabled()
    assert not window.export_a_button.isEnabled()
    assert not window.export_b_button.isEnabled()
    assert not window.export_combined_button.isEnabled()
    assert not window.export_report_button.isEnabled()
    assert not window.export_bundle_button.isEnabled()
    explanation = window.candidate_label.text().lower()
    assert "no improving candidate found" in explanation
    assert "no valid pitch edit improved" in explanation
    assert "preservation may be too high" in explanation
    assert "preset may be too restrictive" in explanation
    assert "after: —" in window.repair_score_summary_label.text()
    assert "improvement: none" in window.repair_score_summary_label.text()
    window.close()


def test_suggest_balance_previews_without_mutating_and_applies_explicitly(
    tmp_path: Path,
    monkeypatch,
) -> None:
    generated = generate_fixtures(tmp_path / "fixtures")
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    window.set_preservation_values(40, 60)
    window.load_clip("A", generated["demo_preset_context"])
    window.load_clip("B", generated["demo_preset_source"])

    observations: list[tuple[bool, bool, str]] = []
    suggestion_calls: list[tuple[object, object, object]] = []
    original_suggest = main_window_module.suggest_preservation_balance

    def observed_suggestion(clip_a, clip_b, analysis):
        observations.append(
            (
                window.is_busy,
                not window.busy_indicator.isHidden(),
                window.busy_status_label.text(),
            )
        )
        suggestion_calls.append((clip_a, clip_b, analysis))
        return original_suggest(clip_a, clip_b, analysis)

    def forbidden_repair(*args, **kwargs):
        raise AssertionError("suggesting a balance must not generate a repair")

    monkeypatch.setattr(
        main_window_module,
        "suggest_preservation_balance",
        observed_suggestion,
    )
    monkeypatch.setattr(
        main_window_module,
        "generate_pair_repair",
        forbidden_repair,
    )

    suggestion = window.suggest_balance()
    application.processEvents()

    assert (suggestion.preservation_a, suggestion.preservation_b) == (95, 65)
    assert suggestion.is_confident
    assert len(suggestion_calls) == 1
    assert suggestion_calls[0][2] is window.pair_analysis
    assert observations == [(True, True, "Suggesting preservation balance…")]
    assert (window.preservation_a_slider.value(), window.preservation_b_slider.value()) == (
        40,
        60,
    )
    assert window.pending_balance_suggestion is suggestion
    assert window.apply_suggestion_button.isEnabled()
    assert "Suggested preservation: A 95% · B 65%" in (
        window.balance_suggestion_label.text()
    )
    assert "Preview only" in window.balance_suggestion_label.text()
    assert window.repair_candidate_count == 0

    cached_analysis = window.pair_analysis
    repeated = window.suggest_balance()
    assert repeated == suggestion
    assert len(suggestion_calls) == 2
    assert window.pair_analysis is cached_analysis
    assert observations[-1] == (
        True,
        True,
        "Suggesting preservation balance…",
    )
    assert (window.preservation_a_slider.value(), window.preservation_b_slider.value()) == (
        40,
        60,
    )

    assert window.apply_balance_suggestion() == (95, 65)
    assert (window.preservation_a_slider.value(), window.preservation_b_slider.value()) == (
        95,
        65,
    )
    assert window.pending_balance_suggestion is None
    assert not window.apply_suggestion_button.isEnabled()
    window.preservation_b_slider.setValue(64)
    assert window.preservation_b_slider.value() == 64
    window.close()


def test_low_confidence_suggestion_honestly_previews_neutral_balance(
    tmp_path: Path,
) -> None:
    generated = generate_fixtures(tmp_path / "fixtures")
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.load_clip("A", generated["identical_a"])
    window.load_clip("B", generated["identical_b"])
    window.set_preservation_values(30, 45)

    suggestion = window.suggest_balance()
    application.processEvents()

    assert (suggestion.preservation_a, suggestion.preservation_b) == (50, 50)
    assert not suggestion.is_confident
    assert (window.preservation_a_slider.value(), window.preservation_b_slider.value()) == (
        30,
        45,
    )
    summary = window.balance_suggestion_label.text()
    assert "Low-confidence balanced fallback: A 50% · B 50%" in summary
    assert "No strong recommendation:" in summary
    assert "Preview only" in summary

    window.apply_suggestion_button.click()
    application.processEvents()
    assert (window.preservation_a_slider.value(), window.preservation_b_slider.value()) == (
        50,
        50,
    )
    window.close()
