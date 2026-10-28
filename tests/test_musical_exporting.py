from pathlib import Path

import mido
import pytest

from glue.fixes.musical import generate_musical_repairs
from glue.fixes.musical_config import EditPermissions
from glue.io import load_midi
from glue.io.edited import _unrelated_events
from glue.musical_exporting import export_musical_bundle
from scripts.generate_v05_fixtures import generate


def test_combined_preserves_source_events_and_bundle_rolls_back_publication(tmp_path, monkeypatch):
    paths = generate(tmp_path / "fixtures")
    midi = mido.MidiFile(paths["rhythmic_collision_b"])
    midi.tracks[0].insert(0, mido.Message("program_change", program=24))
    midi.tracks[0].insert(0, mido.Message("control_change", control=11, value=99))
    midi.save(paths["rhythmic_collision_b"])
    docs = tuple(load_midi(paths[n]) for n in ("rhythmic_collision_a", "rhythmic_collision_b"))
    source_bytes = tuple(d.source_path.read_bytes() for d in docs)
    result = generate_musical_repairs(
        *(d.clip for d in docs),
        preservation=(100, 0),
        preset="creative",
        permissions=(EditPermissions(), EditPermissions(False, True, False)),
    )
    candidate = result.candidates[0]
    bundle = export_musical_bundle(result, candidate, docs, tmp_path / "bundle")
    combined = load_midi(bundle.combined_preview)
    assert _unrelated_events(combined._template) == (
        _unrelated_events(docs[0]._template) + _unrelated_events(docs[1]._template)
    )
    previous = {p: f"previous artifact {i}".encode() for i, p in enumerate(bundle.all_paths)}
    for path, data in previous.items():
        path.write_bytes(data)
    real_replace = Path.replace

    def fail_third(source, target):
        if Path(target) == bundle.combined_preview:
            raise OSError("simulated publication failure")
        return real_replace(source, target)

    monkeypatch.setattr(Path, "replace", fail_third)
    with pytest.raises(OSError, match="simulated"):
        export_musical_bundle(result, candidate, docs, tmp_path / "bundle", overwrite=True)
    assert all(p.read_bytes() == data for p, data in previous.items())
    assert tuple(d.source_path.read_bytes() for d in docs) == source_bytes


def test_incompatible_tempo_bundle_fails_without_publishing(tmp_path):
    paths = generate(tmp_path / "fixtures")
    midi = mido.MidiFile(paths["sustain_conflict_b"])
    for track in midi.tracks:
        for event in track:
            if event.type == "set_tempo":
                event.tempo = 750_000
    midi.save(paths["sustain_conflict_b"])
    docs = tuple(load_midi(paths[n]) for n in ("sustain_conflict_a", "sustain_conflict_b"))
    result = generate_musical_repairs(
        *(d.clip for d in docs),
        preservation=(100, 0),
        preset="creative",
        permissions=(EditPermissions(), EditPermissions(False, False, True)),
    )
    with pytest.raises(ValueError, match="tempo"):
        export_musical_bundle(result, result.candidates[0], docs, tmp_path / "failed")
    assert not tuple(tmp_path.glob("failed-*"))
