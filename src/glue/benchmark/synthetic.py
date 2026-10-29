"""Small self-authored reference corpus for framework validation, not producer ratings."""

from __future__ import annotations

from pathlib import Path

from glue.io import write_midi
from glue.models import MidiClip, MidiNote, TempoChange, TimeSignatureChange, TrackInfo

from .manifest import source


def _clip(name: str, specs: list[tuple[int, float, float, int]]) -> MidiClip:
    notes = tuple(MidiNote(i, p, round(t * 480), round(d * 480), 84, voice, voice)
                  for i, (p, t, d, voice) in enumerate(specs))
    return MidiClip(480, notes, (TempoChange(0, 500000),), (TimeSignatureChange(0, 4, 4),),
                    tuple(TrackInfo(v, "MELODY" if v == 0 else "PIANO", 4800)
                          for v in sorted({n.track for n in notes})), 4800, name)


def generate_reference_manifest(output: Path) -> dict:
    """Create only new synthetic files. Never overwrite material supplied by a user."""
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Synthetic reference output must be empty")
    output.mkdir(parents=True, exist_ok=True)
    melody = _clip("repeated-major-motif", [(p, i, 0.75, 0)
                                          for i, p in enumerate((72, 74, 76, 79) * 2)])
    expressive = _clip("intentional-chromatic-syncopation",
                       [(p, i + 0.375, 0.25, 0)
                        for i, p in enumerate((60, 61, 62, 64, 67, 64, 62, 60))])
    chords = _clip("chord-reference", [(p, i * 2, 1.5, 1)
                                      for i, chord in enumerate(((48, 52, 55), (53, 57, 60),
                                                                  (43, 47, 50), (48, 52, 55)))
                                      for p in chord])
    call = _clip("call", [(p, i * 2, 0.5, 0) for i, p in enumerate((60, 64, 67, 60))])
    response = _clip("response", [(p, i * 2 + 0.5, 0.5, 0)
                                  for i, p in enumerate((64, 67, 71, 64))])
    paths = {c.name: write_midi(c, output / (c.name + ".mid"))
             for c in (melody, expressive, chords, call, response)}
    entries = []
    for ident, names, split in (
        ("motif", (melody.name,), "calibration"),
        ("chords", (chords.name,), "calibration"),
        ("call-response", (call.name, response.name), "calibration"),
        ("intentional", (expressive.name,), "evaluation"),
    ):
        entries.append({"id": ident, "group": ident, "split": split,
                        "sources": [source(output, paths[name]) for name in names],
                        "metadata": {"provenance": "self-authored synthetic", "license": "CC0-1.0"}})
    return {"schema": 1, "dataset": "synthetic-framework-validation", "seed": 0,
            "root": str(output.resolve()), "entries": entries,
            "provenance": "Self-authored CC0 synthetic references; NOT POP909/MAESTRO results, "
                          "not human-rated musical ground truth. Evaluation piece held out."}
