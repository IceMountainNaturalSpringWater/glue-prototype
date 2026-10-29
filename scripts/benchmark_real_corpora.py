"""Inventory actual local corpora and select outcome-independent bounded subsets.

No repair calls occur during selection. No corpus MIDI is copied or rewritten.
The audit parses every canonical/reference file; runs use short windows only.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from time import perf_counter

from glue.benchmark.manifest import (
    build_manifest,
    load_entry,
    stable_seed,
    validate_manifest,
)
from glue.benchmark.runner import algorithm_fingerprint


def _audit(item: tuple[str, dict]) -> dict:
    root, entry = item
    try:
        clips, _ = load_entry(Path(root), entry)
        return {"id": entry["id"], "usable": True, "notes": sum(len(c.notes) for c in clips),
                "beats": max(float(c.duration_quarter_notes) for c in clips),
                "split": entry["split"], "group": entry["group"]}
    except (ValueError, OSError) as exc:
        return {"id": entry["id"], "usable": False, "reason": str(exc),
                "split": entry["split"], "group": entry["group"]}


def select_subset(manifest: dict, audit: list[dict], *, per_split: int, max_notes: int = 64,
                  seed: int = 52, window_beats: int = 8) -> dict:
    """One passage per composition, stratified by source note density quartile.

    Choose a piece by stable hash within each stratum. Select among up to eight
    interior windows by stable hash; only parser validity and 8..max_notes note
    count affect window eligibility, never musical scores or repair outcomes.
    Coverage exclusions are retained, and no evaluation piece informs tuning.
    """
    by_id = {r["id"]: r for r in audit if r["usable"]}
    entries, exclusions = [], []
    for split in ("calibration", "evaluation"):
        candidates = sorted((e for e in manifest["entries"] if e["id"] in by_id
                             and e["split"] == split),
                            key=lambda e: (by_id[e["id"]]["notes"] / max(1, by_id[e["id"]]["beats"]),
                                           e["id"]))
        buckets = [candidates[i * len(candidates) // 4:(i + 1) * len(candidates) // 4]
                   for i in range(4)]
        buckets = [sorted(bucket, key=lambda e: stable_seed(seed, e["group"], e["id"]))
                   for bucket in buckets]
        selected_groups = set()
        counts = [0] * 4
        quota = [(per_split + 3 - i) // 4 for i in range(4)]
        for stratum, bucket in enumerate(buckets):
            for entry in bucket:
                if counts[stratum] >= quota[stratum]:
                    break
                if entry["group"] in selected_groups:
                    continue
                total = by_id[entry["id"]]["beats"]
                starts = sorted({int(total * i / 9 / 4) * 4 for i in range(1, 9)
                                 if int(total * i / 9 / 4) * 4 + window_beats <= total},
                                key=lambda start: stable_seed(seed, entry["id"], start))
                accepted = False
                for start in starts:
                    proposal = {**entry, "id": f"{entry['id']}@{start}:{start + window_beats}",
                                "window_beats": [start, start + window_beats],
                                "density_stratum": stratum}
                    try:
                        clips, _ = load_entry(Path(manifest["root"]), proposal)
                        count = sum(len(c.notes) for c in clips)
                        if not 8 <= count <= max_notes or any(len(c.notes) < 2 for c in clips):
                            continue
                    except (ValueError, OSError):
                        continue
                    entries.append(proposal)
                    counts[stratum] += 1
                    selected_groups.add(entry["group"])
                    accepted = True
                    break
                if not accepted:
                    exclusions.append({"id": entry["id"], "split": split, "stratum": stratum,
                                       "reason": "No eligible bounded interior passage in eight probes"})
    result = {**manifest, "entries": entries, "selection_exclusions": exclusions,
              "subset_protocol": {"seed": seed, "per_split": per_split, "max_notes": max_notes,
                                  "window_beats": window_beats, "density_strata": 4,
                                  "selection": "stable hash, one window per composition, no repair scoring",
                                  "boundary": "only onsets inside window; complete tails, no carried notes"}}
    validate_manifest(result)
    return result


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--per-split", type=int, default=4)
    parser.add_argument("--max-notes", type=int, default=64)
    parser.add_argument("--window-beats", type=int, default=8)
    parser.add_argument("--dataset", choices=("pop909", "maestro", "all"), default="all")
    parser.add_argument("--pop-root", type=Path, default=Path("benchmarks/POP909/POP909"))
    parser.add_argument("--maestro-root", type=Path,
                        default=Path("benchmarks/maestro-v3.0.0-midi/maestro-v3.0.0"))
    parser.add_argument("--maestro-metadata", type=Path, default=Path("benchmarks/maestro-v3.0.0.csv"))
    args = parser.parse_args()
    frozen = algorithm_fingerprint()
    for dataset, root, metadata in (
        ("pop909", args.pop_root, None),
        ("maestro", args.maestro_root, args.maestro_metadata),
    ):
        if args.dataset != "all" and args.dataset != dataset:
            continue
        started = perf_counter()
        print(f"Inventory {dataset}: {root}", flush=True)
        manifest = build_manifest(root, dataset=dataset, metadata=metadata,
                                  pop_pairs=dataset == "pop909", seed=52, quarantine_conflicts=True)
        write_json(args.output / dataset / "inventory-manifest.json", manifest)
        audit = []
        inventory = manifest["entries"] + manifest.get("quarantined_entries", [])
        with ProcessPoolExecutor(max_workers=3) as pool:
            for result in pool.map(_audit, ((str(root), entry) for entry in inventory)):
                audit.append(result)
                if len(audit) % 100 == 0:
                    print(f"{dataset}: parsed {len(audit)}/{len(inventory)}", flush=True)
        counts = {"detected": manifest["discovered_files"],
                  "canonical_or_metadata_listed": len(inventory),
                  "excluded_variants": manifest["excluded_variant_files"],
                  "split_quarantined": len(manifest.get("quarantined_entries", [])),
                  "usable": sum(r["usable"] for r in audit),
                  "splits": dict(Counter(r["split"] for r in audit if r["usable"])),
                  "audit_seconds": perf_counter() - started, "algorithm_sha256": frozen,
                  "files": audit}
        write_json(args.output / dataset / "audit.json", counts)
        subset = select_subset(manifest, audit, per_split=args.per_split,
                               max_notes=args.max_notes, window_beats=args.window_beats)
        write_json(args.output / dataset / "subset-manifest.json", subset)
        write_json(args.output / dataset / "benchmark-manifest.json", subset)
        print(f"{dataset}: usable={counts['usable']}; selected={len(subset['entries'])}", flush=True)
    assert algorithm_fingerprint() == frozen, "Engine changed during inventory"


if __name__ == "__main__":
    main()
