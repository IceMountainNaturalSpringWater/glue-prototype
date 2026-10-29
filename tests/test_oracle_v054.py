from dataclasses import replace

import pytest

from glue.benchmark.corrupt import Change, Corruption
from glue.benchmark.oracle import aggregate_oracles, analyze_oracle, score_parts
from glue.benchmark.runner import run_case
from glue.fixes.musical_config import EditPermissions, musical_search_for
from scripts.generate_v05_fixtures import musical_fixtures


def example(preservation=0):
    damaged = musical_fixtures()["pitch_only"]
    note = next(n for n in damaged.notes if n.pitch == 78)
    truth = replace(note, pitch=76)
    reference = damaged.with_notes(truth if n.id == note.id else n for n in damaged.notes)
    corruption = Corruption((damaged,), (Change(0, note.id, truth, note),), "accidental", 0, 1, 1)
    row = run_case((reference,), corruption, preset="creative", preservation=(preservation,),
                   permissions=EditPermissions(), tracing=True)
    row["kind"] = "accidental"
    return reference, damaged, row


def test_oracle_is_posthoc_bounded_and_does_not_call_repair(monkeypatch):
    reference, damaged, row = example()
    monkeypatch.setattr("glue.fixes.musical.generate_musical_repairs",
                        lambda *a, **k: pytest.fail("Oracle must never call blind repair"))
    original = (reference, damaged)
    report = analyze_oracle((reference,), (damaged,), row, musical_search_for("creative"))
    assert report["available_exact_notes_upper_bound"] == 1
    assert report["feasible_no_collateral_exact_notes"] == 1
    assert report["targets"][0]["generated"]
    assert report == analyze_oracle((reference,), (damaged,), row, musical_search_for("creative"))
    assert (reference, damaged) == original


def test_oracle_respects_locks_and_top_k_denominators():
    reference, damaged, row = example(100)
    report = analyze_oracle((reference,), (damaged,), row, musical_search_for("creative"))
    assert report["available_exact_notes_upper_bound"] == 0
    assert report["feasible_no_collateral_exact_notes"] == 0
    assert report["full_truth_rejections"]
    stats = aggregate_oracles([{"kind": "accidental", "oracle": report}])
    assert stats["top_k"]["pitch"] == {"1": 0, "3": 0, "5": 0}
    assert stats["top_k"]["timing"]["1"] is None


def test_score_decomposition_reconciles_to_objective():
    reference, damaged, _ = example()
    for p in (0, 25, 75):
        result = score_parts((damaged,), (reference,), (p,), musical_search_for("creative"))
        assert sum(result["weighted_terms"].values()) == pytest.approx(result["objective"])
        assert result["weighted_terms"]["Pitch displacement"] == pytest.approx(p / 100 * 2 * .08)


def test_clean_oracle_reports_false_positive_causes():
    _, damaged, _ = example()
    clean = Corruption((damaged,), (), "clean", 0, 1, 1)
    row = run_case((damaged,), clean, preset="creative", preservation=(0,),
                   permissions=EditPermissions(), tracing=True)
    row["kind"] = "clean"
    report = analyze_oracle((damaged,), (damaged,), row, musical_search_for("creative"))
    assert report["clean_causes"]
    assert "corrupted_notes" not in report


def test_matched_oracle_report_rejects_engine_or_case_mismatch():
    from scripts.report_v054 import compare_with_oracles, markdown

    reference, damaged, row = example()
    row.update(entry="unit", seed=52, corruption_ledger=[])
    oracle = analyze_oracle((reference,), (damaged,), row, musical_search_for("creative"))
    report = {"algorithm_sha256": "unit", "results": [row]}
    diagnostics = {"algorithm_sha256": "unit", "results": [{**row, "oracle": oracle}]}
    compared = compare_with_oracles(report, report, diagnostics, diagnostics)
    assert compared["groups"]["all"]["after"]["oracle"]["feasible_no_collateral_exact_notes"] == 1
    assert "n/a" in markdown({"unit": {"calibration": compared}})
    with pytest.raises(ValueError, match="engine differ"):
        compare_with_oracles(report, report, diagnostics, {**diagnostics, "algorithm_sha256": "wrong"})
    with pytest.raises(ValueError, match="cases differ"):
        compare_with_oracles(report, report, diagnostics, {**diagnostics, "results": []})


def test_clean_cause_does_not_confuse_generic_motif_retention_with_motif_generation():
    from glue.benchmark.oracle import clean_causes

    edit = {"before": {"pitch": 60, "onset_ticks": 0, "duration_ticks": 480},
            "after": {"pitch": 61, "onset_ticks": 0, "duration_ticks": 480},
            "reasons": ["Full-passage harmony and phrase/motif retention favor this alternative."]}
    assert clean_causes({"edits": [edit]}) == {"harmony correction": 1}
    assert clean_causes({"edits": [{**edit, "reasons": ["motif correspondence"]}]}) == {"motif correction": 1}


def test_observed_counterfactual_uses_recorded_state_and_stored_weights():
    from scripts.report_v054 import observed_counterfactuals

    reference, damaged, row = example(50)
    oracle = analyze_oracle((reference,), (damaged,), row, musical_search_for("creative"))
    recorded = observed_counterfactuals(row, oracle)
    assert recorded
    first = recorded[0]
    assert first["reference_state_weighted_terms"]["Unmapped residual"] == pytest.approx(0)
    assert sum(x["reference_state_minus_selected"] for x in first["term_margins"]) == pytest.approx(first["score_margin"])
    assert "rounds" in first["explanation"] and first["state_changes"]
