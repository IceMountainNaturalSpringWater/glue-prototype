from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_OPENGL", "software")
os.environ.setdefault("QT_API", "pyside6")

from PySide6.QtWidgets import QApplication

from glue.exporting import RepairExportError, RepairExportPaths
from glue.fixes import EditingStrategy
from glue.io import load_midi
from glue.ui import MainWindow
from scripts.generate_fixtures import generate_fixtures

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _offscreen_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["QT_OPENGL"] = "software"
    environment["QT_API"] = "pyside6"
    source_path = str(REPOSITORY_ROOT / "src")
    current = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        source_path if not current else source_path + os.pathsep + current
    )
    return environment


def _window_with_pair(
    tmp_path: Path,
    fixture_a: str,
    fixture_b: str,
) -> tuple[QApplication, MainWindow, dict[str, Path]]:
    generated = generate_fixtures(tmp_path / "fixtures")
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.load_clip("A", generated[fixture_a])
    window.load_clip("B", generated[fixture_b])
    window.analyze()
    application.processEvents()
    return application, window, generated


def test_details_panel_scrolls_at_the_supported_minimum_window_size() -> None:
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.select_combine_workflow()
    # V0.5 collapses unused legacy results. Preserve the legacy export-panel
    # sizing contract when that panel is shown by the V0.4 public repair API.
    window.legacy_results.show()
    window.resize(900, 650)
    window.show()
    application.processEvents()

    scroll_area = window.details_scroll_area
    vertical_bar = scroll_area.verticalScrollBar()
    collapsed_workspace_height = scroll_area.height()
    assert scroll_area.objectName() == "detailsScrollArea"
    assert scroll_area.widgetResizable()
    assert window.compatibility_estimate_group.isVisible()
    assert window.overall_score_label.isVisible()
    assert window.analysis_details_panel.isHidden()
    root_layout = window.combine_page.layout()
    workspace = scroll_area.parentWidget()
    assert root_layout.indexOf(window.analysis_details_panel) < root_layout.indexOf(
        workspace
    )
    assert vertical_bar.maximum() > 0
    assert scroll_area.horizontalScrollBar().maximum() == 0
    assert window.edit_a_list.height() >= 60
    assert window.edit_b_list.height() >= 60

    window.analysis_toggle_button.setChecked(True)
    application.processEvents()
    assert window.analysis_details_panel.isVisible()
    window.analysis_toggle_button.setChecked(False)
    application.processEvents()
    assert window.analysis_details_panel.isHidden()
    assert scroll_area.height() >= collapsed_workspace_height - 1

    vertical_bar.setValue(vertical_bar.maximum())
    application.processEvents()
    bundle_bottom = window.export_bundle_button.mapTo(
        scroll_area.viewport(),
        window.export_bundle_button.rect().bottomLeft(),
    ).y()
    assert 0 <= bundle_bottom <= scroll_area.viewport().height()
    window.close()


