from dataclasses import replace

import pytest

from glue.analysis.voices import octave_supported, voice_paths
from glue.benchmark.manifest import load_entry
from glue.benchmark.synthetic import generate_reference_manifest
from glue.fixes.context_candidates import context_options
from glue.fixes.musical import generate_musical_repairs
from glue.fixes.musical_config import EditPermissions, musical_search_for
from scripts.generate_v05_fixtures import clip, musical_fixtures


def test_chords_are_separate_continuous_voices():
    source = clip([(p, beat, 0.8, 0) for beat in range(4) for p in (48 + beat, 60 + beat, 67 + beat)])
    voices = voice_paths(source)
    assert len(voices) == 3
    assert [[n.pitch for n in line] for line in voices] == [list(range(p, p + 4)) for p in (48, 60, 67)]
    assert sorted(n.id for line in voices for n in line) == sorted(n.id for n in source.notes)
    assert voices == voice_paths(source)


def test_octave_requires_isolated_excursion_not_chord_revoicing(tmp_path):
    from pathlib import Path

    manifest = generate_reference_manifest(tmp_path / "refs")
    chord, _ = load_entry(Path(manifest["root"]), manifest["entries"][1])
    for preset in ("minimal", "balanced", "creative"):
        result = generate_musical_repairs(*chord, preservation=(0,), preset=preset)
        assert not result.candidates
    source = clip([(60, 0, 1, 0), (74, 1, 1, 0), (64, 2, 1, 0)])
    assert octave_supported(source, source.notes[1], 62)
    assert not octave_supported(source, source.notes[0], 72)  # No two-sided evidence.
    motif = clip([(p, i, 0.75, 0) for i, p in enumerate((72, 74, 76, 79, 84, 74, 76, 79))])
    assert octave_supported(motif, motif.notes[4], 72)


def test_context_recovers_supported_onset_and_duration_without_quantizing_clean_syncopation():
    source = clip([(p, i + 0.375, 0.75, 0) for i, p in enumerate((60, 62, 64, 65, 67, 69, 71))])
    changed = source.with_notes(replace(n, onset_ticks=n.onset_ticks + 60, duration_ticks=600)
                                if n.id == 3 else n for n in source.notes)
    permissions = EditPermissions(True, True, True)
    options = context_options(changed, permissions, musical_search_for("creative"))
    assert any(o.note_id == 3 and o.field == "onset_ticks" and o.value == 1620 for o in options)
    assert any(o.note_id == 3 and o.field == "duration_ticks" and o.value == 360 for o in options)
    assert not any(o.field != "pitch" for o in
                   context_options(source, permissions, musical_search_for("creative")))
    assert not any(o.field != "pitch" for o in
                   context_options(changed, permissions, musical_search_for("minimal")))


@pytest.mark.parametrize("fields", [("pitch", "pitch"), ("pitch", "onset_ticks"),
                                    ("pitch", "duration_ticks")])
def test_neutral_multi_field_and_two_voice_barriers(monkeypatch, fields):
    import glue.fixes.musical as engine

    source = clip([(60, 0, 0.5, 0), (64, 0, 0.5, 1)])
    targets = (61, {"pitch": 65, "onset_ticks": 60, "duration_ticks": 180}[fields[1]])
    options = tuple(engine._Option(0, i, f, v, "bounded test proposal")
                    for i, (f, v) in enumerate(zip(fields, targets, strict=True)))
    monkeypatch.setattr(engine, "_options", lambda *args: options)

    def objective(clips, weights):
        notes = {n.id: n for n in clips[0].notes}
        hits = sum(getattr(notes[i], f) == v for i, (f, v) in enumerate(zip(fields, targets, strict=True)))
        return engine.MusicalScore((("test barrier", hits),), 0 if hits == 2 else 10 + hits)

    monkeypatch.setattr(engine, "score_passage", objective)
    result = engine.generate_musical_repairs(source, preservation=(0,), preset="creative",
                                            permissions=(EditPermissions(True, True, True),))
    assert len(result.candidates[0].edits) == 2
    assert result.candidates[0].score.cost == 0


def test_coordinated_swap_is_evaluated_even_when_both_atomic_states_are_invalid(monkeypatch):
    import glue.fixes.musical as engine

    source = clip([(60, 0, 1, 0), (62, 0, 1, 0)])
    monkeypatch.setattr(engine, "_options", lambda *args: (
        engine._Option(0, 0, "pitch", 62, "swap"), engine._Option(0, 1, "pitch", 60, "swap")))
    monkeypatch.setattr(engine, "score_passage", lambda clips, weights:
                        engine.MusicalScore((("swap test", 0),),
                                           0 if clips[0].notes[0].pitch == 62 else 10))
    result = engine.generate_musical_repairs(source, preservation=(0,), preset="creative")
    assert result.candidates and len(result.candidates[0].edits) == 2


def test_safeguards_keep_known_intentional_material_and_locks():
    f = musical_fixtures()
    for name in ("chromatic_passing", "suspension", "secondary_dominant", "intentional_syncopation"):
        assert not generate_musical_repairs(f[name], preservation=(0,), preset="creative").candidates
    assert not generate_musical_repairs(f["pitch_only"], preservation=(100,), preset="creative").candidates
