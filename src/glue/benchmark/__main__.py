"""Offline benchmarking CLI: python -m glue.benchmark --help."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from glue.fixes.musical_config import EditPermissions

from .corrupt import KINDS
from .manifest import build_manifest, read_manifest, window_manifest
from .report import compare_reports, write_report
from .runner import Experiment, run_benchmark
from .synthetic import generate_reference_manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inventory = commands.add_parser("manifest", help="Inventory a local dataset; no downloads")
    inventory.add_argument("root", type=Path)
    inventory.add_argument("--dataset", choices=("reference", "pop909", "maestro"), default="reference")
    inventory.add_argument("--metadata", type=Path)
    inventory.add_argument("--pop-pairs", action="store_true")
    inventory.add_argument("--quarantine-split-conflicts", action="store_true")
    inventory.add_argument("--seed", type=int, default=0)
    inventory.add_argument("--window-beats", type=int)
    inventory.add_argument("--windows-per-piece", type=int, default=4)
    inventory.add_argument("--output", type=Path, required=True)
    synthetic = commands.add_parser("synthetic", help="Generate self-authored framework references")
    synthetic.add_argument("--output-dir", type=Path, required=True)
    run = commands.add_parser("run")
    run.add_argument("manifest", type=Path)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--split", choices=("calibration", "evaluation"), default="calibration")
    run.add_argument("--presets", nargs="+", choices=("minimal", "balanced", "creative"),
                     default=["minimal", "balanced", "creative"])
    run.add_argument("--preservation", nargs="+", type=int, default=[0, 50, 90, 100])
    run.add_argument("--pair-preservation", nargs="*", default=[], help="Extra A:B settings, e.g. 100:0")
    run.add_argument("--kinds", nargs="*", choices=KINDS, default=list(KINDS),
                     help="Omit values for clean-only testing")
    run.add_argument("--seeds", nargs="+", type=int, default=[0])
    run.add_argument("--severity", type=float, default=1)
    run.add_argument("--count", type=int, default=1)
    run.add_argument("--permissions", nargs="*", choices=("pitch", "timing", "duration"),
                     default=["pitch", "timing", "duration"])
    run.add_argument("--max-notes", type=int, default=256)
    run.add_argument("--trace", action="store_true", help="Record ground-truth-blind search diagnostics")
    compare = commands.add_parser("compare")
    compare.add_argument("before", type=Path)
    compare.add_argument("after", type=Path)
    compare.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            experiment = Experiment(
                presets=tuple(args.presets), preservations=tuple(args.preservation),
                kinds=tuple(args.kinds), seeds=tuple(args.seeds), severity=args.severity,
                count=args.count, split=args.split, max_notes=args.max_notes,
                trace=args.trace,
                permissions=EditPermissions(*(k in args.permissions
                                              for k in ("pitch", "timing", "duration"))),
                pair_preservation=tuple(tuple(int(p) for p in pair.split(":"))
                                        for pair in args.pair_preservation),
            )
            report = run_benchmark(read_manifest(args.manifest), experiment, progress=print)
            write_report(report, args.output_dir)
            print(f"Recorded {len(report['results'])} runs; {len(report['skipped'])} skipped cases.")
            if not report["results"] or any("error" in r for r in report["results"]):
                parser.exit(1, "No runs or engine errors; inspect the report.\n")
            return
        if args.command == "synthetic":
            data = generate_reference_manifest(args.output_dir / "references")
            output = args.output_dir / "manifest.json"
            data["root"] = "references"
        elif args.command == "manifest":
            data = build_manifest(args.root, dataset=args.dataset, seed=args.seed,
                                  metadata=args.metadata, pop_pairs=args.pop_pairs,
                                  quarantine_conflicts=args.quarantine_split_conflicts)
            if args.window_beats:
                data = window_manifest(data, args.window_beats, args.windows_per_piece)
            output = args.output
        else:
            data = compare_reports(json.loads(args.before.read_text(encoding="utf-8")),
                                   json.loads(args.after.read_text(encoding="utf-8")))
            output = args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
        print(output)
    except (ValueError, OSError, KeyError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
