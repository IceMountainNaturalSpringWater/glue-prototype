"""QApplication construction and deterministic GUI smoke workflow."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from glue import __version__
from glue.fixes import RepairPreset

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
    single_file: Path | None = None,
    single_preservation: int | None = None,
    single_preset: str | None = None,
    single_export: Path | None = None,
    single_export_report: Path | None = None,
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
                single_file=single_file,
                single_preservation=single_preservation,
                single_preset=single_preset,
                single_export=single_export,
                single_export_report=single_export_report,
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
    single_file: Path | None,
    single_preservation: int | None,
    single_preset: str | None,
    single_export: Path | None,
    single_export_report: Path | None,
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
        pair_outputs = (
            export_path,
            export_a,
            export_b,
            export_combined,
            export_report,
            export_base,
        )
        if any(value is not None for value in pair_outputs) and file_a is None:
            raise ValueError("export options require --file-a and --file-b")
        single_values = (
            single_preservation,
            single_preset,
            single_export,
            single_export_report,
        )
        if any(value is not None for value in single_values) and single_file is None:
            raise ValueError("single-file options require --single-file")
        if single_file is not None and file_a is not None:
            raise ValueError("single-file and two-file workflows cannot be combined")

        if single_file is not None:
            window.select_polish_workflow()
            selected_preservation = (
                window.polish_page.preservation
                if single_preservation is None
                else single_preservation
            )
            window.polish_page.set_preservation(selected_preservation)
            preset = RepairPreset(single_preset or RepairPreset.MINIMAL.value)
            preset_index = window.polish_page.preset_combo.findData(preset.value)
            if preset_index < 0:
                raise RuntimeError("The requested single-file preset is unavailable")
            window.polish_page.preset_combo.setCurrentIndex(preset_index)
            window.load_single_clip(single_file)
            analysis = window.polish_page.analysis
            if analysis is None:
                analysis = window.analyze_single_clip()
            result = window.repair_single_clip()
            if single_export is not None:
                window.export_single_repaired(single_export)
            if single_export_report is not None:
                window.export_single_report(single_export_report)
            print(
                f"{SMOKE_SUCCESS_SENTINEL} workflow=polish"
                f" preservation={selected_preservation}"
                f" preset={preset.value}"
                f" before={analysis.internal_consistency_score:.3f}"
                f" after={result.repaired_score:.3f}"
                f" changes={result.changed_note_count}",
                flush=True,
            )
            QTimer.singleShot(150, lambda: application.exit(0))
            return

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
            window.select_combine_workflow()
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
