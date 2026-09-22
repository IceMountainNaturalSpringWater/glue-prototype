from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

import glue.ui.main_window as main_module
from glue.fixes.musical_config import EditPermissions
from glue.io import load_midi
from glue.io.edited import note_semantics
from glue.ui import MainWindow
from scripts.generate_v05_fixtures import generate


@pytest.fixture
def window(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: pytest.fail(str(args[2])))
    widget = MainWindow()
    widget.show()
    app.processEvents()
    yield widget
    widget.close()


def test_pair_button_permissions_alternatives_export_and_invalidation(
    window, tmp_path, monkeypatch
):
    paths = generate(tmp_path / "fixtures")
    assert window.current_workflow == "combine"
    assert window.musical_controls.permissions == (EditPermissions(), EditPermissions())
    assert not window.repair_button.isEnabled()
    window.load_clip("A", paths["rhythmic_collision_a"])
    window.load_clip("B", paths["rhythmic_collision_b"])
    window.set_preservation_values(100, 0)
    window.preset_combo.setCurrentIndex(2)
    panel = window.musical_controls
    panel.checks[1][0].setChecked(False)
    panel.checks[1][1].setChecked(True)
    observations = []
    original = main_module.generate_musical_repairs

    def observed(*args, **kwargs):
        observations.append((window.is_busy, window.repair_button.isEnabled(), kwargs))
        assert not window.busy_indicator.isHidden()
        window.repair_button.click()  # Disabled: no duplicate event/search.
        return original(*args, **kwargs)

    monkeypatch.setattr(main_module, "generate_musical_repairs", observed)
    window.repair_button.click()
    assert len(observations) == 1
    assert observations[0][:2] == (True, False)
    assert observations[0][2]["preservation"] == (100, 0)
    result = panel.result
    assert result and result.candidates
    assert panel.candidate.counts[1] > 0
    assert panel.candidate.counts[0] == panel.candidate.counts[2] == 0
    assert not window.legacy_results.isVisible()
    assert not panel.rationale_toggle.isChecked()
    assert not panel.debug_toggle.isChecked()
    assert panel.rationale.isHidden() and panel.debug_panel.isHidden()
    assert window.analysis_details_panel.isHidden()
    assert window.piano_roll.changed_note_ids_b
    assert not window.piano_roll.changed_note_ids_a
    panel.rationale_toggle.click()
    assert panel.rationale.isVisible()
    assert panel.rationale.topLevelItemCount() == len(panel.candidate.edits)
    if len(result.candidates) > 1:
        panel.alternatives.setCurrentIndex(1)
    selected = panel.candidate
    output = panel.export(tmp_path / "b.mid", slot=1)
    assert note_semantics(load_midi(output).clip) == note_semantics(selected.clips[1])
    assert panel.export(tmp_path / "changes.json", report=True).is_file()
    bundle = panel.export(tmp_path / "bundle", bundle=True)
    assert all(p.is_file() for p in bundle.all_paths)
    combined = load_midi(bundle.combined_preview).clip
    assert len(combined.notes) == sum(len(c.notes) for c in selected.clips)
    window.analyze()
    first = window.pair_analysis
    window.analyze()
    assert window.pair_analysis is first
    assert panel.candidate == selected  # Optional estimation doesn't discard a repair.
    window.resize(1024, 768)
    QApplication.processEvents()
    assert panel.alternatives.width() > 150
    panel.checks[1][2].setChecked(True)
    assert panel.result is None
    assert not window.piano_roll.is_comparing
    window.set_preservation_values(100, 100)
    assert not window.repair_button.isEnabled()
    assert "fully preserved" in panel.hint.text()


def test_single_button_pitch_only_rationale_and_export(window, tmp_path):
    paths = generate(tmp_path / "fixtures")
    window.load_single_clip(paths["pitch_only"])
    page = window.polish_page
    page.set_preservation(0)
    page.generate_button.click()
    panel = page.musical_controls
    assert panel.result and panel.candidate
    assert panel.candidate.counts == (1, 0, 0)
    assert panel.candidate.score.estimate > panel.result.before.estimate
    assert not page.legacy_results.isVisible()
    assert page.piano_roll_tabs.currentIndex() == 1
    output = panel.export(tmp_path / "single.mid")
    assert note_semantics(load_midi(output).clip) == note_semantics(panel.candidate.clips[0])
    page.set_preservation(100)
    assert panel.result is None
    assert not page.generate_button.isEnabled()
    page.set_preservation(0)
    page.clear_all_suggestions()
    assert not page.generate_button.isEnabled()
    assert not page.repair_musical().candidates


def test_clean_single_explains_no_improvement_and_blocks_export(window, tmp_path):
    paths = generate(tmp_path / "fixtures")
    window.load_single_clip(paths["intentional_syncopation"])
    page = window.polish_page
    page.set_preservation(0)
    page.preset_combo.setCurrentIndex(2)
    panel = page.musical_controls
    panel.checks[0][1].setChecked(True)
    panel.checks[0][2].setChecked(True)
    page.generate_button.click()
    assert panel.result and not panel.result.candidates
    assert "No improving candidate" in panel.summary.text()
    assert not any(b.isEnabled() for b in panel.export_buttons)
    with pytest.raises(RuntimeError, match="improving"):
        panel.export(tmp_path / "unchanged.mid")


def test_preset_never_silently_enables_timing_or_duration(window):
    for index in range(3):
        window.preset_combo.setCurrentIndex(index)
        window.polish_page.preset_combo.setCurrentIndex(index)
        assert window.musical_controls.permissions == (EditPermissions(), EditPermissions())
        assert window.polish_page.musical_controls.permissions == (EditPermissions(),)
