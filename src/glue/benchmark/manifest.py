"""Read-only local dataset adapters and content-addressed, piece-grouped splits."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import replace
from pathlib import Path

from glue.io import MidiDocument, load_midi
from glue.models import MidiClip, TempoChange, TimeSignatureChange

from . import SCHEMA_VERSION


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def stable_seed(seed: int, *parts: object) -> int:
    data = json.dumps([seed, *parts], sort_keys=True).encode()
    return int.from_bytes(hashlib.sha256(data).digest()[:8], "big")


def local_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(root.resolve()):
        raise ValueError(f"Dataset path must stay inside root: {relative}")
    return path


def source(root: Path, path: Path, tracks: list[int] | None = None) -> dict:
    result = {"path": path.relative_to(root).as_posix(), "sha256": digest(path)}
    if tracks is not None:
        result["tracks"] = tracks
    return result


def _maestro_rows(path: Path) -> list[dict]:
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as stream:
            return list(csv.DictReader(stream))
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    # Support column-oriented JSON, as well as record arrays.
    keys = sorted(data["midi_filename"], key=lambda value: int(value))
    return [{column: values[key] for column, values in data.items()} for key in keys]


def build_manifest(
    root: Path, *, dataset: str = "reference", seed: int = 0,
    metadata: Path | None = None, pop_pairs: bool = False,
    quarantine_conflicts: bool = False,
) -> dict:
    """Inventory user-owned material; no downloading or musical-quality claims.

    Reference directories group all files in each subdirectory as one piece;
    flat files use their stem. Review groups before sealing a final evaluation.
    POP track roles and raw annotations are retained, not guessed as truth.
    """
    root = root.resolve()
    if dataset not in {"reference", "pop909", "maestro"}:
        raise ValueError("Unknown dataset adapter")
    entries = []
    if dataset == "maestro":
        if metadata is None:
            raise ValueError("MAESTRO requires a local metadata CSV or JSON")
        rows = _maestro_rows(metadata)
    else:
        rows = [{"midi_filename": p.relative_to(root).as_posix()} for p in sorted(root.rglob("*"))
                if p.suffix.lower() in {".mid", ".midi"}]
    discovered = len(rows)
    if dataset == "pop909":
        # The extracted release also contains song/versions/*-vN.mid. Inventory
        # canonical song/song.mid files only; variants are not independent works.
        canonical = [r for r in rows if Path(r["midi_filename"]).stem.isdigit()
                     and Path(r["midi_filename"]).parent.name == Path(r["midi_filename"]).stem]
        if canonical:
            rows = canonical
    for row in rows:
        path = local_path(root, row["midi_filename"])
        relative = path.relative_to(root)
        group = str(relative.parent) if len(relative.parts) > 1 else path.stem
        if dataset == "maestro":
            group = " / ".join(str(row.get(k, "")).strip().casefold()
                               for k in ("canonical_composer", "canonical_title"))
            if not group.replace(" / ", ""):
                raise ValueError("MAESTRO rows need canonical composer/title for piece grouping")
        split = row.get("split")
        if split not in {None, "train", "validation", "test", "calibration", "evaluation"}:
            raise ValueError(f"Unknown split: {split}")
        split = ("evaluation" if split in {"test", "evaluation"} else "calibration") if split else (
            "evaluation" if stable_seed(seed, group) % 5 == 0 else "calibration"
        )
        sources = [source(root, path)]
        annotations = []
        roles = {}
        if dataset == "pop909":
            if path.stem.isdigit():
                group = path.stem
            document = load_midi(path)
            roles = {t.name: t.index for t in document.clip.tracks}
            for name in ("chord_midi.txt", "beat_midi.txt", "key_audio.txt", "chord_audio.txt"):
                sidecar = path.parent / name
                if sidecar.exists():
                    annotations.append(source(root, sidecar))
            if pop_pairs:
                melody = [t.index for t in document.clip.tracks if t.name.upper() == "MELODY"]
                backing = [t.index for t in document.clip.tracks
                           if t.name.upper() in {"BRIDGE", "PIANO", "ACCOMPANIMENT"}]
                if not melody or not backing:
                    raise ValueError(f"POP pair needs MELODY and backing track labels: {path}")
                sources = [source(root, path, melody), source(root, path, backing)]
        entries.append({"id": relative.as_posix(), "group": group, "split": split,
                        "sources": sources, "metadata": dict(row), "track_roles": roles,
                        "annotations": annotations})
    if not entries:
        raise ValueError("No MIDI material found")
    result = {"schema": SCHEMA_VERSION, "dataset": dataset, "seed": seed,
              "discovered_files": discovered, "excluded_variant_files": discovered - len(rows),
              "root": str(root), "entries": entries,
              "provenance": "User-supplied references; quality and licensing require human review."}
    if quarantine_conflicts:
        result = quarantine_split_conflicts(result)
    validate_manifest(result)
    return result


def quarantine_split_conflicts(manifest: dict) -> dict:
    """Exclude entire connected piece/content groups; never move a held-out file.

    Some official metadata contains a composition in more than one split. Keep
    strict rejection as the default. This explicit policy records all excluded
    entries and preserves the original metadata for audit without admitting it
    to calibration or evaluation.
    """
    identities = [{"group:" + e["group"], *("content:" + s["sha256"] for s in e["sources"])}
                  for e in manifest["entries"]]
    assignments: dict[str, set[str]] = {}
    for entry, keys in zip(manifest["entries"], identities, strict=True):
        for key in keys:
            assignments.setdefault(key, set()).add(entry["split"])
    bad = {key for key, splits in assignments.items() if len(splits) > 1}
    while True:
        expanded = bad | {key for keys in identities if keys & bad for key in keys}
        if expanded == bad:
            break
        bad = expanded
    kept, excluded = [], []
    for entry, keys in zip(manifest["entries"], identities, strict=True):
        (excluded if keys & bad else kept).append(entry)
    return {**manifest, "entries": kept, "quarantined_entries": excluded,
            "split_conflict_policy": "exclude entire connected piece/content groups"}


def validate_manifest(manifest: dict) -> None:
    if manifest["schema"] != SCHEMA_VERSION:
        raise ValueError("Unsupported manifest schema")
    seen: set[str] = set()
    assignments: dict[str, str] = {}
    for entry in manifest["entries"]:
        if entry["id"] in seen:
            raise ValueError("Duplicate entry id")
        seen.add(entry["id"])
        if entry["split"] not in {"calibration", "evaluation"}:
            raise ValueError("Expected calibration or evaluation split")
        if not 1 <= len(entry["sources"]) <= 2:
            raise ValueError("Each entry requires one clip or a pair")
        identities = ["group:" + entry["group"]]
        identities += ["content:" + s["sha256"] for s in entry["sources"]]
        for identity in identities:
            previous = assignments.setdefault(identity, entry["split"])
            if previous != entry["split"]:
                raise ValueError(f"Split leakage: {identity}")


def read_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    validate_manifest(manifest)
    manifest["root"] = str((path.parent / manifest["root"]).resolve())
    return manifest


def window_manifest(manifest: dict, beats: int, per_piece: int = 4) -> dict:
    """Select deterministic, evenly spaced windows BEFORE inspecting repair outcomes.

    Splits remain piece-grouped. Notes starting before a window are excluded;
    notes starting inside retain their complete duration (including tails).
    This boundary/context limitation is recorded explicitly in the manifest.
    """
    if beats < 4 or beats % 4 or per_piece < 1:
        raise ValueError("Window size must be a positive multiple of 4; count must be positive")
    entries = []
    for entry in manifest["entries"]:
        clips, _ = load_entry(Path(manifest["root"]), entry)
        length = max(c.length_ticks / c.ticks_per_beat for c in clips)
        count = max(1, int((length - 1e-9) // beats) + 1)
        indices = sorted({round(i * (count - 1) / max(1, min(count, per_piece) - 1))
                          for i in range(min(count, per_piece))})
        for i in indices:
            entries.append({**entry, "id": f"{entry['id']}@{i * beats}:{(i + 1) * beats}",
                            "window_beats": [i * beats, (i + 1) * beats]})
    result = {**manifest, "entries": entries,
              "window_policy": {"beats": beats, "max_per_piece": per_piece,
                                "selection": "evenly spaced, outcome-independent",
                                "boundary": "onsets inside window, complete tails, no carried notes"}}
    validate_manifest(result)
    return result


def _window(clip: MidiClip, region: list[float]) -> MidiClip:
    start, end = (round(beat * clip.ticks_per_beat) for beat in region)
    if start < 0 or end <= start:
        raise ValueError("Invalid window region")
    notes = tuple(replace(n, onset_ticks=n.onset_ticks - start) for n in clip.notes
                  if start <= n.onset_ticks < end)
    length = max(end - start, max((n.end_ticks for n in notes), default=0))
    tempos = [t for t in clip.tempo_changes if t.tick <= start]
    signatures = [t for t in clip.time_signature_changes if t.tick <= start]
    return replace(
        clip, notes=notes, length_ticks=length,
        tracks=tuple(replace(t, length_ticks=length) for t in clip.tracks),
        tempo_changes=(replace(tempos[-1], tick=0) if tempos else TempoChange(0, 500000),)
        + tuple(replace(t, tick=t.tick - start) for t in clip.tempo_changes if start < t.tick < end),
        time_signature_changes=(replace(signatures[-1], tick=0) if signatures
                                else TimeSignatureChange(0, 4, 4),)
        + tuple(replace(t, tick=t.tick - start) for t in clip.time_signature_changes
                if start < t.tick < end),
    )


def load_entry(root: Path, entry: dict) -> tuple[tuple[MidiClip, ...], tuple[MidiDocument, ...]]:
    documents, clips = [], []
    for item in entry["sources"]:
        path = local_path(root, item["path"])
        if digest(path) != item["sha256"]:
            raise ValueError(f"Reference hash changed: {item['path']}")
        document = load_midi(path)
        if document.warnings:
            raise ValueError(f"Ground truth has parser warnings: {document.warnings}")
        clip = document.clip
        if "tracks" in item:
            clip = clip.with_notes(n for n in clip.notes if n.track in item["tracks"])
        if "window_beats" in entry:
            clip = _window(clip, entry["window_beats"])
        if not clip.notes or any(n.duration_ticks <= 0 for n in clip.notes):
            raise ValueError("Ground truth must have positive-duration notes")
        documents.append(document)
        clips.append(clip)
    for item in entry.get("annotations", []):
        if digest(local_path(root, item["path"])) != item["sha256"]:
            raise ValueError(f"Annotation hash changed: {item['path']}")
    return tuple(clips), tuple(documents)
