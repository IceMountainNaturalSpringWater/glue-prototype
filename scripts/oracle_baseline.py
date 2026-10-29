"""Post-hoc oracle diagnostics; requires the exact engine used by the saved matrix."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from glue.benchmark.manifest import load_entry, read_manifest
from glue.benchmark.oracle import aggregate_oracles, analyze_oracle
from glue.benchmark.runner import algorithm_fingerprint
from glue.fixes.musical_config import musical_search_for


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifests", type=Path, default=Path("benchmarks/baselines/v052-real"))
    parser.add_argument("--split", choices=("calibration", "evaluation"), default="calibration")
    parser.add_argument("--quiet", action="store_true", help="Seal held-out diagnostics without inspecting metrics")
    args = parser.parse_args()
    frozen = algorithm_fingerprint()
    for dataset in ("pop909", "maestro"):
        report = json.loads((args.input / dataset / args.split / "results.json").read_text())
        if report["algorithm_sha256"] != frozen:
            raise ValueError("Counterfactual scoring requires the original frozen engine")
        manifest = read_manifest(args.manifests / dataset / "benchmark-manifest.json")
        clips = {e["id"]: load_entry(Path(manifest["root"]), e)[0]
                 for e in manifest["entries"] if e["split"] == args.split}
        rows = []
        for row in report["results"]:
            reference = clips[row["entry"]]
            changed = {(e["slot"], e["note_id"]): e["after"] for e in row["corruption_ledger"]}
            damaged = tuple(c.with_notes(replace(n, **{f: changed[slot, n.id][f]
                                                      for f in ("pitch", "onset_ticks", "duration_ticks")})
                                         if (slot, n.id) in changed else n for n in c.notes)
                            for slot, c in enumerate(reference))
            oracle = analyze_oracle(reference, damaged, row, musical_search_for(row["preset"]))
            rows.append({**{k: row[k] for k in ("entry", "kind", "preset", "preservation", "seed")},
                         "oracle": oracle})
        groups = {"all": rows, "unlocked": [r for r in rows if all(p < 100 for p in r["preservation"])]}
        groups.update({f"preservation_{p}": [r for r in rows if all(v == p for v in r["preservation"])]
                       for p in (0, 25, 50, 75, 100)})
        groups.update({f"preset_{p}": [r for r in rows if r["preset"] == p]
                       for p in ("minimal", "balanced", "creative")})
        groups.update({f"kind_{k}": [r for r in rows if r["kind"] == k] for k in sorted({r["kind"] for r in rows})})
        summaries = {name: aggregate_oracles(items) for name, items in groups.items()}
        output = args.output / dataset / args.split
        output.mkdir(parents=True, exist_ok=True)
        with (output / "oracle.json").open("x", encoding="utf-8") as stream:
            json.dump({"algorithm_sha256": frozen, "groups": summaries, "results": rows}, stream,
                      indent=2, sort_keys=True, allow_nan=False)
        if not args.quiet:
            print(dataset, args.split, summaries["all"], flush=True)
    if algorithm_fingerprint() != frozen:
        raise ValueError("Engine changed during diagnostics")


if __name__ == "__main__":
    main()
