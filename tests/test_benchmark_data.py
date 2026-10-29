import json
from dataclasses import replace

import pytest

from glue.benchmark.corrupt import KINDS, corrupt
from glue.benchmark.manifest import build_manifest, load_entry, validate_manifest
from glue.benchmark.metrics import measure
from glue.io import write_midi
from scripts.generate_v05_fixtures import clip


@pytest.fixture
def references():
    melody = clip([(p, i + 0.25, 0.5, 0)
                   for i, p in enumerate((60, 62, 64, 67) * 2)], "melody")
    harmony = clip([(p, i, 0.75, 0) for i in range(8)
                    for p in ((48, 52, 55) if i < 4 else (53, 57, 60))], "harmony")
    return tuple(replace(c, length_ticks=4800,
                         tracks=tuple(replace(t, length_ticks=4800) for t in c.tracks))
                 for c in (melody, harmony))


@pytest.mark.parametrize("kind", KINDS)
def test_corruptions_deterministic_exact_ledger_and_immutable(references, kind):
    before = tuple(hash(c) for c in references)
    result = corrupt(references, kind, seed=7)
    assert result == corrupt(references, kind, seed=7)
    assert not result.skipped, (kind, result.skipped)
    assert tuple(hash(c) for c in references) == before
    identities = {(c.slot, c.note_id) for c in result.changes}
    assert len(identities) == len(result.changes)
    for slot, (source, damaged) in enumerate(zip(references, result.clips, strict=True)):
        new = {n.id: n for n in damaged.notes}
        assert source.tempo_changes == damaged.tempo_changes
        assert source.tracks == damaged.tracks
        for n in source.notes:
            assert (n != new[n.id]) == ((slot, n.id) in identities)
            assert n.velocity == new[n.id].velocity
            assert n.channel == new[n.id].channel
            assert n.track == new[n.id].track
            assert 0 <= new[n.id].pitch <= 127 and new[n.id].duration_ticks > 0
    exact = measure(references, result, references)
    assert exact["exact_note_recovery"] == 1
    assert exact["edit_distance_after"] == 0
    assert exact["unnecessary_edit_count"] == 0


def test_metric_arithmetic_and_collateral_fields(references):
    damaged = corrupt(references, "accidental", seed=7)
    change = damaged.changes[0]
    revised = list(references)
    revised[change.slot] = revised[change.slot].with_notes(
        replace(n, onset_ticks=n.onset_ticks + 120) if n.id == change.note_id else n
        for n in revised[change.slot].notes
    )
    result = measure(references, damaged, tuple(revised))
    assert result["pitch_recovery_accuracy"] == 1
    assert result["pitch_class_recovery"] == 1
    assert result["exact_note_recovery"] == 0
    assert result["onset_error_beats_total_after"] == 0.25
    assert result["edit_distance_before"] == 1
    assert result["edit_distance_after"] == 0.25
    assert result["unnecessary_edit_count"] == 0
    assert result["unnecessary_field_edits"] == 1
    assert result["preservation_penalized_distance"] == 10.25
    assert result["untouched_note_preservation"] == 1


def test_clean_metrics_and_pair_proxies(references):
    pristine = corrupt(references, "clean")
    result = measure(references, pristine, references)
    assert result["clean_false_positive_rate"] == 0
    assert result["exact_note_recovery"] is None
    assert result["motif_similarity_after"] == 1
    assert result["melodic_contour_similarity_after"] == 1
    assert result["simultaneous_attack_density_after"] == 0
    damaged = corrupt(references, "accidental").clips
    false_positive = measure(references, pristine, damaged)
    assert false_positive["unnecessary_edit_count"] == 1
    assert false_positive["clean_false_positive_rate"] == 1 / 32
    assert false_positive["made_worse"]


