"""Command-line entry point for the GLUE desktop application."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GLUE MIDI compatibility prototype")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="construct the GUI, optionally exercise a workflow, then exit",
    )
    parser.add_argument("--file-a", type=Path, help="MIDI A for --smoke-test")
    parser.add_argument("--file-b", type=Path, help="MIDI B for --smoke-test")
    parser.add_argument("--export", type=Path, help="export path for --smoke-test")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse application options and run the PySide6 event loop."""

    parser = _parser()
    args = parser.parse_args(argv)
    supplied_workflow_option = any(
        value is not None for value in (args.file_a, args.file_b, args.export)
    )
    if supplied_workflow_option and not args.smoke_test:
        parser.error("--file-a, --file-b, and --export are smoke-test options")
    if args.smoke_test and ((args.file_a is None) != (args.file_b is None)):
        parser.error("--smoke-test requires --file-a and --file-b together")
    if args.export is not None and args.file_a is None:
        parser.error("--export requires --file-a and --file-b")

    from glue.ui import run

    return run(
        smoke_test=args.smoke_test,
        file_a=args.file_a,
        file_b=args.file_b,
        export_path=args.export,
    )


if __name__ == "__main__":
    raise SystemExit(main())
