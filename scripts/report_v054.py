"""Matched V0.5.3/V0.5.4 actual/oracle report, without pooling corpora or splits."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from glue.benchmark.oracle import aggregate_oracles, clean_causes
from scripts.compare_candidate_baselines import compare, key


def observed_counterfactuals(row: dict, oracle: dict) -> list[dict]:
    """Decompose saved observed states, without rerunning or changing the engine."""
    factors = dict(zip(("Harmony", "Resolution", "Melodic continuity", "Voice leading", "Bass movement",
                        "Rhythm complementarity", "Register", "Collisions", "Unnecessary unisons",
                        "Motif consistency (ambiguous)", "Performance rhythm", "Contextual articulation", "Octave context"),
                       ("harmony", "resolution", "melody", "voice_leading", "bass", "rhythm", "register",
                        "collision", "unison", "motif_consistency", "performance_rhythm", "articulation", "octave_context"),
                       strict=True))
    selected = oracle["score_loss"]["selected"]
    terms = selected["weighted_terms"]
    chosen = {name: terms.get(name, 0) for name in factors}
    chosen["Retention total"] = sum(terms.get("Retention: " + k, 0) or 0 for k in ("motif", "contour", "groove"))
    chosen["Edit total"] = sum(terms.get(k, 0) or 0 for k in
                              ("Pitch displacement", "Onset displacement", "Duration displacement", "Edit count", "Preservation"))
    result = []
    for target in row.get("search_trace", {}).get("targets", []):
        state = target.get("best_scored_state")
        if not state or state["objective"] is None or target["failure_category"] == "recovered":
            continue
        weighted = {name: value * row["search_config"]["weights"][factors[name]]
                    for name, value in state["components"].items() if name in factors}
        weighted["Retention total"] = state["retention_cost"]
        weighted["Edit total"] = state["edit_cost"]
        weighted["Unmapped residual"] = state["objective"] - sum(weighted.values())
        deltas = sorted(({"term": name, "reference_state_minus_selected": value - chosen.get(name, 0)}
                         for name, value in weighted.items()),
                        key=lambda x: (-x["reference_state_minus_selected"], x["term"]))
        margin = state["objective"] - selected["objective"]
        leading = ", ".join(f"{x['term']} {x['reference_state_minus_selected']:+.3f}"
                            for x in deltas[:3] if abs(x["reference_state_minus_selected"]) > 1e-9)
        result.append({"note_id": target["note_id"], "slot": target["slot"], "field": target["field"],
            "reference_value": target["reference_value"], "field_rank": target["field_rank"],
            "selected_weighted_terms": chosen, "reference_state_weighted_terms": weighted,
            "score_margin": margin, "term_margins": deltas, "state_changes": state["changes"],
            "rounds": state["rounds"], "state_survived": state["survived_beam"],
            "state_pruned": state["beam_pruned"], "any_matching_state_survived": target["survived_beam"],
            "explanation": f"Reference {target['field']} {target['reference_value']} was scored at "
                f"rounds {state['rounds']}; best observed containing state costs {margin:+.3f} versus selected. "
                f"Leading losing terms: {leading or 'none'}. The state can contain collateral edits; "
                "pruning alone does not prove why selection lost."})
    return result


def groups(rows: list[dict]) -> dict[str, list[dict]]:
    result = {"all": rows, "unlocked": [r for r in rows if all(p < 100 for p in r["preservation"])]}
    result.update({f"preservation_{p}": [r for r in rows if all(v == p for v in r["preservation"])]
                   for p in (0, 25, 50, 75, 100)})
    result.update({f"preset_{p}": [r for r in rows if r["preset"] == p]
                   for p in ("minimal", "balanced", "creative")})
    result.update({f"kind_{k}": [r for r in rows if r["kind"] == k] for k in sorted({r["kind"] for r in rows})})
    return result


def compare_with_oracles(before: dict, after: dict, old_oracle: dict, new_oracle: dict) -> dict:
    for report, oracle in ((before, old_oracle), (after, new_oracle)):
        if report["algorithm_sha256"] != oracle["algorithm_sha256"]:
            raise ValueError("Oracle and measurement engine differ")
        if {key(r) for r in report["results"]} != {key(r) for r in oracle["results"]}:
            raise ValueError("Oracle and measurement cases differ")
    result = compare(before["results"], after["results"])
    result["observed_counterfactuals"] = {}
    for phase, report, matrix in (("before", old_oracle, before), ("after", new_oracle, after)):
        inputs = {key(r): r for r in matrix["results"]}
        cases = []
        for row in report["results"]:
            diagnostics = observed_counterfactuals(inputs[key(row)], row["oracle"])
            if diagnostics:
                cases.append({**{k: row[k] for k in ("entry", "kind", "preset", "preservation", "seed")},
                              "observed_reference_states": diagnostics})
        result["observed_counterfactuals"][phase] = cases
        # Reclassify legacy diagnostic tags from recorded reasons. A generic
        # mention of motif retention does not establish motif-generated edits.
        classified = [{**r, "oracle": {**r["oracle"], "clean_causes": clean_causes(inputs[key(r)])}}
                      if r["kind"] == "clean" else r for r in report["results"]]
        for name, rows in groups(classified).items():
            result["groups"][name][phase]["oracle"] = aggregate_oracles(rows)
    result["engine_fingerprints"] = [before["algorithm_sha256"], after["algorithm_sha256"]]
    return result


def markdown(comparisons: dict) -> str:
    def pct(value):
        return "n/a" if value is None else f"{value * 100:.2f}%"

    lines = ["# V0.5.3 -> V0.5.4: actual recovery versus oracle", "",
             "No pooled corpus score. Rates repeat passages across settings, not independent compositions.",
             "Oracle = feasible no-collateral reference subsets. Availability is a relaxed upper bound,",
             "not an exhaustive optimum over arbitrary collateral edits. Top-k ranks are per note/edit field.", ""]
    for corpus, splits in comparisons.items():
        for split, result in splits.items():
            lines += [f"## {corpus} / {split}", "",
                      "| Group | Actual exact | Feasible oracle | Available upper bound | Clean FP | Untouched preservation | Mean seconds |",
                      "|---|---:|---:|---:|---:|---:|---:|"]
            for group, values in result["groups"].items():
                if group.startswith("kind_"):
                    continue
                cells = []
                for name in ("exact_recovery_rate", "feasible_no_collateral_exact_notes",
                             "available_exact_notes_upper_bound", "clean_false_positive_rate", "untouched_note_preservation"):
                    cells.append(" -> ".join(pct(values[p].get(name, values[p]["oracle"].get(name)))
                                               for p in ("before", "after")))
                cells.append(" -> ".join("n/a" if values[p]["mean_runtime_seconds"] is None
                                          else f"{values[p]['mean_runtime_seconds']:.3f}" for p in ("before", "after")))
                lines.append(f"| {group} | " + " | ".join(cells) + " |")
            for scope in ("all", "unlocked"):
                values = result["groups"][scope]
                lines += ["", f"### Candidate recall: {scope}", "",
                          "| Edit type | Any rank | Top 1 | Top 3 | Top 5 |", "|---|---:|---:|---:|---:|"]
                for field in ("pitch", "timing", "duration"):
                    cells = [" -> ".join(pct(values[p]["edit_type_diagnostics"].get(field, {}).get("candidate_recall"))
                                         for p in ("before", "after"))]
                    cells += [" -> ".join(pct(values[p]["oracle"]["top_k"][field][str(k)])
                                          for p in ("before", "after")) for k in (1, 3, 5)]
                    lines.append(f"| {field} | " + " | ".join(cells) + " |")
            values = result["groups"]["all"]
            lines += ["", "### Safety, octave, coordinated and failure diagnostics", "", "```json",
                      json.dumps({p: {"clean_octave_edits": values[p]["clean_octave_displacements"],
                                      "clean_octave_rate": values[p]["clean_octave_displacement_rate"],
                                      "unnecessary_edits": values[p]["unnecessary_edits_by_field"],
                                      "octave": values[p]["oracle"]["octave"],
                                      "coordinated": values[p]["oracle"]["coordinated"],
                                      "clean_cause_tags": values[p]["oracle"]["clean_edit_cause_tags"]}
                                  for p in ("before", "after")}, indent=2), "```", "",
                      "Failure migration:", "", "| Before | After | Fields |", "|---|---|---:|"]
            lines += [f"| {r['before']} | {r['after']} | {r['fields']} |" for r in result["failure_migration"]]
            lines += ["", "Analysis attribution is undetermined; clean-cause tags are hypotheses.",
                      "Per-case side-by-side raw and weighted scores and counterfactual explanations are in oracle.json.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, default=Path("benchmarks/baselines/v053-real"))
    parser.add_argument("--oracle-before", type=Path, default=Path("benchmarks/baselines/v054-oracle-v053"))
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--split", choices=("calibration", "evaluation", "all"), default="calibration")
    args = parser.parse_args()
    comparisons = {}
    for name in ("pop909", "maestro"):
        comparisons[name] = {}
        for split in ("calibration", "evaluation"):
            if args.split not in (split, "all"):
                continue
            def read(root, file, name=name, split=split):
                return json.loads((root / name / split / file).read_text(encoding="utf-8"))
            data = compare_with_oracles(read(args.before, "results.json"), read(args.after, "results.json"),
                                        read(args.oracle_before, "oracle.json"), read(args.after, "oracle.json"))
            comparisons[name][split] = data
            for p in ("before", "after"):
                m = data["groups"]["all"][p]
                print(name, split, p, {k: m[k] for k in ("exact_recovery_rate", "clean_false_positive_rate",
                    "clean_octave_displacements", "mean_runtime_seconds")},
                    "oracle", m["oracle"]["feasible_no_collateral_exact_notes"], flush=True)
    output = args.after / f"quality-comparison-{args.split}"
    with output.with_suffix(".json").open("x", encoding="utf-8") as stream:
        json.dump(comparisons, stream, indent=2, sort_keys=True, allow_nan=False)
    with output.with_suffix(".md").open("x", encoding="utf-8") as stream:
        stream.write(markdown(comparisons))


if __name__ == "__main__":
    main()