def test_skips_invalid_parameters_and_ledger(references):
    assert corrupt((clip([(60, 0, 1, 0)]),), "motif").skipped
    with pytest.raises(ValueError):
        corrupt(references, "late", severity=0)
    with pytest.raises(ValueError):
        corrupt(references, "late", count=0)
    result = corrupt(references, "late")
    with pytest.raises(ValueError, match="ledger"):
        measure(references, replace(result, changes=()), result.clips)


def test_local_inventory_hashes_group_splits_and_original_bytes(tmp_path, references):
    path = write_midi(references[0], tmp_path / "reference.mid")
    original = path.read_bytes()
    manifest = build_manifest(tmp_path)
    assert manifest == build_manifest(tmp_path)
    clips, docs = load_entry(tmp_path, manifest["entries"][0])
    corrupt(clips, "accidental")
    assert docs[0].bindings and path.read_bytes() == original
    item = manifest["entries"][0]
    manifest["entries"].append({**item, "id": "copy", "split": (
        "evaluation" if item["split"] == "calibration" else "calibration")})
    with pytest.raises(ValueError, match="leakage"):
        validate_manifest(manifest)


@pytest.mark.parametrize("format", ("json", "csv", "columns"))
def test_maestro_metadata(tmp_path, references, format):
    write_midi(references[0], tmp_path / "piece.mid")
    row = {"midi_filename": "piece.mid", "canonical_composer": "Reference",
           "canonical_title": "Test", "split": "test"}
    path = tmp_path / ("maestro.csv" if format == "csv" else "maestro.json")
    if format == "csv":
        path.write_text(",".join(row) + "\n" + ",".join(row.values()), encoding="utf-8")
    else:
        data = [row] if format == "json" else {k: {"0": v} for k, v in row.items()}
        path.write_text(json.dumps(data), encoding="utf-8")
    result = build_manifest(tmp_path, dataset="maestro", metadata=path)
    assert result["entries"][0]["split"] == "evaluation"
    assert result["entries"][0]["group"] == "reference / test"


def test_pop_metadata_and_pair_extraction(tmp_path):
    from glue.models import TrackInfo

    source = clip([(60, 0, 1, 0), (48, 0, 1, 1)])
    source = replace(source, tracks=(TrackInfo(0, "MELODY", 1920), TrackInfo(1, "PIANO", 1920)))
    write_midi(source, tmp_path / "001.mid")
    (tmp_path / "chord_midi.txt").write_text("0.0 2.0 C:maj\n", encoding="utf-8")
    manifest = build_manifest(tmp_path, dataset="pop909", pop_pairs=True)
    entry = manifest["entries"][0]
    assert entry["track_roles"] == {"MELODY": 0, "PIANO": 1}
    assert len(entry["annotations"]) == 1
    clips, _ = load_entry(tmp_path, entry)
    assert [len(c.notes) for c in clips] == [1, 1]
    assert clips[0].notes[0].pitch == 60 and clips[1].notes[0].pitch == 48


def test_wrong_chord_tone_avoids_occupied_unisons():
    reference = (clip([(p, 0, 1, 0) for p in (48, 52, 55)]),)
    damaged = corrupt(reference, "wrong_chord_tone", seed=2)
    assert not damaged.skipped
    assert damaged.changes[0].after.pitch % 12 in {0, 4, 7}
    assert len({n.pitch for n in damaged.clips[0].notes}) == 3


def test_harmony_overlap_requires_sonority_change():
    reference = (clip([(p, i, 0.5, 0) for i, p in enumerate((60, 62, 64, 65))]),)
    assert corrupt(reference, "harmony_overlap").skipped


def test_severity_and_motif_damage(references):
    slight = corrupt(references, "late", seed=7, severity=1)
    strong = corrupt(references, "late", seed=7, severity=2)
    a, b = slight.changes[0], strong.changes[0]
    assert (a.slot, a.note_id) == (b.slot, b.note_id)
    assert b.after.onset_ticks - b.before.onset_ticks == 2 * (
        a.after.onset_ticks - a.before.onset_ticks)
    altered = corrupt(references, "motif", seed=3)
    assert measure(references, altered, altered.clips)["motif_similarity_after"] < 1
