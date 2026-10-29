"""Replay a bounded calibration slice of a frozen real-corpus candidate baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from glue.benchmark.manifest import read_manifest
from glue.benchmark.runner import Experiment, algorithm_fingerprint, run_benchmark
from scripts.repeat_real_baseline import identity, normalized


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifests", type=Path, default=Path("benchmarks/baselines/v052-real"))
    args = parser.parse_args()
    frozen = algorithm_fingerprint()
    result = {"algorithm_sha256": frozen, "corpora": {}}
    for name in ("pop909", "maestro"):
        manifest = read_manifest(args.manifests / name / "benchmark-manifest.json")
        entry = next(e for e in manifest["entries"]
                     if e["split"] == "calibration" and e["density_stratum"] == 3)
        original = json.loads((args.root / name / "calibration/results.json").read_text(encoding="utf-8"))
        if original["algorithm_sha256"] != frozen:
            raise ValueError("Engine differs from frozen baseline")
        expected = {identity(r): normalized(r) for r in original["results"]}
        repeated = run_benchmark({**manifest, "entries": [entry]}, Experiment(
            kinds=("accidental", "coordinated"), seeds=(52,),
            preservations=(0, 25, 50, 75, 100), max_notes=64, trace=True))
        for row in repeated["results"]:
            if normalized(row) != expected[identity(row)]:
                raise AssertionError(f"Nondeterministic result: {name} {identity(row)}")
        result["corpora"][name] = {"entry": entry["id"], "matched": len(repeated["results"])}
        print(name, result["corpora"][name], flush=True)
    if algorithm_fingerprint() != frozen:
        raise ValueError("Engine changed during replay")
    with (args.root / "replay-verification.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)


if __name__ == "__main__":
    main()
