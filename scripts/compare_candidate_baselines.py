"""Compare frozen candidate baselines without pooling datasets or inspecting MIDI."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from scripts.summarize_real_baseline import group_metrics


def key(row: dict) -> tuple:
    return row["entry"], row["kind"], row["preset"], tuple(row["preservation"]), row["seed"]


def metrics(rows: list[dict]) -> dict:
    result = group_metrics(rows)
    unnecessary = Counter()
    coordinated = Counter()
    scoring_cases = []
    for row in rows:
        if "metrics" not in row:
            continue
        corrupted = {(c["slot"], c["note_id"], f)
                     for c in row["corruption_ledger"] for f in c["fields"]}
        for edit in row["edits"]:
            for field in ("pitch", "onset_ticks", "duration_ticks"):
                if (edit["before"][field] != edit["after"][field]
                        and (edit["slot"], edit["note_id"], field) not in corrupted):
                    unnecessary[field] += 1
        trace = row.get("search_trace", {})
        target = trace.get("coordinated", {})
        if target.get("target_fields", 0) > 1:
            coordinated["cases"] += 1
            for field in ("all_generated", "entered_search", "scored", "survived_beam"):
                coordinated[field] += bool(target[field])
        for t in trace.get("targets", []):
            if (t["generated"] and t["survived_beam"]
                    and t["failure_category"] == "scoring_preferred_another_result"
                    and len(scoring_cases) < 12):
                scoring_cases.append({"entry": row["entry"], "kind": row["kind"],
                                      "preset": row["preset"], "preservation": row["preservation"],
                                      "target": t})
    result["unnecessary_edits_by_field"] = dict(unnecessary)
    result["coordinated_state_availability"] = dict(coordinated)
    result["scoring_gate_examples"] = scoring_cases
    result["usable_reference_field_coverage"] = {}
    for field in ("pitch", "timing", "duration"):
        eligible = [t for row in rows for t in row.get("search_trace", {}).get("targets", [])
                    if t["edit_type"] == field and t["eligible"]]
        result["usable_reference_field_coverage"][field] = {
            "eligible": len(eligible),
            "scored": sum(t["scored"] for t in eligible),
            "survived_beam": sum(t["survived_beam"] for t in eligible),
            "note": "Generated values may still be rejected by movement/safety constraints or budgets."}
    return result


def compare(before: list[dict], after: list[dict]) -> dict:
    if {key(r) for r in before} != {key(r) for r in after}:
        raise ValueError("Before/after matrices differ")
    originals = {key(r): r for r in before}
    for row in after:
        prior = originals[key(row)]
        if any(row.get(field) != prior.get(field) for field in
               ("corruption_ledger", "corruption_seed", "permissions")):
            raise ValueError("Cannot compare changed corruptions or edit permissions")
    previous = {(key(r), t["slot"], t["note_id"], t["field"]): t["failure_category"]
                for r in before for t in r.get("search_trace", {}).get("targets", [])}
    migration = Counter((previous[key(r), t["slot"], t["note_id"], t["field"]], t["failure_category"])
                        for r in after for t in r.get("search_trace", {}).get("targets", []))
    groups = {"all": lambda r: True, "unlocked": lambda r: all(p < 100 for p in r["preservation"])}
    groups.update({f"preservation_{p}": lambda r, p=p: all(v == p for v in r["preservation"])
                   for p in (0, 25, 50, 75, 100)})
    groups.update({f"preset_{p}": lambda r, p=p: r["preset"] == p
                   for p in ("minimal", "balanced", "creative")})
    groups.update({f"kind_{k}": lambda r, k=k: r["kind"] == k for k in sorted({r["kind"] for r in before})})
    return {"groups": {name: {"before": metrics([r for r in before if select(r)]),
                              "after": metrics([r for r in after if select(r)])}
                       for name, select in groups.items()},
            "failure_migration": [{"before": a, "after": b, "fields": count}
                                  for (a, b), count in sorted(migration.items())]}


def markdown(comparisons: dict) -> str:
    def percent(value: float | None) -> str:
        return "n/a" if value is None else f"{value * 100:.2f}%"

    lines = ["# V0.5.2 -> V0.5.3 candidate comparison", "",
             "Separate datasets and splits. Arrows mean before -> after; no pooled corpus score.",
             "All counts repeat observations across settings. Unlocked excludes 100% preservation.",
             "Candidate recall uses all targets in each group; unlocked excludes locked targets.",
             "Recovery is exact unless marked partial. JSON also includes editable-field recall explicitly.", ""]
    for dataset, splits in comparisons.items():
        for split, data in splits.items():
            lines += [f"## {dataset} / {split}", "",
                      "| Settings | Pitch recall | Timing recall | Duration recall | Exact notes | Partial fields | Clean FP | Untouched preservation | Mean seconds |",
                      "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
            for name, group in data["groups"].items():
                if name.startswith("kind_"):
                    continue
                values = []
                for field in ("pitch", "timing", "duration"):
                    values.append(" -> ".join(percent(group[p]["edit_type_diagnostics"].get(
                        field, {}).get("candidate_recall")) for p in ("before", "after")))
                for metric in ("exact_recovery_rate", "partial_field_recovery", "clean_false_positive_rate",
                               "untouched_note_preservation"):
                    values.append(" -> ".join(percent(group[p][metric]) for p in ("before", "after")))
                values.append(" -> ".join("n/a" if group[p]["mean_runtime_seconds"] is None
                                          else f"{group[p]['mean_runtime_seconds']:.3f}"
                                          for p in ("before", "after")))
                lines.append(f"| {name} | " + " | ".join(values) + " |")
            group = data["groups"]["all"]
            lines += ["", "| Additional metric (all settings) | Before | After |", "|---|---:|---:|"]
            for name in ("clean_octave_displacements", "clean_octave_displacement_rate",
                         "clean_timing_edits", "clean_duration_edits", "unnecessary_edit_count",
                         "made_worse_runs", "total_runtime_seconds"):
                lines.append(f"| {name} | {group['before'][name]} | {group['after'][name]} |")
            for field in ("pitch", "onset_ticks", "duration_ticks"):
                values = [group[p]["unnecessary_edits_by_field"].get(field, 0) for p in ("before", "after")]
                lines.append(f"| Unnecessary {field} edits | {values[0]} | {values[1]} |")
            lines += ["", "Coordinated-state counts (including locked controls):", "", "```json",
                      json.dumps({p: group[p]["coordinated_state_availability"]
                                  for p in ("before", "after")}, indent=2), "```", "",
                      "Failure migration (corrupted fields):", "", "| Before | After | Count |",
                      "|---|---|---:|"]
            for row in data["failure_migration"]:
                lines.append(f"| {row['before']} | {row['after']} | {row['fields']} |")
            lines += ["", "Analysis attribution remains undetermined. Pruning is observed history, not proof of causation.",
                      "Ground-truth values and scoring-loss examples are diagnostic only, never repair inputs.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, default=Path("benchmarks/baselines/v052-real"))
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--split", choices=("calibration", "evaluation", "all"), default="calibration")
    args = parser.parse_args()
    comparisons = {}
    for dataset in ("pop909", "maestro"):
        comparisons[dataset] = {}
        for split in ("calibration", "evaluation"):
            if args.split not in (split, "all"):
                continue
            reports = [json.loads((root / dataset / split / "results.json").read_text(encoding="utf-8"))
                       for root in (args.before, args.after)]
            data = compare(*(r["results"] for r in reports))
            data["engine_fingerprints"] = [r["algorithm_sha256"] for r in reports]
            comparisons[dataset][split] = data
            group = data["groups"]["all"]
            for phase in ("before", "after"):
                m = group[phase]
                print(dataset, split, phase, {k: m[k] for k in (
                    "exact_recovery_rate", "partial_field_recovery", "clean_false_positive_rate",
                    "clean_octave_displacements", "unnecessary_edits_by_field", "mean_runtime_seconds")},
                    {k: v["eligible_candidate_recall"] for k, v in m["edit_type_diagnostics"].items()}, flush=True)
    path = args.after / f"comparison-{args.split}.json"
    with path.open("x", encoding="utf-8") as stream:
        json.dump(comparisons, stream, indent=2, sort_keys=True)
    with path.with_suffix(".md").open("x", encoding="utf-8") as stream:
        stream.write(markdown(comparisons))


if __name__ == "__main__":
    main()
