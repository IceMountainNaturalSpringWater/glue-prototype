"""Validated V0.5 MIDI artifacts and optional producer-calibration reports."""

from __future__ import annotations

import json
import shutil
from collections import Counter
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

import mido

from glue import __version__
from glue.exporting import RepairExportPaths
from glue.fixes.musical import MusicalCandidate, MusicalRepair
from glue.io import MidiDocument, MidiWriteError, load_midi
from glue.io.edited import note_semantics, write_edited_midi
from glue.io.midi import _paths_refer_to_same_file
from glue.io.preview import _canonical_signature_map, _canonical_tempo_map, _shared_ticks_per_beat
from glue.models import MidiClip


def _preflight(path: Path, documents: tuple[MidiDocument, ...], overwrite: bool) -> None:
    if any(_paths_refer_to_same_file(path, doc.source_path) for doc in documents):
        raise MidiWriteError("Refusing to overwrite a loaded source MIDI file")
    if path.exists() and (not overwrite or not path.is_file()):
        raise MidiWriteError("Export exists; choose a new filename or explicitly confirm overwrite")
    if not path.parent.is_dir():
        raise MidiWriteError("Export directory does not exist")


def _validate(
    repair: MusicalRepair, candidate: MusicalCandidate, documents: tuple[MidiDocument, ...]
) -> None:
    if tuple(d.clip for d in documents) != repair.originals:
        raise MidiWriteError("Candidate does not match the loaded documents")
    if candidate not in repair.candidates or not candidate.edits:
        raise MidiWriteError("No retained improving candidate is available")


def calibration_report(repair: MusicalRepair, candidate: MusicalCandidate) -> dict:
    return {
        "version": __version__,
        "workflow": "polish" if len(repair.originals) == 1 else "combine",
        "preset": repair.config.preset.value,
        "preservation": repair.preservation,
        "permissions": [asdict(p) for p in repair.permissions],
        "before": dict(repair.before.components),
        "after": dict(candidate.score.components),
        "before_estimate": repair.before.estimate,
        "after_estimate": candidate.score.estimate,
        "motif_contour_groove_cost": candidate.retention_cost,
        "edit_cost": candidate.edit_cost,
        "objective": candidate.objective,
        "evaluations": repair.evaluations,
        "stop_reason": repair.stop_reason,
        "edits": [asdict(e) for e in candidate.edits],
        "rating": None,
        "calibration_schema": 1,
        "weights": asdict(repair.config.weights),
        "clips": [
            {"name": c.name, "notes": len(c.notes), "ppq": c.ticks_per_beat}
            for c in repair.originals
        ],
    }


def export_musical_candidate(
    repair: MusicalRepair,
    candidate: MusicalCandidate,
    documents: tuple[MidiDocument, ...],
    destination: str | Path,
    *,
    slot: int = 0,
    report: bool = False,
    overwrite: bool = False,
) -> Path:
    _validate(repair, candidate, documents)
    if not 0 <= slot < len(documents):
        raise ValueError("Invalid export clip")
    path = Path(destination)
    _preflight(path, documents, overwrite)
    with NamedTemporaryFile(
        dir=path.parent, prefix=".glue-", suffix=path.suffix, delete=False
    ) as f:
        staged = Path(f.name)
    try:
        if report:
            payload = calibration_report(repair, candidate)
            staged.write_text(
                json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
                encoding="utf-8",
            )
            json.loads(staged.read_text(encoding="utf-8"))
        else:
            allow = repair.permissions[slot]
            config = repair.config
            write_edited_midi(
                documents[slot],
                candidate.clips[slot],
                staged,
                pitch=allow.pitch,
                timing=allow.timing,
                duration=allow.duration,
                onset_limit=config.onset_beats,
                duration_limit=config.duration_beats,
                duration_fraction=config.duration_fraction,
            )
        _preflight(path, documents, overwrite)
        staged.replace(path)
    finally:
        staged.unlink(missing_ok=True)
    return path


def export_musical_combined(
    repair: MusicalRepair,
    candidate: MusicalCandidate,
    documents: tuple[MidiDocument, ...],
    destination: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Separate original tracks, exact shared PPQ, and all source MIDI events.

    No flattening or channel remapping. Conflicting tempo/meter maps are refused;
    downstream instruments may still share state for equal MIDI channel numbers.
    """
    _validate(repair, candidate, documents)
    if len(documents) != 2:
        raise ValueError("A combined preview requires two clips")
    a, b = candidate.clips
    if _canonical_tempo_map(a) != _canonical_tempo_map(b):
        raise MidiWriteError("Combined preview requires compatible tempo maps")
    if _canonical_signature_map(a) != _canonical_signature_map(b):
        raise MidiWriteError("Combined preview requires compatible meter maps")
    ppq = _shared_ticks_per_beat(a, b)
    path = Path(destination)
    _preflight(path, documents, overwrite)
    with TemporaryDirectory(dir=path.parent, prefix=".glue-combined-") as temp:
        root = Path(temp)
        combined = mido.MidiFile(type=1, ticks_per_beat=ppq)
        expected: Counter = Counter()
        for slot, clip in enumerate(candidate.clips):
            exported = export_musical_candidate(
                repair, candidate, documents, root / f"{slot}.mid", slot=slot
            )
            midi = mido.MidiFile(exported)
            scale = ppq // clip.ticks_per_beat
            offset = len(combined.tracks)
            expected.update(
                note_semantics(
                    MidiClip(
                        ppq,
                        tuple(
                            replace(
                                n,
                                track=n.track + offset,
                                onset_ticks=n.onset_ticks * scale,
                                duration_ticks=n.duration_ticks * scale,
                            )
                            for n in clip.notes
                        ),
                    )
                )
            )
            for track in midi.tracks:
                combined.tracks.append(
                    mido.MidiTrack(msg.copy(time=msg.time * scale) for msg in track)
                )
        staged = root / "combined.mid"
        combined.save(staged)
        if note_semantics(load_midi(staged).clip) != expected:
            raise MidiWriteError("Combined preview failed note round-trip validation")
        _preflight(path, documents, overwrite)
        staged.replace(path)
    return path


def export_musical_bundle(
    repair: MusicalRepair,
    candidate: MusicalCandidate,
    documents: tuple[MidiDocument, ...],
    base: str | Path,
    *,
    overwrite: bool = False,
) -> RepairExportPaths:
    """Stage and validate all four artifacts before publishing, with rollback."""
    paths = RepairExportPaths.from_base(base)
    destinations = (paths.revised_a, paths.revised_b, paths.combined_preview, paths.change_report)
    for path in destinations:
        _preflight(path, documents, overwrite)
    with TemporaryDirectory(dir=Path(base).parent, prefix=".glue-bundle-") as temp:
        root = Path(temp)
        staged = (root / "a.mid", root / "b.mid", root / "combined.mid", root / "report.json")
        export_musical_candidate(repair, candidate, documents, staged[0], slot=0)
        export_musical_candidate(repair, candidate, documents, staged[1], slot=1)
        export_musical_combined(repair, candidate, documents, staged[2])
        export_musical_candidate(repair, candidate, documents, staged[3], report=True)
        backups = {}
        for index, path in enumerate(destinations):
            _preflight(path, documents, overwrite)
            if path.exists():
                backup = root / f"backup-{index}"
                shutil.copy2(path, backup)
                backups[path] = backup
        promoted = []
        try:
            for source, target in zip(staged, destinations, strict=True):
                source.replace(target)
                promoted.append(target)
        except OSError:
            for target in reversed(promoted):
                if target in backups:
                    backups[target].replace(target)
                else:
                    target.unlink()
            raise
    return paths
