import json
from dataclasses import replace

import pytest

from glue.benchmark.__main__ import main
from glue.benchmark.corrupt import corrupt
from glue.benchmark.manifest import load_entry, local_path, read_manifest, window_manifest
from glue.benchmark.report import compare_reports, summary, write_report
from glue.benchmark.runner import Experiment, reproducible_payload, run_benchmark, run_case
from glue.benchmark.synthetic import generate_reference_manifest
from glue.fixes import musical as engine
from glue.fixes.musical_config import EditPermissions


@pytest.fixture
def corpus(tmp_path):
    return generate_reference_manifest(tmp_path / "references")


def test_blind_engine_boundary_and_no_oracle_selection(corpus, monkeypatch):
    from pathlib import Path

    truth, _ = load_entry(Path(corpus["root"]), corpus["entries"][0])
    damaged = corrupt(truth, "accidental", seed=13)
    actual = engine.generate_musical_repairs
    calls = []

    def spy(*clips, **kwargs):
        assert clips == damaged.clips and clips != truth
        assert set(kwargs) == {"preset", "preservation", "permissions"}
        calls.append((clips, kwargs))
        return actual(*clips, **kwargs)

    monkeypatch.setattr(engine, "generate_musical_repairs", spy)
    result = run_case(truth, damaged, preset="minimal", preservation=(0,),
                      permissions=EditPermissions(True, True, True))
    assert len(calls) == 1
    assert result["selected_candidate"] in {None, 0}


def test_reproducible_single_pair_and_clean_runs(corpus):
    from pathlib import Path

    original_bytes = {p: p.read_bytes() for p in Path(corpus["root"]).glob("*.mid")}
    experiment = Experiment(presets=("minimal",), preservations=(0, 100), kinds=("accidental",),
                            seeds=(3, 9), pair_preservation=((100, 0),))
    before = run_benchmark(corpus, experiment)
    after = run_benchmark(corpus, experiment)
    assert reproducible_payload(before) == reproducible_payload(after)
    assert before["reproducibility_digest"] == after["reproducibility_digest"]
    assert original_bytes == {p: p.read_bytes() for p in original_bytes}
    assert not before["skipped"]
    assert all("error" not in r for r in before["results"])
    assert {r["workflow"] for r in before["results"]} == {"single", "pair"}
    assert all(r["split"] == "calibration" for r in before["results"])
    for row in before["results"]:
        if row["kind"] != "clean":
            assert row["corruption_ledger"][0]["source_events"]["note_on"]["event_index"] >= 0
            entry = next(e for e in corpus["entries"] if e["id"] == row["entry"])
            _, documents = load_entry(Path(corpus["root"]), entry)
            for change in row["corruption_ledger"]:
                document = documents[change["slot"]]
                for name in ("note_on", "note_off"):
                    event = change["source_events"][name]
                    message = document._template.tracks[event["track"]][event["event_index"]]
                    assert message.note == change["before"]["pitch"]
                    assert message.channel == change["before"]["channel"]
        if all(p == 100 for p in row["preservation"]):
            assert row["metrics"]["edited_notes"] == 0
    # Clean is run once per setting, not duplicated for corruption seeds.
    assert len([r for r in before["results"] if r["kind"] == "clean"]) == 7


def test_reports_csv_summary_and_matched_comparison(corpus, tmp_path):
    report = run_benchmark(corpus, Experiment(presets=("minimal",), preservations=(100,),
                                             kinds=("accidental",)))
    output = tmp_path / "report"
    write_report(report, output)
    assert json.loads((output / "results.json").read_text())["algorithm_sha256"]
    assert "pitch_recovery_accuracy" in (output / "results.csv").read_text()
    assert "By preset" in (output / "summary.md").read_text(encoding="utf-8")
    assert summary(report)["overall"]["exact_recovery_rate"] == 0
    assert summary(report)["overall"]["clean_false_positive_rate"] == 0
    comparison = compare_reports(report, report)
    assert comparison["before"] == comparison["after"]
    with pytest.raises(ValueError, match="identical"):
        compare_reports(report, {**report, "experiment": {}})
    with pytest.raises(FileExistsError):
        write_report(report, output)


def test_manifest_hash_failure_is_visible_not_success(corpus):
    corpus["entries"][0]["sources"][0]["sha256"] = "bad"
    result = run_benchmark(corpus, Experiment(presets=("minimal",), kinds=(), preservations=(100,)))
    assert any("hash changed" in s["reason"] for s in result["skipped"])
    assert all(r["entry"] != "motif" for r in result["results"])


def test_engine_failure_is_recorded_and_counted(corpus, monkeypatch):
    def broken(*args, **kwargs):
        raise ValueError("deliberate engine failure")

    monkeypatch.setattr(engine, "generate_musical_repairs", broken)
    result = run_benchmark(corpus, Experiment(presets=("minimal",), kinds=(), preservations=(0,)))
    assert summary(result)["overall"]["errors"] == 3
    assert all("deliberate engine failure" in r["error"] for r in result["results"])


def test_windows_are_grouped_and_keep_event_identity(corpus):
    from pathlib import Path

    sliced = window_manifest(corpus, 4, per_piece=2)
    assert len(sliced["entries"]) == 8
    for entry in sliced["entries"]:
        source = next(e for e in corpus["entries"] if e["group"] == entry["group"])
        assert source["split"] == entry["split"]
        # A final empty tail is explicit, rather than fabricated reference material.
        try:
            clips, docs = load_entry(Path(corpus["root"]), entry)
        except ValueError as exc:
            assert "positive-duration" in str(exc)
            continue
        for clip, doc in zip(clips, docs, strict=True):
            originals = {n.id: n for n in doc.clip.notes}
            for note in clip.notes:
                assert note.id in doc.bindings
                assert note.duration_ticks == originals[note.id].duration_ticks
                assert note.onset_ticks + entry["window_beats"][0] * 480 == originals[note.id].onset_ticks


def test_path_escape_and_invalid_experiments(tmp_path):
    with pytest.raises(ValueError, match="inside root"):
        local_path(tmp_path, "../outside.mid")
    with pytest.raises(ValueError):
        Experiment(preservations=(101,))
    with pytest.raises(ValueError):
        Experiment(pair_preservation=((100,),))
    with pytest.raises(ValueError):
        replace(Experiment(), seeds=())


def test_cli_end_to_end_clean_control_and_relative_manifest(tmp_path, capsys):
    dataset = tmp_path / "dataset"
    main(["synthetic", "--output-dir", str(dataset)])
    manifest = dataset / "manifest.json"
    assert read_manifest(manifest)["root"] == str((dataset / "references").resolve())
    main(["run", str(manifest), "--output-dir", str(tmp_path / "out"), "--kinds",
          "--presets", "minimal", "--preservation", "100"])
    assert "Recorded 3 runs" in capsys.readouterr().out
    with pytest.raises(SystemExit) as exc:
        main(["run", str(manifest), "--output-dir", str(tmp_path / "empty"), "--max-notes", "1"])
    assert exc.value.code == 1