def test_preservation_only_controls_expose_derived_hard_lock_semantics(
    tmp_path: Path,
) -> None:
    application, window, _ = _window_with_pair(
        tmp_path,
        "both_locked_a",
        "both_locked_b",
    )

    assert not hasattr(window, "strategy_combo")
    assert not hasattr(window, "selected_strategy")
    assert not hasattr(window, "lock_a_radio")
    assert not hasattr(window, "lock_b_radio")
    assert not hasattr(window, "compare_strategies_button")
    assert not hasattr(window, "generate_strategy_comparison")
    assert window.preservation_a_slider.value() == 100
    assert window.preservation_b_slider.value() == 100
    assert window.preservation_a_slider.isEnabled()
    assert window.preservation_b_slider.isEnabled()
    assert not window.preservation_a_locked_indicator.isHidden()
    assert not window.preservation_b_locked_indicator.isHidden()
    assert not window.repair_button.isEnabled()

    window.preservation_b_slider.setValue(70)
    application.processEvents()
    assert window.preservation_a_slider.value() == 100
    assert window.preservation_a_slider.isEnabled()
    assert not window.preservation_a_locked_indicator.isHidden()
    assert window.preservation_b_locked_indicator.isHidden()
    assert window.preservation_a_locked_indicator.text() == "Locked"
    assert window.repair_button.isEnabled()
    keep_a = window.repair_selected()
    assert keep_a.strategy is EditingStrategy.CUSTOM
    assert keep_a.preservation_a == pytest.approx(1.0)
    assert keep_a.changed_note_count_a == 0

    window.preservation_b_slider.setValue(100)
    application.processEvents()
    assert window.preservation_a_slider.isEnabled()
    assert window.preservation_b_slider.isEnabled()
    assert not window.preservation_b_locked_indicator.isHidden()
    assert not window.repair_button.isEnabled()
    assert "Both clips are fully preserved" in window.repair_button.toolTip()
    assert "Both clips are fully preserved" in window.candidate_label.text()
    with pytest.raises(RuntimeError, match="Both clips are fully preserved"):
        window.repair_selected()

    window.preservation_a_slider.setValue(72)
    application.processEvents()
    assert window.preservation_a_slider.value() == 72
    assert window.preservation_a_slider.isEnabled()
    assert window.preservation_b_slider.isEnabled()
    assert window.preservation_a_locked_indicator.isHidden()
    assert "Both clips are fully preserved" not in window.candidate_label.text()
    assert window.repair_button.isEnabled()
    keep_b = window.repair_selected()
    assert keep_b.strategy is EditingStrategy.CUSTOM
    assert keep_b.preservation_a == pytest.approx(0.72)
    assert keep_b.preservation_b == pytest.approx(1.0)
    assert keep_b.changed_note_count_b == 0
    window.close()


def test_quick_balance_buttons_only_set_exact_slider_values() -> None:
    application = QApplication.instance() or QApplication([])
    window = MainWindow()

    window.keep_a_button.click()
    application.processEvents()
    assert (window.preservation_a_slider.value(), window.preservation_b_slider.value()) == (
        100,
        0,
    )
    assert window.preservation_a_slider.isEnabled()

    window.balanced_button.click()
    application.processEvents()
    assert (window.preservation_a_slider.value(), window.preservation_b_slider.value()) == (
        50,
        50,
    )

    window.keep_b_button.click()
    application.processEvents()
    assert (window.preservation_a_slider.value(), window.preservation_b_slider.value()) == (
        0,
        100,
    )
    window.preservation_b_slider.setValue(63)
    assert window.preservation_b_slider.value() == 63

    with pytest.raises(ValueError, match="preservation_a"):
        window.set_preservation_values(-1, 85)
    with pytest.raises(TypeError, match="preservation_b"):
        window.set_preservation_values(85, True)
    window.close()


def test_custom_candidate_displays_both_edit_sets_and_retains_balance_history(
    tmp_path: Path,
) -> None:
    application, window, _ = _window_with_pair(
        tmp_path,
        "shared_better_a",
        "shared_better_b",
    )

    window.set_preservation_values(85, 85)
    shared = window.repair_selected()
    application.processEvents()

    assert (shared.changed_note_count_a, shared.changed_note_count_b) == (1, 1)
    assert shared.strategy is EditingStrategy.CUSTOM
    assert window.repaired_slot is None
    assert not window.export_button.isEnabled()
    assert window.export_a_button.isEnabled()
    assert window.export_b_button.isEnabled()
    assert window.export_combined_button.isEnabled()
    assert window.export_report_button.isEnabled()
    assert "Estimated compatibility" not in window.candidate_label.text()
    assert "Estimated compatibility before" in (
        window.repair_score_summary_label.text()
    )
    assert "Clip A: 1 changed" in window.candidate_label.text()
    assert "Clip B: 1 changed" in window.candidate_label.text()
    assert window.edit_a_list.count() == 1
    assert window.edit_b_list.count() == 1
    assert window.piano_roll.changed_note_ids_a == frozenset({3})
    assert window.piano_roll.changed_note_ids_b == frozenset({0})
    assert window.timeline.after_analysis == shared.after_analysis

    window.set_preservation_values(100, 70)
    preserve_a = window.repair_selected()
    window.set_preservation_values(70, 100)
    preserve_b = window.repair_selected()
    application.processEvents()

    assert window.repair_candidate_count == 3
    assert window.candidate_list.count() == 3
    assert preserve_a.changed_note_count_a == 0
    assert preserve_b.changed_note_count_b == 0
    window.candidate_list.setCurrentRow(0)
    application.processEvents()
    assert window.repair_result is shared
    assert "Minimal repair" in window.candidate_label.text()
    assert "preservation 85%" in window.candidate_label.text()
    window.close()


