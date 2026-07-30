"""Application-level export of all artifacts for a repaired MIDI pair."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from glue import __version__
from glue.fixes import NoteEdit, PairRepairResult
from glue.io import MidiDocument, MidiWriteError, load_midi, save_midi, write_midi
from glue.io.midi import _paths_refer_to_same_file
from glue.io.preview import build_combined_preview
from glue.models import MidiClip, MidiNote

PathLike = str | Path
CHANGE_REPORT_VERSION = __version__


class RepairExportError(MidiWriteError):
    """Raised before a repair artifact export can alter a destination."""


@dataclass(frozen=True, slots=True)
class RepairExportPaths:
    """The four explicit destinations for one repair candidate."""

    revised_a: Path
    revised_b: Path
    combined_preview: Path
    change_report: Path

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, Path(getattr(self, name)))

    @classmethod
    def from_base(cls, base: PathLike) -> RepairExportPaths:
        """Derive predictable artifact names from a user-selected base path."""

        path = Path(base)
        if path.suffix:
            path = path.with_suffix("")
        return cls(
            revised_a=path.with_name(f"{path.name}-A.mid"),
            revised_b=path.with_name(f"{path.name}-B.mid"),
            combined_preview=path.with_name(f"{path.name}-combined.mid"),
            change_report=path.with_name(f"{path.name}-changes.json"),
        )

    @property
    def all_paths(self) -> tuple[Path, Path, Path, Path]:
        """Return destinations in their stable write order."""

        return (
            self.revised_a,
            self.revised_b,
            self.combined_preview,
            self.change_report,
        )


@dataclass(frozen=True, slots=True)
class RepairExportResult:
    """Paths successfully produced by :func:`export_repair_bundle`."""

    paths: RepairExportPaths

    @property
    def revised_a(self) -> Path:
        return self.paths.revised_a

    @property
    def revised_b(self) -> Path:
        return self.paths.revised_b

    @property
    def combined_preview(self) -> Path:
        return self.paths.combined_preview

    @property
    def change_report(self) -> Path:
        return self.paths.change_report


def _validate_source_documents(
    result: PairRepairResult,
    document_a: MidiDocument,
    document_b: MidiDocument,
) -> None:
    if result.original_clip_a != document_a.clip:
        raise RepairExportError(
            "Repair candidate Clip A does not match the loaded source document"
        )
    if result.original_clip_b != document_b.clip:
        raise RepairExportError(
            "Repair candidate Clip B does not match the loaded source document"
        )


def _edit_records(
    label: str,
    original: MidiClip,
    edits: tuple[NoteEdit, ...],
) -> list[dict[str, object]]:
    original_by_id = {note.id: note for note in original.notes}
    ordered = sorted(
        edits,
        key=lambda edit: (
            original_by_id[edit.note_id].onset_ticks,
            original_by_id[edit.note_id].track,
            original_by_id[edit.note_id].channel,
            edit.note_id,
        ),
    )
    records: list[dict[str, object]] = []
    for edit in ordered:
        note = original_by_id[edit.note_id]
        records.append(
            {
                "clip": label,
                "note_id": edit.note_id,
                "track": note.track,
                "channel": note.channel,
                "original_pitch": edit.original_pitch,
                "revised_pitch": edit.repaired_pitch,
                "onset_ticks": note.onset_ticks,
                "duration_ticks": note.duration_ticks,
            }
        )
    return records


def build_change_report(
    result: PairRepairResult,
    document_a: MidiDocument,
    document_b: MidiDocument,
) -> dict[str, object]:
    """Return a JSON-compatible, traceable report for a pair repair."""

    _validate_source_documents(result, document_a, document_b)
    records_a = _edit_records("A", result.original_clip_a, result.edits_a)
    records_b = _edit_records("B", result.original_clip_b, result.edits_b)
    return {
        "version": CHANGE_REPORT_VERSION,
        "strategy": result.strategy.value,
        "preset": result.preset.value,
        "before_score": result.original_score,
        "after_score": result.repaired_score,
        "score_improvement": result.score_improvement,
        "clip_a": {
            "source": document_a.source_path.name,
            "preservation": result.preservation_a,
            "retention": result.retention_a,
            "changed_note_count": result.changed_note_count_a,
            "changed_notes": records_a,
        },
        "clip_b": {
            "source": document_b.source_path.name,
            "preservation": result.preservation_b,
            "retention": result.retention_b,
            "changed_note_count": result.changed_note_count_b,
            "changed_notes": records_b,
        },
    }


def serialize_change_report(report: dict[str, object]) -> bytes:
    """Serialize a report deterministically and reject non-standard numbers."""

    text = json.dumps(
        report,
        allow_nan=False,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    return f"{text}\n".encode()


def _preflight_destinations(
    destinations: tuple[Path, ...],
    sources: tuple[Path, ...],
    *,
    overwrite: bool,
) -> None:
    for index, destination in enumerate(destinations):
        if any(
            _paths_refer_to_same_file(destination, source) for source in sources
        ):
            raise RepairExportError(
                "Refusing to overwrite loaded MIDI A or MIDI B; choose different "
                "export paths"
            )
        if any(
            _paths_refer_to_same_file(destination, prior)
            for prior in destinations[:index]
        ):
            raise RepairExportError("Every repair artifact requires a distinct path")
        if destination.exists():
            if destination.is_dir():
                raise RepairExportError(
                    f"Repair export destination is a directory: '{destination}'"
                )
            if not overwrite:
                raise RepairExportError(
                    f"Refusing to overwrite existing export '{destination}'"
                )
        if not destination.parent.is_dir():
            raise RepairExportError(
                f"Repair export directory does not exist: '{destination.parent}'"
            )


def _temporary_path(destination: Path) -> Path:
    with tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=f".{destination.name}.",
        suffix=destination.suffix,
        dir=destination.parent,
        delete=False,
    ) as handle:
        return Path(handle.name)


def _note_signature(note: MidiNote) -> tuple[int, ...]:
    return (
        note.id,
        note.pitch,
        note.onset_ticks,
        note.duration_ticks,
        note.velocity,
        note.release_velocity,
        note.track,
        note.channel,
    )


def _validate_revised_round_trip(path: Path, expected: MidiClip, label: str) -> None:
    reloaded = load_midi(path).clip
    actual_notes = tuple(_note_signature(note) for note in reloaded.notes)
    expected_notes = tuple(_note_signature(note) for note in expected.notes)
    if actual_notes != expected_notes:
        raise RepairExportError(
            f"Revised Clip {label} did not round-trip with the intended notes"
        )


def _preview_note_signature(note: MidiNote) -> tuple[int, ...]:
    """Return preview semantics without transient combined-file note ids."""

    return (
        note.pitch,
        note.onset_ticks,
        note.duration_ticks,
        note.velocity,
        note.release_velocity,
        note.track,
        note.channel,
    )


def _validate_preview_round_trip(path: Path, expected: MidiClip) -> None:
    reloaded = load_midi(path).clip
    if len(reloaded.tracks) != 2:
        raise RepairExportError("Combined preview did not round-trip as two tracks")
    if reloaded.ticks_per_beat != expected.ticks_per_beat:
        raise RepairExportError(
            "Combined preview did not round-trip with the intended timing resolution"
        )
    actual_notes = tuple(_preview_note_signature(note) for note in reloaded.notes)
    expected_notes = tuple(_preview_note_signature(note) for note in expected.notes)
    if actual_notes != expected_notes:
        raise RepairExportError(
            "Combined preview did not round-trip with the intended note timing semantics"
        )


def _write_staged_bundle(
    result: PairRepairResult,
    document_a: MidiDocument,
    document_b: MidiDocument,
    preview: MidiClip,
    report_bytes: bytes,
    staged: tuple[Path, Path, Path, Path],
) -> None:
    save_midi(document_a, staged[0], clip=result.repaired_clip_a)
    save_midi(document_b, staged[1], clip=result.repaired_clip_b)
    write_midi(preview, staged[2])
    staged[3].write_bytes(report_bytes)

    _validate_revised_round_trip(staged[0], result.repaired_clip_a, "A")
    _validate_revised_round_trip(staged[1], result.repaired_clip_b, "B")
    _validate_preview_round_trip(staged[2], preview)
    try:
        json.loads(staged[3].read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RepairExportError("Change report did not round-trip as JSON") from exc


def _promote_single(
    temporary: Path,
    destination: Path,
    sources: tuple[Path, Path],
    *,
    overwrite: bool,
) -> Path:
    if not overwrite:
        _preflight_destinations((destination,), sources, overwrite=False)
    temporary.replace(destination)
    return destination


def export_revised_clip(
    result: PairRepairResult,
    document_a: MidiDocument,
    document_b: MidiDocument,
    slot: str,
    destination: PathLike,
    *,
    overwrite: bool = False,
) -> Path:
    """Export one revised source-preserving clip after full path preflight."""

    _validate_source_documents(result, document_a, document_b)
    normalized = slot.strip().upper()
    if normalized == "A":
        document, clip = document_a, result.repaired_clip_a
    elif normalized == "B":
        document, clip = document_b, result.repaired_clip_b
    else:
        raise ValueError("slot must be 'A' or 'B'")
    output = Path(destination)
    sources = (document_a.source_path, document_b.source_path)
    _preflight_destinations((output,), sources, overwrite=overwrite)
    temporary = _temporary_path(output)
    try:
        save_midi(document, temporary, clip=clip)
        _validate_revised_round_trip(temporary, clip, normalized)
        return _promote_single(
            temporary,
            output,
            sources,
            overwrite=overwrite,
        )
    except RepairExportError:
        raise
    except (OSError, TypeError, ValueError) as exc:
        raise RepairExportError(f"Could not export revised Clip {normalized}: {exc}") from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def export_combined_repair_preview(
    result: PairRepairResult,
    document_a: MidiDocument,
    document_b: MidiDocument,
    destination: PathLike,
    *,
    overwrite: bool = False,
) -> Path:
    """Export the repaired pair as a validated separate-track MIDI preview."""

    _validate_source_documents(result, document_a, document_b)
    preview = build_combined_preview(
        result.repaired_clip_a,
        result.repaired_clip_b,
    )
    output = Path(destination)
    sources = (document_a.source_path, document_b.source_path)
    _preflight_destinations((output,), sources, overwrite=overwrite)
    temporary = _temporary_path(output)
    try:
        write_midi(preview, temporary)
        _validate_preview_round_trip(temporary, preview)
        return _promote_single(
            temporary,
            output,
            sources,
            overwrite=overwrite,
        )
    except RepairExportError:
        raise
    except (OSError, TypeError, ValueError) as exc:
        raise RepairExportError(f"Could not export combined preview: {exc}") from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def export_change_report(
    result: PairRepairResult,
    document_a: MidiDocument,
    document_b: MidiDocument,
    destination: PathLike,
    *,
    overwrite: bool = False,
) -> Path:
    """Export one deterministic machine-readable JSON change report."""

    report_bytes = serialize_change_report(
        build_change_report(result, document_a, document_b)
    )
    output = Path(destination)
    sources = (document_a.source_path, document_b.source_path)
    _preflight_destinations((output,), sources, overwrite=overwrite)
    temporary = _temporary_path(output)
    try:
        temporary.write_bytes(report_bytes)
        json.loads(temporary.read_text(encoding="utf-8"))
        return _promote_single(
            temporary,
            output,
            sources,
            overwrite=overwrite,
        )
    except (OSError, UnicodeError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RepairExportError(f"Could not export change report: {exc}") from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def export_repair_bundle(
    result: PairRepairResult,
    document_a: MidiDocument,
    document_b: MidiDocument,
    paths: RepairExportPaths,
    *,
    overwrite: bool = False,
) -> RepairExportResult:
    """Export revised A, revised B, a preview, and JSON as one staged bundle.

    All compatibility and path checks happen before any destination is
    changed. Each artifact is then built and validated under a temporary name;
    only a fully valid four-file set is promoted to the requested paths.
    """

    _validate_source_documents(result, document_a, document_b)
    preview = build_combined_preview(
        result.repaired_clip_a,
        result.repaired_clip_b,
    )
    report_bytes = serialize_change_report(
        build_change_report(result, document_a, document_b)
    )
    destinations = paths.all_paths
    sources = (document_a.source_path, document_b.source_path)
    _preflight_destinations(destinations, sources, overwrite=overwrite)

    staged: list[Path] = []
    try:
        staged.extend(_temporary_path(destination) for destination in destinations)
        staged_paths = (staged[0], staged[1], staged[2], staged[3])
        _write_staged_bundle(
            result,
            document_a,
            document_b,
            preview,
            report_bytes,
            staged_paths,
        )
        if not overwrite:
            # Recheck immediately before promotion to avoid silently replacing
            # a path created after the initial preflight.
            _preflight_destinations(destinations, sources, overwrite=False)
        for temporary, destination in zip(staged_paths, destinations, strict=True):
            temporary.replace(destination)
        return RepairExportResult(paths=paths)
    except RepairExportError:
        raise
    except (OSError, TypeError, ValueError) as exc:
        raise RepairExportError(f"Could not export repair artifacts: {exc}") from exc
    finally:
        for temporary in staged:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


# A descriptive alias is convenient for GUI call sites.
export_pair_repair = export_repair_bundle


__all__ = [
    "CHANGE_REPORT_VERSION",
    "RepairExportError",
    "RepairExportPaths",
    "RepairExportResult",
    "build_change_report",
    "export_change_report",
    "export_combined_repair_preview",
    "export_pair_repair",
    "export_repair_bundle",
    "export_revised_clip",
    "serialize_change_report",
]
