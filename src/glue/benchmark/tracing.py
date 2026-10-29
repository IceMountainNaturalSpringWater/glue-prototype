"""Ground-truth joins happen after search, never in the optimizer."""

from __future__ import annotations

from collections import Counter, defaultdict

from glue.fixes.search_trace import SearchTrace

from .corrupt import Corruption

EDIT_TYPES = {"pitch": "pitch", "onset_ticks": "timing", "duration_ticks": "duration"}


def targets(corruption: Corruption, trace: SearchTrace, repair) -> dict:
    """Mutually exclusive observed outcomes; unavailable causes remain explicit.

    A pruned state can still win: production retains all improving states outside
    the beam. Therefore pruning alone is never claimed to cause a scoring loss.
    Analysis failure needs external musical annotations; a protected-tone gate is
    reported as evidence, not proof that the musical analysis was objectively wrong.
    """
    expected = {(c.slot, c.note_id, f, getattr(c.before, f))
                for c in corruption.changes for f in c.fields}
    states = list(trace.states.values())
    joint = [s for s in states if expected and expected <= set(s["changes"])]
    rows = []
    for change in corruption.changes:
        for name in change.fields:
            key = (change.slot, change.note_id, name, getattr(change.before, name))
            matching = [o for o in trace.options if
                        (o["slot"], o["note_id"], o["field"], o["value"]) == key]
            visits = [s for s in states if key in s["changes"]]
            scored = [s for s in visits if s["scored"]]
            recovered = key in trace.winner
            allowed = repair.preservation[change.slot] < 100 and getattr(
                repair.permissions[change.slot], EDIT_TYPES[name])
            if recovered:
                category = "recovered"
            elif not allowed:
                category = "blocked_by_permissions_or_lock"
            elif trace.truncated:
                category = "trace_incomplete"
            elif not matching:
                category = "correct_candidate_never_generated"
            elif any("improving" in s["outcomes"] for s in visits):
                category = "scoring_preferred_another_result"
            elif scored and len(expected) > 1 and not any(s["scored"] for s in joint):
                category = "required_combination_not_discovered"
            elif scored and any(s["survived_beam"] for s in scored):
                category = "scoring_preferred_another_result"
            elif scored and any(s["beam_pruned"] for s in scored):
                category = "correct_candidate_generated_but_pruned"
            elif visits:
                category = "constraint_or_budget_rejection"
            else:
                category = "generated_not_entered_search"
            rows.append({"slot": change.slot, "note_id": change.note_id,
                         "edit_type": EDIT_TYPES[name], "field": name,
                         "reference_value": getattr(change.before, name),
                         "generated": bool(matching), "eligible": allowed,
                         "global_rank": matching[0]["global_rank"] if matching else None,
                         "field_rank": matching[0]["field_rank"] if matching else None,
                         "entered_search": bool(visits), "scored": bool(scored),
                         "survived_beam": any(s["survived_beam"] for s in visits),
                         "beam_pruned": any(s["beam_pruned"] for s in visits),
                         "failure_category": category,
                         "rejection_reasons": sorted({v for s in visits for v in s["outcomes"]
                                                       if v != "improving"}),
                         "scored_state_count": len(scored),
                         "best_scored_state": min(scored, key=lambda s: (
                             s["objective"] if s["objective"] is not None else float("inf"),
                             s["changes"])) if scored else None})
    return {"targets": rows, "winner": trace.winner, "retained": trace.retained,
            "candidate_set": trace.options,
            "inferred_voices": trace.note_contexts,
            "coordinated": {"target_fields": len(expected),
                            "all_generated": bool(expected) and all(r["generated"] for r in rows),
                            "entered_search": bool(joint),
                            "scored": any(s["scored"] for s in joint),
                            "survived_beam": any(s["survived_beam"] for s in joint),
                            "beam_pruned": any(s["beam_pruned"] for s in joint)},
            "state_count": len(states), "truncated": trace.truncated,
            "analysis_failure": "Undetermined without independently annotated musical context."}


def aggregate_traces(rows: list[dict]) -> dict:
    grouped = defaultdict(list)
    for row in rows:
        for target in row.get("search_trace", {}).get("targets", []):
            grouped[target["edit_type"]].append(target)
    result = {}
    for edit_type, items in sorted(grouped.items()):
        categories = Counter(t["failure_category"] for t in items)
        eligible = [t for t in items if t["eligible"]]
        failures = [t for t in eligible if t["failure_category"] != "recovered"]
        result[edit_type] = {
            "corrupted_fields": len(items), "eligible_fields": len(eligible),
            "candidate_recall": sum(t["generated"] for t in items) / len(items),
            "eligible_candidate_recall": sum(t["generated"] for t in eligible) / len(eligible)
            if eligible else None,
            "failure_counts": dict(categories),
            "category_percent_of_all_targets": {k: 100 * v / len(items)
                                                 for k, v in sorted(categories.items())},
            "category_percent_of_eligible_failures": {
                k: 100 * v / len(failures) for k, v in
                sorted(Counter(t["failure_category"] for t in failures).items())},
            "analysis_failure_percent": None,
        }
    return result