def test_custom_preservation_changes_allocation_and_invalidates_active_preview(
    tmp_path: Path,
) -> None:
    application, window, _ = _window_with_pair(
        tmp_path,
        "preservation_bias_a",
        "preservation_bias_b",
    )
    window.set_preservation_values(10, 90)
    favor_a = window.repair_selected()
    application.processEvents()

    assert (favor_a.changed_note_count_a, favor_a.changed_note_count_b) == (1, 0)
    assert window.repair_candidate_count == 1
    window.set_preservation_values(90, 90)
    application.processEvents()
    assert window.repair_result is None
    assert window.repair_candidate_count == 1
    assert not window.export_a_button.isEnabled()

    window.set_preservation_values(90, 10)
    favor_b = window.repair_selected()
    application.processEvents()
    assert (favor_b.changed_note_count_a, favor_b.changed_note_count_b) == (0, 1)
    assert window.repair_candidate_count == 2
    window.close()


def test_gui_exports_each_artifact_and_the_complete_bundle(
    tmp_path: Path,
) -> None:
    application, window, generated = _window_with_pair(
        tmp_path,
        "dual_export_a",
        "dual_export_b",
    )
    window.set_preservation_values(85, 85)
    result = window.repair_selected()
    application.processEvents()

    revised_a = window.export_revised_clip("A", tmp_path / "revised-a.mid")
    revised_b = window.export_revised_clip("B", tmp_path / "revised-b.mid")
    combined = window.export_combined_preview(tmp_path / "combined.mid")
    report = window.export_change_report(tmp_path / "changes.json")
    bundle = window.export_repair_bundle(tmp_path / "bundle.mid")

    assert load_midi(revised_a).clip.notes == result.repaired_clip_a.notes
    assert load_midi(revised_b).clip.notes == result.repaired_clip_b.notes
    preview = load_midi(combined).clip
    assert len(preview.tracks) == 2
    assert [track.name for track in preview.tracks] == [
        "GLUE Revised A",
        "GLUE Revised B",
    ]
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["strategy"] == "custom"
    assert payload["clip_a"]["changed_note_count"] == 1
    assert payload["clip_b"]["changed_note_count"] == 1
    assert all(path.is_file() for path in bundle.paths.all_paths)
    assert bundle.paths == RepairExportPaths.from_base(tmp_path / "bundle.mid")

    with pytest.raises(RepairExportError, match="Refusing to overwrite loaded"):
        window.export_revised_clip("A", generated["dual_export_b"])
    window.close()


def test_v03_offscreen_smoke_runs_shared_analysis_repair_and_four_exports(
    tmp_path: Path,
) -> None:
    generated = generate_fixtures(tmp_path / "fixtures")
    revised_a = tmp_path / "shared-a.mid"
    revised_b = tmp_path / "shared-b.mid"
    combined = tmp_path / "shared-combined.mid"
    report = tmp_path / "shared-changes.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "glue",
            "--smoke-test",
            "--file-a",
            str(generated["dual_export_a"]),
            "--file-b",
            str(generated["dual_export_b"]),
            "--strategy",
            "shared",
            "--preserve-a",
            "85",
            "--preserve-b",
            "85",
            "--export-a",
            str(revised_a),
            "--export-b",
            str(revised_b),
            "--export-combined",
            str(combined),
            "--export-report",
            str(report),
        ],
        cwd=REPOSITORY_ROOT,
        env=_offscreen_environment(),
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )

    diagnostic = f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    assert completed.returncode == 0, diagnostic
    assert "GLUE_GUI_SMOKE_OK" in completed.stdout, diagnostic
    assert "preservation_a=85" in completed.stdout, diagnostic
    assert "preservation_b=85" in completed.stdout, diagnostic
    assert "changes_a=1" in completed.stdout, diagnostic
    assert "changes_b=1" in completed.stdout, diagnostic
    assert all(path.is_file() for path in (revised_a, revised_b, combined, report))
    assert len(load_midi(combined).clip.tracks) == 2
    assert json.loads(report.read_text(encoding="utf-8"))["version"] == "0.5.4"
