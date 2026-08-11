from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_OPENGL", "software")
os.environ.setdefault("QT_API", "pyside6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

import glue.ui.single_workflow as single_workflow_module
from glue.fixes import RepairPreset
from glue.io import load_midi
from glue.single_exporting import SingleRepairExportError
from glue.ui import MainWindow, PianoRollWidget
from scripts.generate_fixtures import generate_fixtures

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SMOKE_SENTINEL = "GLUE_GUI_SMOKE_OK"


def _application() -> QApplication:
    return QApplication.instance() or QApplication([])


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


def test_top_workflow_buttons_default_to_combine_and_preserve_state() -> None:
    application = _application()
    window = MainWindow()
    window.show()
    application.processEvents()

    assert window.current_workflow == "combine"
    assert window.combine_page.isVisible()
    assert window.combine_workflow_button.isChecked()
    assert not window.polish_workflow_button.isChecked()
    assert window.polish_workflow_button.text() == "Polish One Clip"
    assert window.combine_workflow_button.text() == "Combine Two Clips"
    assert window.workflow_stack.count() == 2
    assert not hasattr(window, "workflow_chooser_page")

    window.polish_workflow_button.click()
    window.polish_page.set_preservation(37)
    application.processEvents()
    assert window.current_workflow == "polish"
    assert window.polish_page.isVisible()
    assert window.polish_workflow_button.isChecked()

    window.combine_workflow_button.click()
    window.set_preservation_values(100, 42)
    application.processEvents()
    assert window.current_workflow == "combine"
    assert window.combine_page.isVisible()
    assert window.preservation_b_slider.value() == 42
    assert window.combine_workflow_button.isChecked()

    window.polish_workflow_button.click()
    application.processEvents()
    assert window.current_workflow == "polish"
    assert window.polish_page.preservation == 37

    window.combine_workflow_button.click()
    assert window.preservation_b_slider.value() == 42
    window.close()


def test_single_analysis_is_cached_and_suggestions_are_reviewable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generated = generate_fixtures(tmp_path / "fixtures")
    application = _application()
    window = MainWindow()
    window.show()
    window.select_polish_workflow()
    page = window.polish_page

    calls = 0
    observations: list[tuple[bool, bool, str]] = []
    original_analyze = single_workflow_module.analyze_single_clip

    def observed_analyze(*args, **kwargs):
        nonlocal calls
        calls += 1
        observations.append(
            (
                page.is_busy,
                not page.busy_indicator.isHidden(),
                page.busy_status_label.text(),
            )
        )
        return original_analyze(*args, **kwargs)

    monkeypatch.setattr(
        single_workflow_module,
        "analyze_single_clip",
        observed_analyze,
    )

    window.load_single_clip(generated["single_awkward_leap"])
    application.processEvents()
    analysis = page.analysis
    assert analysis is not None
    assert calls == 1
    assert observations == [(True, True, "Analyzing suggestions...")]
    assert page.primary_suggestion_list.count() == 1
    assert page.secondary_suggestion_list.count() == 1
    assert page.secondary_suggestion_panel.isHidden()
    assert page.secondary_toggle_button.text() == (
        "Show low-confidence suggestions (1)"
    )
    assert page.enabled_suggestion_ids == analysis.default_enabled_suggestion_ids
    primary = page.primary_suggestion_list.item(0)
    secondary = page.secondary_suggestion_list.item(0)
    assert primary.checkState() == Qt.CheckState.Checked
    assert secondary.checkState() == Qt.CheckState.Unchecked
    assert "Possible melodic discontinuity" in primary.text()
    assert "Alternatives:" in primary.text()

    page.secondary_toggle_button.setChecked(True)
    page.primary_suggestion_list.setCurrentRow(0)
    application.processEvents()
    assert page.secondary_suggestion_panel.isVisible()
    assert "Possible alternatives:" in page.suggestion_detail_label.text()

    page.preservation_slider.setValue(20)
    page.preset_combo.setCurrentIndex(2)
    page.select_all_suggestions()
    page.clear_all_suggestions()
    page.select_all_suggestions()
    window.select_combine_workflow()
    window.select_polish_workflow()
    assert calls == 1
    assert page.enabled_suggestion_ids == frozenset(
        suggestion.suggestion_id for suggestion in analysis.suggestions
    )

    first_analysis = page.analysis
    page.load_clip(generated["single_awkward_leap"])
    assert calls == 1
    assert page.analysis is first_analysis
    window.close()


def test_single_repair_busy_preview_and_exports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generated = generate_fixtures(tmp_path / "fixtures")
    source = generated["single_obvious_accidental"]
    application = _application()
    window = MainWindow()
    window.show()
    window.load_single_clip(source)
    page = window.polish_page
    page.set_preservation(0)

    observations: list[tuple[bool, bool, str, dict[str, object]]] = []
    original_repair = single_workflow_module.generate_single_repair

    def observed_repair(*args, **kwargs):
        observations.append(
            (
                page.is_busy,
                not page.busy_indicator.isHidden(),
                page.busy_status_label.text(),
                dict(kwargs),
            )
        )
        return original_repair(*args, **kwargs)

    monkeypatch.setattr(
        single_workflow_module,
        "generate_single_repair",
        observed_repair,
    )

    assert page.advanced_export_panel.isHidden()
    result = window.repair_single_clip()
    application.processEvents()

    assert result.has_improvement
    assert result.changed_note_count == 1
    assert observations[0][0:3] == (
        True,
        True,
        "Generating Minimal repair...",
    )
    assert observations[0][3]["analysis"] is page.analysis
    assert observations[0][3]["enabled_suggestion_ids"] == (
        page.enabled_suggestion_ids
    )
    assert observations[0][3]["preset"] is RepairPreset.MINIMAL
    assert observations[0][3]["preservation"] == 0
    assert page.repair_result is result
    assert page.after_piano_roll.is_comparing
    assert page.after_piano_roll.changed_note_ids_a == frozenset(
        edit.note_id for edit in result.edits
    )
    assert page.piano_roll_tabs.isTabEnabled(1)
    assert page.piano_roll_tabs.currentIndex() == 1
    assert page.edit_list.count() == result.changed_note_count
    assert "before:" in page.score_summary_label.text()
    assert "after:" in page.score_summary_label.text()
    assert result.stop_reason == page.stop_reason_label.text()
    assert page.export_midi_button.isEnabled()
    assert page.export_json_button.isEnabled()
    assert not page.advanced_export_panel.isAncestorOf(page.export_midi_button)
    assert page.advanced_export_panel.isAncestorOf(page.export_json_button)

    repaired_path = window.export_single_repaired(tmp_path / "polished.mid")
    report_path = window.export_single_report(tmp_path / "polished.json")
    assert load_midi(repaired_path).clip.notes == result.repaired_clip.notes
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["workflow"] == "polish-one-clip"
    assert report["changed_note_count"] == result.changed_note_count
    with pytest.raises(SingleRepairExportError, match="loaded source"):
        window.export_single_repaired(source)
    window.close()


def test_disabled_suggestions_hard_lock_and_no_improvement_are_not_successes(
    tmp_path: Path,
) -> None:
    generated = generate_fixtures(tmp_path / "fixtures")
    application = _application()
    window = MainWindow()
    window.load_single_clip(generated["single_obvious_accidental"])
    page = window.polish_page
    page.set_preservation(0)
    page.clear_all_suggestions()

    assert page.enabled_suggestion_ids == frozenset()
    assert not page.generate_button.isEnabled()
    disabled_result = page.generate_repair()
    assert not disabled_result.has_improvement
    assert disabled_result.changed_note_count == 0
    assert page.repair_result is None
    assert not page.export_midi_button.isEnabled()
    assert "suggestions are enabled" in page.stop_reason_label.text().lower()

    page.load_clip(generated["single_obvious_accidental"])
    page.set_preservation(100)
    assert not page.generate_button.isEnabled()
    assert not page.preservation_locked_indicator.isHidden()
    locked_result = page.generate_repair()
    assert not locked_result.has_improvement
    assert locked_result.changed_note_count == 0
    assert page.repair_result is None
    assert "Preservation is 100%" in page.stop_reason_label.text()

    page.load_clip(generated["single_no_improvement"])
    page.set_preservation(0)
    no_improvement = page.generate_repair()
    application.processEvents()
    assert no_improvement.changed_note_count == 0
    assert not no_improvement.has_improvement
    assert page.repair_result is None
    assert "No suggestions are enabled" in no_improvement.stop_reason
    assert not page.piano_roll_tabs.isTabEnabled(1)
    assert not page.export_json_button.isEnabled()
    window.close()


def test_single_piano_roll_modes_preserve_pitch_label_alignment(
    tmp_path: Path,
) -> None:
    application = _application()
    generated = generate_fixtures(tmp_path / "fixtures")
    original = load_midi(generated["single_obvious_accidental"]).clip
    repaired_notes = tuple(
        note if note.id != 5 else replace(note, pitch=65)
        for note in original.notes
    )
    repaired = original.with_notes(repaired_notes)
    widget = PianoRollWidget()
    widget.resize(760, 320)
    widget.set_single_comparison(original, repaired)
    widget.show()
    application.processEvents()

    assert widget.is_comparing
    assert widget.comparison_slot == "A"
    assert widget.changed_note_ids_a == frozenset({5})
    assert "one MIDI clip" in widget.accessibleDescription()
    for label in widget.pitch_labels:
        row = widget.pitch_row_rect(label.pitch)
        assert row is not None
        assert label.rect.center().y() == pytest.approx(row.center().y())
    assert not widget.grab().toImage().isNull()
    widget.close()


def test_offscreen_single_file_smoke_repairs_exports_and_reopens(
    tmp_path: Path,
) -> None:
    generated = generate_fixtures(tmp_path / "fixtures")
    repaired = tmp_path / "single-polished.mid"
    report = tmp_path / "single-polished.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "glue",
            "--smoke-test",
            "--single-file",
            str(generated["single_obvious_accidental"]),
            "--single-preservation",
            "0",
            "--single-preset",
            "minimal",
            "--single-export",
            str(repaired),
            "--single-export-report",
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
    assert SMOKE_SENTINEL in completed.stdout, diagnostic
    assert "workflow=polish" in completed.stdout, diagnostic
    assert "changes=1" in completed.stdout, diagnostic
    assert load_midi(repaired).clip.notes
    assert json.loads(report.read_text(encoding="utf-8"))["workflow"] == (
        "polish-one-clip"
    )
