"""Check frozen-engine replay and clean-control consistency without tuning."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from glue.benchmark.manifest import read_manifest
from glue.benchmark.runner import Experiment, algorithm_fingerprint, run_benchmark


def normalized(row: dict) -> dict:
    return json.loads(json.dumps({k: v for k, v in row.items()
                                 if k not in {"runtime_seconds", "diagnostic_seconds"}}))


def identity(row: dict) -> tuple:
    return row["entry"], row["kind"], row["preset"], tuple(row["preservation"]), row["seed"]


def verify(root: Path) -> dict:
    frozen = algorithm_fingerprint()
    results = {}
    for dataset in ("pop909", "maestro"):
        base = root / dataset
        manifest = read_manifest(base / "benchmark-manifest.json")
        entry = next(e for e in manifest["entries"]
                     if e["split"] == "calibration" and e["density_stratum"] == 3)
        subset = {**manifest, "entries": [entry]}
        original = json.loads((base / "calibration/results.json").read_text(encoding="utf-8"))
        if original["algorithm_sha256"] != frozen:
            raise ValueError("Current engine differs from recorded baseline")
        expected = {identity(r): normalized(r) for r in original["results"]}
        repeated = run_benchmark(subset, Experiment(
            kinds=("accidental", "coordinated"), seeds=(52,),
            preservations=(0, 25, 50, 75, 100), max_notes=64, trace=True))
        for row in repeated["results"]:
            if normalized(row) != expected[identity(row)]:
                raise AssertionError(f"Replay mismatch: {dataset} {identity(row)}")
        clean_count = 0
        truncated = 0
        for split in ("calibration", "evaluation"):
            matrix = json.loads((base / split / "results.json").read_text(encoding="utf-8"))
            controls = json.loads((base / f"clean-{split}" / "results.json").read_text(
                encoding="utf-8"))
            expected_clean = {identity(r): normalized(r) for r in matrix["results"]
                              if r["kind"] == "clean"}
            for row in controls["results"]:
                if normalized(row) != expected_clean[identity(row)]:
                    raise AssertionError(f"Clean-control mismatch: {dataset} {identity(row)}")
                clean_count += 1
            truncated += sum(r["search_trace"]["truncated"] for r in matrix["results"])
        results[dataset] = {"replayed_cases": len(repeated["results"]),
                            "clean_controls_matched": clean_count,
                            "matrix_truncated_traces": truncated, "entry": entry["id"]}
        print(dataset, results[dataset], flush=True)
    if algorithm_fingerprint() != frozen:
        raise ValueError("Engine changed during replay")
    return {"algorithm_sha256": frozen, "corpora": results,
            "excluded_comparison_fields": ["runtime_seconds", "diagnostic_seconds"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("benchmarks/baselines/v052-real"))
    args = parser.parse_args()
    result = verify(args.root)
    with (args.root / "replay-verification.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
