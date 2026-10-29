"""Run separate, bounded real-corpus measurements against one frozen engine."""

from __future__ import annotations

import argparse
from pathlib import Path
from time import perf_counter

from glue.benchmark.manifest import read_manifest
from glue.benchmark.report import write_report
from glue.benchmark.runner import Experiment, algorithm_fingerprint, run_benchmark

KINDS = {
    "pop909": ("accidental", "octave", "early", "attack_collision", "sustain", "short",
               "pitch_timing", "coordinated"),
    "maestro": ("accidental", "octave", "early", "late", "groove", "sustain", "short",
                "timing_duration", "coordinated"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifests", type=Path, default=Path("benchmarks/baselines/v052-real"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset", choices=("pop909", "maestro", "all"), default="all")
    parser.add_argument("--split", choices=("calibration", "evaluation", "all"), default="all")
    args = parser.parse_args()
    frozen = algorithm_fingerprint()
    for dataset, kinds in KINDS.items():
        if args.dataset not in ("all", dataset):
            continue
        manifest = read_manifest(args.manifests / dataset / "benchmark-manifest.json")
        for split in ("calibration", "evaluation"):
            if args.split not in ("all", split):
                continue
            started = perf_counter()
            count = 0

            def progress(message: str, label: str = f"{dataset}/{split}",
                         start_time: float = started) -> None:
                nonlocal count
                count += 1
                if count % 60 == 0:
                    print(f"{label}: {count} runs started, "
                          f"{perf_counter() - start_time:.1f}s elapsed", flush=True)

            print(f"START {dataset}/{split}; frozen engine {frozen}", flush=True)
            experiment = Experiment(kinds=kinds, seeds=(52,), preservations=(0, 25, 50, 75, 100),
                                    split=split, max_notes=64, trace=True)
            report = run_benchmark(manifest, experiment, progress=progress)
            if algorithm_fingerprint() != frozen or report["algorithm_sha256"] != frozen:
                raise RuntimeError("Engine changed during measurement")
            write_report(report, args.output / dataset / split)
            errors = sum("error" in row for row in report["results"])
            print(f"DONE {dataset}/{split}: {len(report['results'])} runs, "
                  f"{len(report['skipped'])} inapplicable, {errors} errors; "
                  f"{perf_counter() - started:.1f}s total", flush=True)
            if errors:
                raise RuntimeError("Benchmark contains engine errors; inspect recorded failures")


if __name__ == "__main__":
    main()
