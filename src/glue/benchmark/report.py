"""Transparent JSON/CSV/Markdown reports and matched-protocol comparisons."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from .tracing import aggregate_traces


def aggregate(rows: list[dict]) -> dict:
    successful = [r for r in rows if "metrics" in r]
    damaged = [r for r in successful if r["kind"] != "clean"]
    clean = [r for r in successful if r["kind"] == "clean"]
    denominator = sum(r["metrics"]["corrupted_notes"] for r in damaged)
    clean_notes = sum(r["metrics"]["note_count"] for r in clean)
    return {
        "edit_type_diagnostics": aggregate_traces(rows),
        "runs": len(rows), "errors": len(rows) - len(successful),
        "corrupted_notes": denominator,
        "partial_field_recovery": sum(r["metrics"].get("recovered_corrupted_fields", 0)
                                      for r in damaged) / max(1, sum(
                                          r["metrics"].get("corrupted_field_count", 0)
                                          for r in damaged)) if denominator else None,
        "corrupted_note_improvement_rate": sum(r["metrics"].get("corrupted_notes_improved", 0)
                                               for r in damaged) / denominator
        if denominator else None,
        "clean_pitch_edits": sum(r["metrics"].get("pitch_edits", 0) for r in clean),
        "clean_timing_edits": sum(r["metrics"].get("timing_edits", 0) for r in clean),
        "clean_duration_edits": sum(r["metrics"].get("duration_edits", 0) for r in clean),
        "clean_octave_displacements": sum(r["metrics"].get("octave_displacements", 0) for r in clean),
        "clean_octave_displacement_rate": sum(r["metrics"].get("octave_displacements", 0)
                                              for r in clean) / clean_notes if clean_notes else None,
        "clean_motif_disturbance_runs": sum(
            r["metrics"].get("motif_similarity_after") is not None
            and r["metrics"]["motif_similarity_after"] < r["metrics"]["motif_similarity_before"]
            for r in clean),
        "exact_recovery_rate": sum(r["metrics"]["exact_recovered_notes"] for r in damaged)
        / denominator if denominator else None,
        "unnecessary_edit_count": sum(r["metrics"]["unnecessary_edit_count"] for r in successful),
        "unnecessary_field_edits": sum(r["metrics"]["unnecessary_field_edits"] for r in successful),
        "clean_runs": len(clean), "clean_notes": clean_notes,
        "clean_false_positive_rate": sum(r["metrics"]["edited_notes"] for r in clean)
        / clean_notes if clean_notes else None,
        "made_worse_runs": sum(r["metrics"]["made_worse"] for r in successful),
        "mean_runtime_seconds": mean(r["runtime_seconds"] for r in successful) if successful else None,
        "total_runtime_seconds": sum(r["runtime_seconds"] for r in successful),
        "mean_distance_before": mean(r["metrics"]["edit_distance_before"] for r in damaged)
        if damaged else None,
        "mean_distance_after": mean(r["metrics"]["edit_distance_after"] for r in damaged)
        if damaged else None,
    }


def summary(report: dict) -> dict:
    results = report["results"]
    grouped = {}
    for field in ("dataset", "kind", "preset", "preservation", "workflow"):
        groups = defaultdict(list)
        for row in results:
            groups[str(row.get(field, report["manifest"]["dataset"]))].append(row)
        grouped[field] = {key: aggregate(rows) for key, rows in sorted(groups.items())}
    measured = [r for r in results if "metrics" in r]
    worst = sorted(measured, key=lambda r: (
        -r["metrics"]["preservation_penalized_distance"], r["entry"], r["kind"], r["preset"]
    ))[:10]

    def case(row):
        return {k: row[k] for k in ("entry", "kind", "preset", "preservation", "metrics",
                                     "failure_hypotheses")}

    return {"overall": aggregate(results), "groups": grouped,
            "skipped_cases": len(report["skipped"]),
            "failure_stage_mentions": dict(Counter(
                f["stage"] for r in measured for f in r["failure_hypotheses"])),
            "worst_examples": [case(r) for r in worst],
            "made_worse_examples": [case(r) for r in measured if r["metrics"]["made_worse"]],
            "runtime_vs_note_count": [
                {"entry": r["entry"], "kind": r["kind"], "preset": r["preset"],
                 "preservation": r["preservation"], "notes": r["metrics"]["note_count"],
                 "seconds": r["runtime_seconds"], "evaluations": r["evaluations"]}
                for r in measured]}


def markdown(report: dict, stats: dict) -> str:
    lines = ["# GLUE benchmark baseline", "", f"GLUE: {report['glue_version']}",
             f"Algorithm SHA-256: `{report['algorithm_sha256']}`", "",
             f"Dataset: {report['manifest']['dataset']}; split: {report['experiment']['split']}.",
             report["manifest"].get("provenance", "User-supplied references."), "",
             "This measures recovery of designated references, not objective musical quality.",
             "Top-ranked candidate only; no oracle selection or tuning. Clean controls are mandatory.",
             "Timing is machine-dependent; deterministic digests exclude runtime/environment.", "",
             "## Overall", "", "```json", json.dumps(stats["overall"], indent=2), "```", "",
             f"Skipped/inapplicable cases: {stats['skipped_cases']} (see JSON for reasons).", ""]
    for grouping, groups in stats["groups"].items():
        lines += [f"## By {grouping}", "",
                  "| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for key, values in groups.items():
            def fmt(value):
                return "n/a" if value is None else f"{value:.4f}"

            lines.append(f"| {key} | {values['runs']} | {fmt(values['exact_recovery_rate'])} | "
                         f"{values['unnecessary_edit_count']} / {values['unnecessary_field_edits']} | "
                         f"{fmt(values['clean_false_positive_rate'])} | {values['made_worse_runs']} | "
                         f"{fmt(values['mean_runtime_seconds'])} |")
        lines += [""]
    lines += ["## Worst examples (distance + 10 × unnecessary field edits)", ""]
    for row in stats["worst_examples"]:
        metrics = row["metrics"]
        lines.append(f"- {row['entry']} / {row['kind']} / {row['preset']} / {row['preservation']}: "
                     f"distance {metrics['edit_distance_before']:.3f} → "
                     f"{metrics['edit_distance_after']:.3f}; "
                     f"{metrics['unnecessary_field_edits']} unnecessary field edits.")
    lines += ["", "## Failure attribution", "",
              "Hypotheses are not proven causes. Coverage gaps are observed; their upstream cause",
              "may be analysis, harmony inference, filtering or permissions. Search and scoring",
              "cannot always be distinguished without a production trace API.", "",
              "```json", json.dumps(stats["failure_stage_mentions"], indent=2), "```", "",
              "See results.json for exact ledgers, source event bindings, component metrics,",
              "retained-alternative diagnostics, failures, and runtime vs note count.", ""]
    if stats["overall"]["edit_type_diagnostics"]:
        lines += ["## Candidate recall and search outcomes by edit type", "",
                  "```json", json.dumps(stats["overall"]["edit_type_diagnostics"], indent=2),
                  "```", "", "Full per-setting breakdowns are in summary.json; target ranks,",
                  "best component-scored states and rejection reasons are in results.json.", ""]
    return "\n".join(lines)


def write_report(report: dict, output: Path) -> None:
    """Never overwrite an earlier baseline or any source MIDI."""
    targets = [output / name for name in ("results.json", "results.csv", "summary.json", "summary.md")]
    if any(p.exists() for p in targets):
        raise FileExistsError("Report already exists; choose a new output directory")
    output.mkdir(parents=True, exist_ok=True)
    stats = summary(report)
    for path, value in ((targets[0], report), (targets[2], stats)):
        with path.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
    with targets[3].open("x", encoding="utf-8") as stream:
        stream.write(markdown(report, stats))
    flat = []
    for row in report["results"]:
        data = {key: row.get(key) for key in ("entry", "group", "split", "workflow", "kind", "seed",
                                              "preset", "preservation", "runtime_seconds", "error")}
        data.update(row.get("metrics", {}))
        flat.append({key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list, tuple))
                     else value for key, value in data.items()})
    with targets[1].open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=sorted({k for row in flat for k in row}))
        writer.writeheader()
        writer.writerows(flat)


def compare_reports(before: dict, after: dict) -> dict:
    """Comparison is allowed only with identical examples and experiment protocol."""
    if before["manifest"] != after["manifest"] or before["experiment"] != after["experiment"]:
        raise ValueError("Comparison requires identical manifests and experiment settings")
    if before["benchmark_sha256"] != after["benchmark_sha256"]:
        raise ValueError("Comparison requires the same benchmark implementation")
    a, b = summary(before), summary(after)
    return {"before_algorithm": before["algorithm_sha256"],
            "after_algorithm": after["algorithm_sha256"],
            "before": a["overall"], "after": b["overall"],
            "before_groups": a["groups"], "after_groups": b["groups"],
            "caution": "Compare all components, errors and skipped coverage, not one aggregate score.",
            "before_skipped": before["skipped"], "after_skipped": after["skipped"]}
