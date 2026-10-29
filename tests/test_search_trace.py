from dataclasses import replace

from glue.benchmark.corrupt import Change, Corruption
from glue.benchmark.runner import run_case
from glue.benchmark.tracing import aggregate_traces
from glue.fixes.musical import generate_musical_repairs
from glue.fixes.musical_config import EditPermissions
from glue.fixes.search_trace import SearchTrace
from scripts.generate_v05_fixtures import musical_fixtures


def test_trace_is_deterministic_and_does_not_change_repair():
    fixtures = musical_fixtures()
    for name in ("pitch_only", "motif_accidental", "intentional_syncopation"):
        source = fixtures[name]
        baseline = generate_musical_repairs(source, preservation=(0,), preset="creative")
        first, second = SearchTrace(), SearchTrace()
        assert generate_musical_repairs(source, preservation=(0,), preset="creative",
                                        trace=first) == baseline
        assert generate_musical_repairs(source, preservation=(0,), preset="creative",
                                        trace=second) == baseline
        assert first == second
        assert len(first.states) <= first.max_states
        assert all(s["components"] is not None for s in first.states.values() if s["scored"])
        if baseline.candidates:
            assert first.winner and first.retained


def test_trace_truncation_and_reuse_are_explicit():
    source = musical_fixtures()["pitch_only"]
    observer = SearchTrace(max_states=1)
    result = generate_musical_repairs(source, preservation=(0,), preset="creative", trace=observer)
    assert observer.truncated and len(observer.states) == 1
    assert result == generate_musical_repairs(source, preservation=(0,), preset="creative")
    generate_musical_repairs(source, preservation=(100,), trace=observer)
    assert not observer.truncated and not observer.states and not observer.options and not observer.winner


def test_ground_truth_join_rank_recall_component_scores_and_locks():
    source = musical_fixtures()["pitch_only"]
    damaged_note = next(n for n in source.notes if n.pitch == 78)
    truth_note = replace(damaged_note, pitch=76)
    truth = source.with_notes(truth_note if n.id == damaged_note.id else n for n in source.notes)
    corruption = Corruption((source,), (Change(0, damaged_note.id, truth_note, damaged_note),),
                            "wrong_diatonic", 0, 1, 1)
    row = run_case((truth,), corruption, preset="creative", preservation=(0,),
                   permissions=EditPermissions(), tracing=True)
    target = row["search_trace"]["targets"][0]
    assert target["generated"] and target["global_rank"] >= 1 and target["field_rank"] >= 1
    assert target["entered_search"] and target["scored"] and target["survived_beam"]
    assert target["best_scored_state"]["components"]
    assert aggregate_traces([row])["pitch"]["candidate_recall"] == 1
    locked = run_case((truth,), corruption, preset="creative", preservation=(100,),
                      permissions=EditPermissions(), tracing=True)
    assert locked["search_trace"]["targets"][0]["failure_category"] == "blocked_by_permissions_or_lock"
    assert aggregate_traces([locked])["pitch"]["eligible_candidate_recall"] is None


def test_trace_records_safety_and_budget_rejections():
    f = musical_fixtures()
    observer = SearchTrace()
    generate_musical_repairs(f["budget_a"], f["budget_b"], preservation=(100, 0),
                             preset="creative", trace=observer)
    assert observer.states
    assert any(s["beam_pruned"] for s in observer.states.values())
    assert any("duplicate_state" in s["outcomes"] for s in observer.states.values())


def test_coordinated_trace_contains_full_multi_field_state():
    f = musical_fixtures()
    observer = SearchTrace()
    result = generate_musical_repairs(
        f["pitch_timing_a"], f["pitch_timing_b"], preservation=(100, 0),
        permissions=(EditPermissions(), EditPermissions(True, True, True)),
        preset="creative", trace=observer,
    )
    assert sum(c > 0 for c in result.candidates[0].counts) >= 2
    assert any(len({c[2] for c in s["changes"]}) >= 2 and s["scored"]
               for s in observer.states.values())
