from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import mido
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_OPENGL", "software")
os.environ.setdefault("QT_API", "pyside6")

from PySide6.QtWidgets import QApplication, QMessageBox

from glue.analysis import analyze_pair
from glue.fixes import RepairPreset
from glue.io import MidiContentError, MidiParseError, load_midi, write_midi
from glue.ui import MainWindow
from scripts.generate_fixtures import fixture_clips, generate_fixtures

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SMOKE_SENTINEL = "GLUE_GUI_SMOKE_OK"


def _offscreen_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["QT_OPENGL"] = "software"
    environment["QT_API"] = "pyside6"
    source_path = str(REPOSITORY_ROOT / "src")
    existing_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        source_path
        if not existing_pythonpath
        else source_path + os.pathsep + existing_pythonpath
    )
    return environment


def test_offscreen_module_smoke_runs_full_repair_and_export_workflow(
    tmp_path: Path,
) -> None:
    generated = generate_fixtures(tmp_path / "fixtures")
    source_a = generated["out_of_key_context"]
    source_b = generated["out_of_key_melody"]
    exported = tmp_path / "repaired.mid"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "glue",
            "--smoke-test",
            "--file-a",
            str(source_a),
            "--file-b",
            str(source_b),
            "--export",
            str(exported),
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
    assert "changes=1" in completed.stdout, diagnostic
    assert exported.is_file()

    original_a = load_midi(source_a).clip
    original_b = load_midi(source_b).clip
    repaired = load_midi(exported).clip
    assert analyze_pair(original_a, repaired).overall_score > analyze_pair(
        original_a,
        original_b,
    ).overall_score
    assert [
        (note.id, note.onset_ticks, note.duration_ticks)
        for note in repaired.notes
    ] == [
        (note.id, note.onset_ticks, note.duration_ticks)
        for note in original_b.notes
    ]


def test_offscreen_smoke_exits_nonzero_for_malformed_midi(
    tmp_path: Path,
) -> None:
    generated = generate_fixtures(tmp_path / "fixtures")
    malformed = tmp_path / "malformed.mid"
    malformed.write_bytes(b"not a MIDI file")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "glue",
            "--smoke-test",
            "--file-a",
            str(malformed),
            "--file-b",
            str(generated["identical_b"]),
        ],
        cwd=REPOSITORY_ROOT,
        env=_offscreen_environment(),
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )

    diagnostic = f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    assert completed.returncode != 0, diagnostic
    assert SMOKE_SENTINEL not in completed.stdout, diagnostic
    assert "malformed.mid" in completed.stderr, diagnostic
    assert "Could not read MIDI file" in completed.stderr, diagnostic


def test_no_comparable_overlap_is_not_presented_as_a_perfect_score(
    tmp_path: Path,
) -> None:
    clips = fixture_clips()
    clip_a = clips["identical_a"]
    shift = 8 * clip_a.ticks_per_beat
    clip_b = replace(
        clips["identical_b"],
        notes=tuple(
            replace(note, onset_ticks=note.onset_ticks + shift)
            for note in clips["identical_b"].notes
        ),
    )
    path_a = write_midi(clip_a, tmp_path / "a.mid")
    path_b = write_midi(clip_b, tmp_path / "b.mid")

    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.load_clip("A", path_a)
    window.load_clip("B", path_b)
    result = window.analyze()
    application.processEvents()

    assert result.overall_score == 100
    assert not any(item.activity_weight > 0 for item in result.windows)
    assert window.overall_score_label.text() == "No comparable overlap"
    assert {
        window.harmonic_score_label.text(),
        window.bass_score_label.text(),
        window.register_score_label.text(),
        window.rhythm_score_label.text(),
    } == {"N/A"}
    assert "Neutral internal scores do not establish compatibility" in (
        window.diagnosis_list.item(0).text()
    )
    assert not window.repair_button.isEnabled()
    window.close()


def test_repair_controls_retain_and_select_before_after_candidates(
    tmp_path: Path,
) -> None:
    generated = generate_fixtures(tmp_path / "fixtures")
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()

    assert window.preset_combo.count() == 3
    assert [
        window.preset_combo.itemData(index)
        for index in range(window.preset_combo.count())
    ] == [preset.value for preset in RepairPreset]
    assert window.selected_preset is RepairPreset.MINIMAL
    assert window.preservation_slider.minimum() == 0
    assert window.preservation_slider.maximum() == 100
    assert window.preservation_slider.value() == 50
    assert window.repair_button.objectName() == "minimalRepairButton"

    window.load_clip("A", generated["out_of_key_context"])
    window.load_clip("B", generated["out_of_key_melody"])
    before = window.analyze()
    first = window.repair_minimal()
    application.processEvents()

    assert window.repair_candidate_count == 1
    assert window.candidate_list.count() == 1
    assert window.repair_result is first
    assert window.repaired_slot == "B"
    assert window.timeline.is_comparing
    assert window.timeline.before_analysis == before
    assert window.timeline.after_analysis == first.after_analysis
    assert window.piano_roll.is_comparing
    assert window.piano_roll.comparison_slot == "B"
    assert window.piano_roll.comparison_clip == first.repaired_clip

    balanced_index = window.preset_combo.findData(RepairPreset.BALANCED.value)
    window.preset_combo.setCurrentIndex(balanced_index)
    window.preservation_slider.setValue(25)
    second = window.repair_selected()
    application.processEvents()

    assert second.preset is RepairPreset.BALANCED
    assert second.preservation == 25
    assert window.repair_candidate_count == 2
    assert window.candidate_list.currentRow() == 1
    assert window.repair_result is second
    assert "Balanced" in window.candidate_label.text()
    assert "preservation 25%" in window.candidate_label.text()

    window.candidate_list.setCurrentRow(0)
    application.processEvents()

    assert window.repair_result is first
    assert window.timeline.after_analysis == first.after_analysis
    assert window.piano_roll.comparison_clip == first.repaired_clip

    window.lock_b_radio.setChecked(True)
    application.processEvents()

    assert window.repair_candidate_count == 0
    assert window.candidate_list.count() == 0
    assert window.repair_result is None
    assert not window.timeline.is_comparing
    assert not window.piano_roll.is_comparing
    window.close()


