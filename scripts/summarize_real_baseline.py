"""Summarize POP909 and MAESTRO independently; never pool corpus quality scores."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import median

from glue.benchmark.report import aggregate
from glue.benchmark.tracing import aggregate_traces


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rate(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def group_metrics(rows: list[dict]) -> dict:
    result = aggregate(rows)
    damaged = [r for r in rows if r["kind"] != "clean" and "metrics" in r]
    untouched = sum(r["metrics"]["untouched_notes"] for r in damaged)
    result["untouched_note_preservation"] = rate(
        untouched - sum(r["metrics"]["unnecessary_edit_count"] for r in damaged), untouched)
    for label in ("onset", "duration"):
        result[f"{label}_error_beats_before"] = sum(
            r["metrics"][f"{label}_error_beats_total_before"] for r in damaged)
        result[f"{label}_error_beats_after"] = sum(
            r["metrics"][f"{label}_error_beats_total_after"] for r in damaged)
    return result


def summarize(root: Path, dataset: str) -> dict:
    base = root / dataset
    audit = read(base / "audit.json")
    inventory = read(base / "inventory-manifest.json")
    manifest = read(base / "benchmark-manifest.json")
    reports = {s: read(base / s / "results.json") for s in ("calibration", "evaluation")}
    rows = [r for report in reports.values() for r in report["results"]]
    if len({r["algorithm_sha256"] for r in reports.values()}) != 1:
        raise ValueError("Cannot combine runs from different engine snapshots")
    usable = {r["id"] for r in audit["files"] if r["usable"]}
    eligible = [e for e in inventory["entries"] if e["id"] in usable]
    clean = [r for r in rows if r["kind"] == "clean" and "metrics" in r]
    damaged = [r for r in rows if r["kind"] != "clean" and "metrics" in r]
    seen = set()
    worst = []
    for row in sorted(damaged, key=lambda r: (
        -r["metrics"]["preservation_penalized_distance"], r["entry"], r["kind"], r["preset"]
    )):
        identity = (row["entry"], row["kind"])
        if identity in seen:
            continue
        seen.add(identity)
        worst.append({key: row[key] for key in ("entry", "kind", "preset", "preservation",
                                                "metrics", "edits", "search_trace")})
        if len(worst) == 8:
            break
    failures = {}
    for edit_type, data in aggregate_traces(rows).items():
        counts = data["failure_counts"]
        failures[edit_type] = {
            "analysis_failure": None,
            "analysis_note": "Not independently attributable from note recovery alone; unknown, not zero.",
            "correct_candidate_missing": counts.get("correct_candidate_never_generated", 0),
            "candidate_pruned": counts.get("correct_candidate_generated_but_pruned", 0),
            "scoring_rejected_correct_candidate": counts.get("scoring_preferred_another_result", 0),
            "coordinated_search_failure": counts.get("required_combination_not_discovered", 0),
            "other_outcomes": {k: v for k, v in counts.items() if k not in {
                "correct_candidate_never_generated", "correct_candidate_generated_but_pruned",
                "scoring_preferred_another_result", "required_combination_not_discovered"}},
            "percentages": data["category_percent_of_all_targets"],
        }
    timings = sorted(r["runtime_seconds"] for r in rows if "runtime_seconds" in r)
    return {
        "dataset": dataset, "algorithm_sha256": next(iter(reports.values()))["algorithm_sha256"],
        "counts": {"detected_midi": audit["detected"],
                   "canonical_or_metadata_listed": len(audit["files"]),
                   "parse_valid": audit["usable"], "excluded_variants": audit["excluded_variants"],
                   "split_quarantined": len(inventory.get("quarantined_entries", [])),
                   "benchmark_eligible": len(eligible),
                   "eligible_splits": dict(Counter(e["split"] for e in eligible)),
                   "sampled_pieces": len({e["group"] for e in manifest["entries"]}),
                   "sampled_windows": len(manifest["entries"]),
                   "unique_window_notes": sum({r["entry"]: r["metrics"]["note_count"]
                                               for r in clean}.values()),
                   "sample_splits": dict(Counter(e["split"] for e in manifest["entries"])),
                   "runs": len(rows), "corrupted_runs": len(damaged), "clean_runs": len(clean),
                   "skipped_cases": sum(len(r["skipped"]) for r in reports.values())},
        "overall": group_metrics(rows),
        "by_split": {s: group_metrics(r["results"]) for s, r in reports.items()},
        "by_kind": {kind: group_metrics([r for r in rows if r["kind"] == kind])
                    for kind in sorted({r["kind"] for r in rows})},
        "by_preset": {preset: group_metrics([r for r in rows if r["preset"] == preset])
                      for preset in ("minimal", "balanced", "creative")},
        "by_preservation": {str(p): group_metrics([r for r in rows
                                                  if all(value == p for value in r["preservation"])])
                            for p in (0, 25, 50, 75, 100)},
        "failure_categories": failures, "worst_examples": worst,
        "runtime": {"repair_seconds": sum(timings), "median_seconds": median(timings),
                    "p95_seconds": timings[int(0.95 * (len(timings) - 1))],
                    "max_seconds": max(timings),
                    "scope": "repair invocation including trace, excluding loading/corruption/metrics"},
        "limits": ["Eight short passages, not full-corpus musical validation.",
                   "Density-stratified, count-bounded windows omit preceding sustained notes.",
                   "Professional performance is a reference, not a proof every original note is correct.",
                   "Clean/corrupted observations repeat across settings; not independent compositions.",
                   "Analysis failure attribution remains unknown without independent context labels."],
    }


def percent(value: float | None) -> str:
    return "n/a" if value is None else f"{100 * value:.2f}%"


def markdown(report: dict) -> str:
    lines = [f"# {report['dataset']} frozen real-corpus baseline", "",
             f"Engine SHA-256: `{report['algorithm_sha256']}`", "",
             "## Counts", "", "```json", json.dumps(report["counts"], indent=2), "```", "",
             "No weights or repair behavior changed during this measurement phase.", ""]
    for title, key in (("Corruption type", "by_kind"), ("Preset", "by_preset"),
                       ("Preservation", "by_preservation"), ("Split", "by_split")):
        lines += [f"## {title}", "",
                  "| Setting | Runs | Exact recovery | Field recovery | Corrupted notes improved | Untouched preservation | Clean FP |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for setting, values in report[key].items():
            lines.append(f"| {setting} | {values['runs']} | {percent(values['exact_recovery_rate'])} | "
                         f"{percent(values['partial_field_recovery'])} | "
                         f"{percent(values['corrupted_note_improvement_rate'])} | "
                         f"{percent(values['untouched_note_preservation'])} | "
                         f"{percent(values['clean_false_positive_rate'])} |")
        lines.append("")
    lines += ["## Candidate recall", "",
              "All-target recall includes hard locks; editable recall excludes locked/disabled fields.", "",
              "| Edit type | Targets | Generated | Recall | Editable recall |",
              "|---|---:|---:|---:|---:|"]
    for edit_type, values in report["overall"]["edit_type_diagnostics"].items():
        lines.append(f"| {edit_type} | {values['corrupted_fields']} | "
                     f"{round(values['candidate_recall'] * values['corrupted_fields'])} | "
                     f"{percent(values['candidate_recall'])} | "
                     f"{percent(values['eligible_candidate_recall'])} |")
    lines += ["", "## Failure classification", "", "```json",
              json.dumps(report["failure_categories"], indent=2), "```", "",
              "Analysis attribution is unknown, not 0%. Missing candidates can have upstream analysis causes.",
              "Pruned states can still be retained by the engine; pruning alone is not proof of loss.", "",
              "## Clean edits and runtime", "", "```json", json.dumps({
                  k: v for k, v in report["overall"].items() if k.startswith("clean_")}, indent=2),
              "```", "", "```json", json.dumps(report["runtime"], indent=2), "```", "",
              "## Limitations", "", *[f"- {s}" for s in report["limits"]], "",
              "Full target ranks, scored components, rejection reasons and worst examples are in JSON.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("benchmarks/baselines/v052-real"))
    args = parser.parse_args()
    for name in ("pop909", "maestro"):
        result = summarize(args.root, name)
        for suffix, content in (("json", json.dumps(result, indent=2, sort_keys=True)),
                                ("md", markdown(result))):
            with (args.root / name / f"corpus-summary.{suffix}").open("x", encoding="utf-8") as stream:
                stream.write(content + "\n")
        print(name, result["counts"], flush=True)
