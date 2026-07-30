"""QApplication construction and deterministic GUI smoke workflow."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from glue import __version__

from .main_window import MainWindow

SMOKE_SUCCESS_SENTINEL = "GLUE_GUI_SMOKE_OK"

_LEGACY_STRATEGY_VALUES = {
    "preserve-a": (100, 70),
    "preserve-b": (70, 100),
    "shared": (85, 85),
    "custom": (85, 85),
}


def run(
    *,
    smoke_test: bool = False,
    file_a: Path | None = None,
    file_b: Path | None = None,
    export_path: Path | None = None,
    strategy: str | None = None,
    preservation_a: int | None = None,
    preservation_b: int | None = None,
    export_a: Path | None = None,
    export_b: Path | None = None,
    export_combined: Path | None = None,
    export_report: Path | None = None,
    export_base: Path | None = None,
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
    application.setApplicationVersion(__version__)

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
                strategy=strategy,
                preservation_a=preservation_a,
                preservation_b=preservation_b,
                export_a=export_a,
                export_b=export_b,
                export_combined=export_combined,
                export_report=export_report,
                export_base=export_base,
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
    strategy: str | None,
    preservation_a: int | None,
    preservation_b: int | None,
    export_a: Path | None,
    export_b: Path | None,
    export_combined: Path | None,
    export_report: Path | None,
    export_base: Path | None,
) -> None:
    try:
        if (file_a is None) != (file_b is None):
            raise ValueError("smoke workflow requires both --file-a and --file-b")
        outputs = (
            export_path,
            export_a,
            export_b,
            export_combined,
            export_report,
            export_base,
        )
        if any(value is not None for value in outputs) and file_a is None:
            raise ValueError("export options require --file-a and --file-b")

        selected_a, selected_b = (
            _LEGACY_STRATEGY_VALUES[strategy]
            if strategy is not None
            else (
                window.preservation_a_slider.value(),
                window.preservation_b_slider.value(),
            )
        )
        if preservation_a is not None:
            selected_a = preservation_a
        if preservation_b is not None:
            selected_b = preservation_b
        window.set_preservation_values(selected_a, selected_b)

        detail = f" preservation_a={selected_a} preservation_b={selected_b}"
        if file_a is not None and file_b is not None:
            window.load_clip("A", file_a)
            window.load_clip("B", file_b)
            before = window.analyze()
            candidate = window.repair_selected()
            if export_path is not None:
                window.export_candidate(export_path)
            if export_a is not None:
                window.export_revised_clip("A", export_a)
            if export_b is not None:
                window.export_revised_clip("B", export_b)
            if export_combined is not None:
                window.export_combined_preview(export_combined)
            if export_report is not None:
                window.export_change_report(export_report)
            if export_base is not None:
                window.export_repair_bundle(export_base)
            detail = (
                f" preservation_a={candidate.preservation_a * 100:.0f}"
                f" preservation_b={candidate.preservation_b * 100:.0f}"
                f" before={before.overall_score:.3f}"
                f" after={candidate.repaired_score:.3f}"
                f" changes={candidate.changed_note_count}"
                f" changes_a={candidate.changed_note_count_a}"
                f" changes_b={candidate.changed_note_count_b}"
            )
        print(f"{SMOKE_SUCCESS_SENTINEL}{detail}", flush=True)
        QTimer.singleShot(150, lambda: application.exit(0))
    except (OSError, RuntimeError, ValueError):
        traceback.print_exc()
        QTimer.singleShot(0, lambda: application.exit(1))
