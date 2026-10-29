from pathlib import Path

import pytest

from glue.benchmark.manifest import build_manifest, quarantine_split_conflicts, validate_manifest
from glue.benchmark.synthetic import generate_reference_manifest
from scripts.benchmark_real_corpora import _audit, select_subset


def test_pop_release_variants_do_not_become_independent_works(tmp_path):
    from glue.io import write_midi
    from scripts.generate_v05_fixtures import clip

    directory = tmp_path / "POP909" / "001"
    (directory / "versions").mkdir(parents=True)
    midi = clip([(60, 0, 1, 0)])
    write_midi(midi, directory / "001.mid")
    write_midi(midi, directory / "versions" / "001-v1.mid")
    result = build_manifest(tmp_path, dataset="pop909")
    assert result["discovered_files"] == 2
    assert result["excluded_variant_files"] == 1
    assert result["entries"][0]["group"] == "001"


def test_quarantine_excludes_entire_connected_groups_without_reassigning():
    entries = [
        {"id": "a", "group": "work1", "split": "calibration", "sources": [{"sha256": "hash1"}]},
        {"id": "b", "group": "work1", "split": "evaluation", "sources": [{"sha256": "hash2"}]},
        {"id": "c", "group": "work2", "split": "evaluation", "sources": [{"sha256": "hash2"}]},
        {"id": "d", "group": "work3", "split": "calibration", "sources": [{"sha256": "hash3"}]},
    ]
    manifest = {"schema": 1, "entries": entries}
    with pytest.raises(ValueError, match="leakage"):
        validate_manifest(manifest)
    cleaned = quarantine_split_conflicts(manifest)
    assert cleaned["entries"] == [entries[3]]
    assert cleaned["quarantined_entries"] == entries[:3]
    validate_manifest(cleaned)
    assert len(manifest["entries"]) == 4


def test_audit_and_subset_are_deterministic_and_keep_splits(tmp_path):
    manifest = generate_reference_manifest(tmp_path / "references")
    audit = [_audit((str(Path(manifest["root"])), entry)) for entry in manifest["entries"]]
    assert all(row["usable"] for row in audit)
    first = select_subset(manifest, audit, per_split=4)
    assert first == select_subset(manifest, audit, per_split=4)
    original_splits = {e["group"]: e["split"] for e in manifest["entries"]}
    assert all(e["split"] == original_splits[e["group"]] for e in first["entries"])


def test_real_summary_uses_note_weighted_preservation_and_explicit_empty_denominators():
    from scripts.summarize_real_baseline import group_metrics

    empty = group_metrics([])
    assert empty["untouched_note_preservation"] is None
    assert empty["clean_false_positive_rate"] is None
    row = {"kind": "accidental", "runtime_seconds": 1, "metrics": {
        "corrupted_notes": 1, "exact_recovered_notes": 1, "unnecessary_edit_count": 2,
        "unnecessary_field_edits": 2, "made_worse": True, "untouched_notes": 9,
        "edit_distance_before": 1, "edit_distance_after": 2,
        "onset_error_beats_total_before": 0, "onset_error_beats_total_after": 0.25,
        "duration_error_beats_total_before": 0, "duration_error_beats_total_after": 0,
    }}
    result = group_metrics([row])
    assert result["untouched_note_preservation"] == 7 / 9
    assert result["exact_recovery_rate"] == 1
    assert result["onset_error_beats_after"] == 0.25


def test_replay_normalization_ignores_only_wall_clock_fields():
    from scripts.repeat_real_baseline import identity, normalized

    row = {"entry": "piece", "kind": "clean", "preset": "minimal", "seed": 52,
           "preservation": (0, 0), "runtime_seconds": 1.0, "diagnostic_seconds": 0.1,
           "search_trace": {"winner": ((0, 1, "pitch", 60),)}, "metrics": {"edited_notes": 1}}
    result = normalized(row)
    assert "runtime_seconds" not in result and "diagnostic_seconds" not in result
    assert result["search_trace"]["winner"] == [[0, 1, "pitch", 60]]
    assert result["metrics"] == row["metrics"]
    assert identity(result) == identity(row)
    assert row["runtime_seconds"] == 1.0
