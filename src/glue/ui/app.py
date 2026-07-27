"""QApplication construction and deterministic GUI smoke workflow."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from .main_window import MainWindow

SMOKE_SUCCESS_SENTINEL = "GLUE_GUI_SMOKE_OK"


def run(
    *,
    smoke_test: bool = False,
    file_a: Path | None = None,
    file_b: Path | None = None,
    export_path: Path | None = None,
) -> int:
    """Create and run the GLUE Qt application.

    Smoke mode performs an optional complete workflow after the event loop
    starts, then exits through a timer so layout and painting are exercised.
    """

    application = QApplication.instance()
    if application is None:
        application = QApplication([sys.argv[0]])
    application.setApplicationName("GLUE")
    application.setOrganizationName("GLUE")

    window = MainWindow()
    window.show()

    if smoke_test:
        QTimer.singleShot(
            0,
            lambda: _run_smoke_workflow(
                application,
                window,
                file_a=file_a,
                file_b=file_b,
                export_path=export_path,
            ),
        )
    return application.exec()


def _run_smoke_workflow(
    application: QApplication,
    window: MainWindow,
    *,
    file_a: Path | None,
    file_b: Path | None,
    export_path: Path | None,
) -> None:
    try:
        if (file_a is None) != (file_b is None):
            raise ValueError("smoke workflow requires both --file-a and --file-b")
        if export_path is not None and file_a is None:
            raise ValueError("--export requires --file-a and --file-b")

        detail = ""
        if file_a is not None and file_b is not None:
            window.load_clip("A", file_a)
            window.load_clip("B", file_b)
            before = window.analyze()
            candidate = window.repair_minimal()
            if export_path is not None:
                window.export_candidate(export_path)
            detail = (
                f" before={before.overall_score:.3f}"
                f" after={candidate.repaired_score:.3f}"
                f" changes={candidate.changed_note_count}"
            )
        print(f"{SMOKE_SUCCESS_SENTINEL}{detail}", flush=True)
        QTimer.singleShot(150, lambda: application.exit(0))
    except (OSError, RuntimeError, ValueError):
        traceback.print_exc()
        QTimer.singleShot(0, lambda: application.exit(1))
