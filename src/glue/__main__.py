"""Command-line entry point for the GLUE desktop application."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path


def _percentage(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("preservation must be an integer") from exc
    if not 0 <= parsed <= 100:
        raise argparse.ArgumentTypeError("preservation must be between 0 and 100")
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GLUE MIDI compatibility prototype")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="construct the GUI, optionally exercise a workflow, then exit",
    )
    parser.add_argument("--file-a", type=Path, help="MIDI A for --smoke-test")
    parser.add_argument("--file-b", type=Path, help="MIDI B for --smoke-test")
    parser.add_argument(
        "--single-file",
        type=Path,
        help="one MIDI file for the Polish One Clip smoke workflow",
    )
    parser.add_argument(
        "--single-preservation",
        type=_percentage,
        help="preservation percentage for the single-file smoke workflow",
    )
    parser.add_argument(
        "--single-preset",
        choices=("minimal", "balanced", "creative"),
        help="repair preset for the single-file smoke workflow",
    )
    parser.add_argument(
        "--single-export",
        type=Path,
        help="repaired MIDI output for the single-file smoke workflow",
    )
    parser.add_argument(
        "--single-export-report",
        type=Path,
        help="JSON output for the single-file smoke workflow",
    )
    parser.add_argument("--export", type=Path, help="export path for --smoke-test")
    parser.add_argument(
        "--strategy",
        choices=("preserve-a", "preserve-b", "shared", "custom"),
        help=(
            "legacy smoke-test shortcut that only selects preservation values; "
            "use --preserve-a/--preserve-b for explicit control"
        ),
    )
    parser.add_argument(
        "--preserve-a",
        type=_percentage,
        help="Clip A preservation percentage for smoke workflows",
    )
    parser.add_argument(
        "--preserve-b",
        type=_percentage,
        help="Clip B preservation percentage for smoke workflows",
    )
    parser.add_argument("--export-a", type=Path, help="revised Clip A output")
    parser.add_argument("--export-b", type=Path, help="revised Clip B output")
    parser.add_argument(
        "--export-combined",
        type=Path,
        help="separate-track combined preview output",
    )
    parser.add_argument("--export-report", type=Path, help="JSON change report output")
    parser.add_argument(
        "--export-base",
        type=Path,
        help="base path for all four repair artifacts",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse application options and run the PySide6 event loop."""

    parser = _parser()
    args = parser.parse_args(argv)
    workflow_values = (
        args.file_a,
        args.file_b,
        args.single_file,
        args.single_preservation,
        args.single_preset,
        args.single_export,
        args.single_export_report,
        args.export,
        args.strategy,
        args.preserve_a,
        args.preserve_b,
        args.export_a,
        args.export_b,
        args.export_combined,
        args.export_report,
        args.export_base,
    )
    supplied_workflow_option = any(value is not None for value in workflow_values)
    if supplied_workflow_option and not args.smoke_test:
        parser.error("MIDI workflow and export options require --smoke-test")
    if args.smoke_test and ((args.file_a is None) != (args.file_b is None)):
        parser.error("--smoke-test requires --file-a and --file-b together")
    pair_specific_values = (
        args.file_a,
        args.file_b,
        args.export,
        args.strategy,
        args.preserve_a,
        args.preserve_b,
        args.export_a,
        args.export_b,
        args.export_combined,
        args.export_report,
        args.export_base,
    )
    if args.single_file is not None and any(
        value is not None for value in pair_specific_values
    ):
        parser.error("single-file and two-file smoke workflows cannot be combined")
    single_specific_values = (
        args.single_preservation,
        args.single_preset,
        args.single_export,
        args.single_export_report,
    )
    if any(value is not None for value in single_specific_values) and (
        args.single_file is None
    ):
        parser.error("single-file options require --single-file")
    output_values = (
        args.export,
        args.export_a,
        args.export_b,
        args.export_combined,
        args.export_report,
        args.export_base,
    )
    if any(value is not None for value in output_values) and args.file_a is None:
        parser.error("export options require --file-a and --file-b")

    from glue.ui import run

    return run(
        smoke_test=args.smoke_test,
        file_a=args.file_a,
        file_b=args.file_b,
        single_file=args.single_file,
        single_preservation=args.single_preservation,
        single_preset=args.single_preset,
        single_export=args.single_export,
        single_export_report=args.single_export_report,
        export_path=args.export,
        strategy=args.strategy,
        preservation_a=args.preserve_a,
        preservation_b=args.preserve_b,
        export_a=args.export_a,
        export_b=args.export_b,
        export_combined=args.export_combined,
        export_report=args.export_report,
        export_base=args.export_base,
    )


if __name__ == "__main__":
    raise SystemExit(main())