def test_gui_rejects_empty_midi_before_replacing_a_loaded_slot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generated = generate_fixtures(tmp_path / "fixtures")
    empty_path = tmp_path / "empty.mid"
    empty_midi = mido.MidiFile(type=1, ticks_per_beat=480)
    empty_midi.tracks.append(
        mido.MidiTrack([mido.MetaMessage("end_of_track")])
    )
    empty_midi.save(filename=empty_path)
    malformed_path = tmp_path / "malformed.mid"
    malformed_path.write_bytes(b"not a MIDI file")

    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    original = window.load_clip("A", generated["identical_a"])
    original_label = window.path_a_label.text()

    with pytest.raises(MidiContentError, match="no complete positive-duration notes"):
        window.load_clip("A", empty_path)

    assert window.document_a is original
    assert window.path_a_label.text() == original_label
    with pytest.raises(MidiParseError, match="malformed.mid"):
        window.load_clip("A", malformed_path)
    assert window.document_a is original
    assert window.path_a_label.text() == original_label

    critical_messages: list[tuple[str, str]] = []

    def record_critical(
        _parent: object,
        title: str,
        message: str,
    ) -> QMessageBox.StandardButton:
        critical_messages.append((title, message))
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "critical", record_critical)
    result = window._run_interactive(
        "Could not load MIDI A",
        lambda: window.load_clip("A", empty_path),
    )
    application.processEvents()

    assert result is None
    assert critical_messages
    assert critical_messages[0][0] == "Could not load MIDI A"
    assert "empty.mid" in critical_messages[0][1]
    assert window.document_a is original
    window.close()


def test_gui_surfaces_nonfatal_parser_warning_details(tmp_path: Path) -> None:
    source = tmp_path / "warning.mid"
    midi = mido.MidiFile(type=0, ticks_per_beat=480)
    track = mido.MidiTrack()
    midi.tracks.append(track)
    track.extend(
        (
            mido.Message("note_off", note=61, velocity=0, time=0),
            mido.Message("note_on", note=60, velocity=90, time=0),
            mido.Message("note_off", note=60, velocity=0, time=480),
        )
    )
    midi.save(filename=source)

    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    document = window.load_clip("A", source)
    application.processEvents()

    assert len(document.warnings) == 1
    assert "Warnings: 1" in window.metadata_a_label.text()
    assert "unmatched note-off" in window.metadata_a_label.toolTip()
    assert "parser warning" in window.statusBar().currentMessage()
    window.close()


def test_gui_disables_repair_when_unlocked_clip_has_only_percussion(
    tmp_path: Path,
) -> None:
    clips = fixture_clips()
    percussion = replace(
        clips["identical_b"],
        notes=tuple(
            replace(note, channel=9)
            for note in clips["identical_b"].notes
        ),
    )
    path_a = write_midi(clips["identical_a"], tmp_path / "pitched.mid")
    path_b = write_midi(percussion, tmp_path / "percussion.mid")

    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.load_clip("A", path_a)
    window.load_clip("B", path_b)
    result = window.analyze()
    application.processEvents()

    assert any(item.activity_weight > 0 for item in result.windows)
    assert not window.repair_button.isEnabled()
    with pytest.raises(RuntimeError, match="no pitched notes"):
        window.repair_minimal()
    window.close()


def test_gui_export_never_overwrites_either_loaded_source(tmp_path: Path) -> None:
    generated = generate_fixtures(tmp_path / "fixtures")
    source_a = generated["out_of_key_context"]
    source_b = generated["out_of_key_melody"]
    before_a = source_a.read_bytes()
    before_b = source_b.read_bytes()

    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.load_clip("A", source_a)
    window.load_clip("B", source_b)
    window.analyze()
    window.repair_minimal()
    application.processEvents()

    for source in (source_a, source_b):
        with pytest.raises(RuntimeError, match="Refusing to overwrite"):
            window.export_candidate(source)

    assert source_a.read_bytes() == before_a
    assert source_b.read_bytes() == before_b
    window.close()
