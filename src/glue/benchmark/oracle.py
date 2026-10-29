"""Reference-aware diagnostics ONLY; never imported by production repair.

Distinguish a relaxed Cartesian value-availability upper bound from a feasible
no-collateral truth-subset oracle. Neither claims an exhaustive optimum over
arbitrary collateral edits. Search history is observed, not counterfactual causality.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from itertools import combinations
from math import ceil, isfinite

from glue.fixes import musical as engine
from glue.fixes.musical_config import EditPermissions, MusicalSearch
from glue.io.edited import validate_note_edits
from glue.models import MidiClip

FIELDS = ("pitch", "onset_ticks", "duration_ticks")
FACTOR_NAMES = (
    "harmony", "resolution", "melody", "voice_leading", "bass", "rhythm",
    "register", "collision", "unison", "motif_consistency",
)


def options_between(before: tuple[MidiClip, ...], after: tuple[MidiClip, ...]) -> tuple:
    result = []
    for slot, (a, b) in enumerate(zip(before, after, strict=True)):
        old = {n.id: n for n in a.notes}
        for note in b.notes:
            result.extend(engine._Option(slot, note.id, field, getattr(note, field),
                                         "benchmark-only counterfactual")
                          for field in FIELDS if getattr(note, field) != getattr(old[note.id], field))
    return tuple(result)


def validity(original: tuple[MidiClip, ...], revised: tuple[MidiClip, ...],
             preservation: tuple[int, ...], permissions: tuple[EditPermissions, ...],
             config: MusicalSearch) -> list[str]:
    reasons = []
    for slot, (a, b, p, allow) in enumerate(zip(original, revised, preservation, permissions, strict=True)):
        limit = 0 if p == 100 else max(1, ceil(config.max_edits * (1 - p / 100)))
        old = {n.id: n for n in a.notes}
        if sum(n != old[n.id] for n in b.notes) > limit:
            reasons.append(f"clip_{slot}_edit_limit_or_lock")
        try:
            validate_note_edits(a, b, pitch=allow.pitch, timing=allow.timing, duration=allow.duration,
                                onset_limit=config.onset_beats, duration_limit=config.duration_beats,
                                duration_fraction=config.duration_fraction)
        except ValueError as exc:
            reasons.append(f"safety: {exc}")
    if not isfinite(engine._retention(original, revised, config.weights)):
        reasons.append("structural_retention")
    return reasons


def score_parts(original: tuple[MidiClip, ...], revised: tuple[MidiClip, ...],
                preservation: tuple[int, ...], config: MusicalSearch) -> dict:
    w = config.weights
    score = engine.score_passage(revised, w)
    candidate = engine._candidate(original, revised, options_between(original, revised),
                                  score, preservation, config)
    # Named mapping, not positional after future score components are appended.
    labels = ("Harmony", "Resolution", "Melodic continuity", "Voice leading", "Bass movement",
              "Rhythm complementarity", "Register", "Collisions", "Unnecessary unisons",
              "Motif consistency (ambiguous)")
    factors = dict(zip(labels, (getattr(w, name) for name in FACTOR_NAMES), strict=True))
    for label, attr in (("Performance rhythm", "performance_rhythm"),
                        ("Contextual articulation", "articulation"), ("Octave context", "octave_context")):
        if hasattr(w, attr):
            factors[label] = getattr(w, attr)
    terms = {name: value * factors[name] for name, value in score.components if name in factors}
    raw = dict(score.components)
    for name in ("motif", "contour", "groove"):
        isolated = replace(w, **{n: getattr(w, n) if n == name else 0
                                 for n in ("motif", "contour", "groove")})
        cost = engine._retention(original, revised, isolated)
        terms[f"Retention: {name}"] = cost if isfinite(cost) else None
    edits = dict.fromkeys(("Pitch displacement", "Onset displacement", "Duration displacement",
                          "Edit count", "Preservation"), 0.0)
    for edit in candidate.edits:
        p = preservation[edit.slot] / 100
        ppq = original[edit.slot].ticks_per_beat
        edits["Pitch displacement"] += p * w.pitch_distance * abs(edit.after.pitch - edit.before.pitch)
        edits["Onset displacement"] += p * w.onset_distance * abs(
            edit.after.onset_ticks - edit.before.onset_ticks) / ppq
        edits["Duration displacement"] += p * w.duration_distance * abs(
            edit.after.duration_ticks - edit.before.duration_ticks) / ppq
        edits["Edit count"] += p * w.edit
        edits["Preservation"] += p * p * w.preservation
    terms.update(edits)
    if isfinite(candidate.objective):
        terms["Contextual relationships"] = candidate.objective - sum(v or 0 for v in terms.values())
    return {"raw_components": raw, "weighted_terms": terms,
            "objective": candidate.objective if isfinite(candidate.objective) else None,
            "structurally_rejected": not isfinite(candidate.objective)}


def decompose(original: tuple[MidiClip, ...], selected: tuple[MidiClip, ...],
              reference: tuple[MidiClip, ...], preservation: tuple[int, ...],
              config: MusicalSearch) -> dict:
    chosen = score_parts(original, selected, preservation, config)
    correct = score_parts(original, reference, preservation, config)
    margin = (correct["objective"] - chosen["objective"]
              if correct["objective"] is not None and chosen["objective"] is not None else None)
    terms = sorted(({"term": name, "truth_minus_selected": value - chosen["weighted_terms"].get(name, 0)}
                    for name, value in correct["weighted_terms"].items()
                    if value is not None and chosen["weighted_terms"].get(name, 0) is not None),
                   key=lambda t: (-t["truth_minus_selected"], t["term"]))
    leading = ", ".join(f"{t['term']} {t['truth_minus_selected']:+.3f}" for t in terms[:3]
                        if abs(t["truth_minus_selected"]) > 1e-9)
    explanation = ("Full-reference state is structurally rejected; no finite score margin."
                   if margin is None else
                   f"Full-reference state minus selected objective: {margin:+.3f}; "
                   f"largest losing terms: {leading or 'none'}. Positive terms favor selected.")
    return {"selected": chosen, "ground_truth": correct, "truth_minus_selected_margin": margin,
            "term_margins": terms, "explanation": explanation,
            "interpretation": "Positive margin favors selected under the objective; not musical ground truth."}


def explain_target(target: dict) -> str:
    label = f"{target['edit_type']} reference {target['reference_value']} for clip {target['slot']} note {target['note_id']}"
    if not target["eligible"]:
        return label + ": prohibited by explicit permission or preservation lock."
    if not target["generated"]:
        return label + ": absent from the generated bounded pool; inference versus filtering is unresolved."
    if not target["entered_search"]:
        return label + ": generated but never entered search."
    if not target["scored"]:
        return label + ": entered search but not scored: " + "; ".join(target["rejection_reasons"])
    if target["failure_category"] == "recovered":
        return label + ": selected."
    if target["survived_beam"]:
        return label + ": scored and survived in at least one state, but not selected; inspect score margins."
    if target["beam_pruned"]:
        return label + ": scored then pruned; pruning alone does not prove the cause of final selection."
    return label + ": scored; coordinated availability and objective gates require inspection."


def clean_causes(row: dict) -> dict:
    """Evidence-label attribution, not independently verified musical causation."""
    counts = Counter()
    for edit in row["edits"]:
        reason = " ".join(edit["reasons"]).lower()
        for field in FIELDS:
            if edit["before"][field] == edit["after"][field]:
                continue
            label = ("timing collision logic" if field == "onset_ticks" else
                     "duration logic" if field == "duration_ticks" else
                     "motif correction" if any(s in reason for s in ("motif correspondence", "repeated motif")) else
                     "register/voice correction" if any(s in reason for s in ("voice continuity", "octave", "contour", "register"))
                     else "harmony correction")
            counts[label] += 1
    if len(row["edits"]) > 1:
        counts["search interaction (overlapping tag)"] += 1
    return dict(counts)


def analyze_oracle(reference: tuple[MidiClip, ...], corrupted: tuple[MidiClip, ...], row: dict,
                   config: MusicalSearch) -> dict:
    """Analyze an already finished blind repair; never call production search."""
    permissions = (EditPermissions(**row["permissions"]),) * len(corrupted)
    preserves = tuple(row["preservation"])
    selected_options = tuple(engine._Option(e["slot"], e["note_id"], f, e["after"][f], "selected")
                             for e in row["edits"] for f in FIELDS if e["before"][f] != e["after"][f])
    selected = engine._apply(corrupted, selected_options)
    if row["kind"] == "clean":
        return {"clean_causes": clean_causes(row), "score_loss": decompose(
            corrupted, selected, reference, preserves, config)}
    targets = row["search_trace"]["targets"]
    corrections = options_between(corrupted, reference)
    available = {(o["slot"], o["note_id"], o["field"], o["value"])
                 for o in row["search_trace"]["candidate_set"]}
    units = sorted({(o.slot, o.note_id) for o in corrections})
    if len(units) > 10:
        raise ValueError("Truth-subset oracle capped at ten corrupted notes; no silent approximate ceiling")
    complete = [u for u in units if all((o.slot, o.note_id, o.field, o.value) in available
                                       for o in corrections if (o.slot, o.note_id) == u)]
    best = 0
    rejected = Counter()
    for count in range(1, len(complete) + 1):
        for subset in combinations(complete, count):
            options = tuple(o for o in corrections if (o.slot, o.note_id) in subset)
            reasons = validity(corrupted, engine._apply(corrupted, options), preserves, permissions, config)
            if reasons:
                rejected.update(reasons)
            else:
                best = max(best, count)
    loss = decompose(corrupted, selected, reference, preserves, config)
    return {"corrupted_notes": len(units), "available_exact_notes_upper_bound": len(complete),
            "feasible_no_collateral_exact_notes": best,
            "actual_exact_notes": row["metrics"]["exact_recovered_notes"],
            "oracle_scope": "Exhaustive truth-only subsets, not arbitrary collateral states; availability is a relaxed upper bound.",
            "oracle_rejections": dict(rejected),
            "full_truth_rejections": validity(corrupted, reference, preserves, permissions, config),
            "targets": [{**{k: t[k] for k in ("slot", "note_id", "edit_type", "reference_value",
                         "eligible", "generated", "field_rank", "global_rank", "entered_search",
                         "scored", "survived_beam", "beam_pruned", "failure_category")},
                         "top_k": {str(k): t["generated"] and t["field_rank"] <= k for k in (1, 3, 5)},
                         "explanation": explain_target(t)} for t in targets],
            "coordinated": row["search_trace"]["coordinated"], "score_loss": loss}


def aggregate_oracles(rows: list[dict]) -> dict:
    damaged = [r for r in rows if "corrupted_notes" in r["oracle"]]
    total = sum(r["oracle"]["corrupted_notes"] for r in damaged)
    result = {name: sum(r["oracle"][name] for r in damaged) / total if total else None
              for name in ("available_exact_notes_upper_bound", "feasible_no_collateral_exact_notes", "actual_exact_notes")}
    result["corrupted_note_observations"] = total
    result["top_k"] = {}
    for kind in ("pitch", "timing", "duration"):
        targets = [t for r in damaged for t in r["oracle"]["targets"] if t["edit_type"] == kind]
        result["top_k"][kind] = {str(k): sum(t["top_k"][str(k)] for t in targets) / len(targets)
                                  if targets else None for k in (1, 3, 5)}
    causes = Counter()
    for r in rows:
        causes.update(r["oracle"].get("clean_causes", {}))
    result["clean_edit_cause_tags"] = dict(causes)
    octave = [r for r in damaged if r["kind"] == "octave"]
    pitch = [t for r in octave for t in r["oracle"]["targets"] if t["edit_type"] == "pitch"]
    result["octave"] = {"targets": len(pitch), "generated": sum(t["generated"] for t in pitch),
                        "selected_reference_pitch": sum(t["failure_category"] == "recovered" for t in pitch),
                        "exact_notes": sum(r["oracle"]["actual_exact_notes"] for r in octave)}
    joint = [r["oracle"] for r in damaged if r["oracle"]["coordinated"]["target_fields"] > 1]
    result["coordinated"] = {"cases": len(joint),
        "all_values_generated": sum(o["coordinated"]["all_generated"] for o in joint),
        "entered_search": sum(o["coordinated"]["entered_search"] for o in joint),
        "scored": sum(o["coordinated"]["scored"] for o in joint),
        "survived": sum(o["coordinated"]["survived_beam"] for o in joint),
        "all_corrupted_notes_recovered": sum(o["actual_exact_notes"] == o["corrupted_notes"] for o in joint)}
    return result
