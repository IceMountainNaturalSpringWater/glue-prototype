from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_OPENGL", "software")
os.environ.setdefault("QT_API", "pyside6")

from PySide6.QtWidgets import QApplication

from glue.analysis import analyze_pair
from glue.io import load_midi, write_midi
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
    window.close()
