"""Source-preserving export for the V0.4 single-clip repair workflow."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import mido

from glue import __version__
from glue.fixes import SingleRepairResult
from glue.io import MidiDocument, MidiWriteError, load_midi, save_midi
from glue.io.midi import _paths_refer_to_same_file
from glue.models import MidiClip, MidiNote

PathLike = str | Path
SINGLE_CHANGE_REPORT_VERSION = __version__


class SingleRepairExportError(MidiWriteError):
    """Raised before a single-repair export can alter a destination."""


def _validate_source(
    result: SingleRepairResult,
    document: MidiDocument,
) -> None:
    if result.original_clip != document.clip:
        raise SingleRepairExportError(
            "Single repair candidate does not match the loaded source document"
        )
    if not result.has_improvement:
        raise SingleRepairExportError(
            "No improving repair is available to export"
        )


def _preflight_destination(
    destination: Path,
    source: Path,
    *,
    overwrite: bool,
) -> None:
    if _paths_refer_to_same_file(destination, source):
        raise SingleRepairExportError(
            "Refusing to overwrite the loaded source MIDI file; "
            "choose a different export path"
        )
    if destination.exists():
        if destination.is_dir():
            raise SingleRepairExportError(
                f"Single repair export destination is a directory: '{destination}'"
            )
        if not overwrite:
            raise SingleRepairExportError(
                f"Refusing to overwrite existing export '{destination}'"
            )
    if not destination.parent.is_dir():
        raise SingleRepairExportError(
            f"Single repair export directory does not exist: '{destination.parent}'"
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


def _clip_semantic_signature(clip: MidiClip) -> tuple[object, ...]:
    """Return every reparse-stable modeled field except the path-derived name."""

    return (
        clip.ticks_per_beat,
        clip.midi_type,
        tuple(_note_signature(note) for note in clip.notes),
        clip.tempo_changes,
        clip.time_signature_changes,
        clip.tracks,
        clip.length_ticks,
    )


def _validate_round_trip(
    staged: Path,
    result: SingleRepairResult,
    document: MidiDocument,
) -> None:
    reloaded = load_midi(staged).clip
    if _clip_semantic_signature(reloaded) != _clip_semantic_signature(
        result.repaired_clip
    ):
        raise SingleRepairExportError(
            "Repaired MIDI did not reopen with the intended pitch-only semantics"
        )

    before = mido.MidiFile(filename=document.source_path)
    after = mido.MidiFile(filename=staged)
    if (
        before.type != after.type
        or before.ticks_per_beat != after.ticks_per_beat
        or len(before.tracks) != len(after.tracks)
    ):
        raise SingleRepairExportError(
            "Repaired MIDI changed source file structure"
        )
    edited_pitch_by_id = {
        edit.note_id: edit.repaired_pitch for edit in result.edits
    }
    expected_references = {
        (reference.track, reference.event_index): edited_pitch_by_id[note_id]
        for note_id in edited_pitch_by_id
        for reference in (
            document.bindings[note_id].note_on,
            document.bindings[note_id].note_off,
        )
    }
    for track_index, (source_track, repaired_track) in enumerate(
        zip(before.tracks, after.tracks, strict=True)
    ):
        if len(source_track) != len(repaired_track):
            raise SingleRepairExportError(
                "Repaired MIDI changed the source event count"
            )
        for event_index, (source_message, repaired_message) in enumerate(
            zip(source_track, repaired_track, strict=True)
        ):
            source_fields = source_message.dict()
            repaired_fields = repaired_message.dict()
            changed = {
                name
                for name in source_fields.keys() | repaired_fields.keys()
                if source_fields.get(name) != repaired_fields.get(name)
            }
            expected_pitch = expected_references.get((track_index, event_index))
            if expected_pitch is None:
                if changed:
                    raise SingleRepairExportError(
                        "Repaired MIDI changed an unrelated source event"
                    )
            elif (
                changed != {"note"}
                or repaired_fields.get("note") != expected_pitch
            ):
                raise SingleRepairExportError(
                    "Repaired MIDI changed more than an approved note pitch"
                )


def _edit_records(
    result: SingleRepairResult,
) -> list[dict[str, object]]:
    original_by_id = {
        note.id: note for note in result.original_clip.notes
    }
    suggestion_by_id = {
        suggestion.suggestion_id: suggestion
        for suggestion in result.before_analysis.suggestions
    }
    records: list[dict[str, object]] = []
    for edit in sorted(
        result.edits,
        key=lambda item: (
            original_by_id[item.note_id].onset_ticks,
            original_by_id[item.note_id].track,
            original_by_id[item.note_id].channel,
            item.note_id,
        ),
    ):
        note = original_by_id[edit.note_id]
        suggestion_ids = result.suggestion_ids_for_edit(edit.note_id)
        records.append(
            {
                "note_id": edit.note_id,
                "track": note.track,
                "channel": note.channel,
                "original_pitch": edit.original_pitch,
                "revised_pitch": edit.repaired_pitch,
                "onset_ticks": note.onset_ticks,
                "duration_ticks": note.duration_ticks,
                "suggestion_ids": list(suggestion_ids),
                "suggestion_categories": sorted(
                    {
                        suggestion_by_id[suggestion_id].category.value
                        for suggestion_id in suggestion_ids
                    }
                ),
            }
        )
    return records


def build_single_change_report(
    result: SingleRepairResult,
    document: MidiDocument,
) -> dict[str, object]:
    """Return a deterministic, traceable advanced JSON report."""

    _validate_source(result, document)
    return {
        "version": SINGLE_CHANGE_REPORT_VERSION,
        "workflow": "polish-one-clip",
        "preset": result.preset.value,
        "preservation": result.preservation,
        "before_score": result.original_score,
        "after_score": result.repaired_score,
        "score_improvement": result.score_improvement,
        "stop_reason": result.stop_reason,
        "source": document.source_path.name,
        "retention": result.retention,
        "changed_note_count": result.changed_note_count,
        "enabled_suggestion_ids": sorted(result.enabled_suggestion_ids),
        "changed_notes": _edit_records(result),
    }


def serialize_single_change_report(report: dict[str, object]) -> bytes:
    """Serialize a single-clip report as stable UTF-8 JSON."""

    text = json.dumps(
        report,
        allow_nan=False,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    return f"{text}\n".encode()


def _promote(
    temporary: Path,
    destination: Path,
    source: Path,
    *,
    overwrite: bool,
) -> Path:
    if not overwrite:
        _preflight_destination(destination, source, overwrite=False)
    temporary.replace(destination)
    return destination


def export_single_repaired_midi(
    result: SingleRepairResult,
    document: MidiDocument,
    destination: PathLike,
    *,
    overwrite: bool = False,
) -> Path:
    """Export one validated source-preserving repaired MIDI file."""

    _validate_source(result, document)
    output = Path(destination)
    _preflight_destination(output, document.source_path, overwrite=overwrite)
    temporary = _temporary_path(output)
    try:
        save_midi(document, temporary, clip=result.repaired_clip)
        _validate_round_trip(temporary, result, document)
        return _promote(
            temporary,
            output,
            document.source_path,
            overwrite=overwrite,
        )
    except SingleRepairExportError:
        raise
    except (OSError, TypeError, ValueError) as exc:
        raise SingleRepairExportError(
            f"Could not export repaired MIDI: {exc}"
        ) from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def export_single_change_report(
    result: SingleRepairResult,
    document: MidiDocument,
    destination: PathLike,
    *,
    overwrite: bool = False,
) -> Path:
    """Export the optional advanced single-repair JSON report."""

    report = build_single_change_report(result, document)
    report_bytes = serialize_single_change_report(report)
    output = Path(destination)
    _preflight_destination(output, document.source_path, overwrite=overwrite)
    temporary = _temporary_path(output)
    try:
        temporary.write_bytes(report_bytes)
        parsed = json.loads(temporary.read_text(encoding="utf-8"))
        if parsed != report:
            raise SingleRepairExportError(
                "Single repair report did not round-trip as JSON"
            )
        return _promote(
            temporary,
            output,
            document.source_path,
            overwrite=overwrite,
        )
    except SingleRepairExportError:
        raise
    except (
        OSError,
        UnicodeError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        raise SingleRepairExportError(
            f"Could not export single repair report: {exc}"
        ) from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


# Compact aliases keep GUI call sites readable.
export_single_repair = export_single_repaired_midi
export_single_repair_report = export_single_change_report


__all__ = [
    "SINGLE_CHANGE_REPORT_VERSION",
    "SingleRepairExportError",
    "build_single_change_report",
    "export_single_change_report",
    "export_single_repair",
    "export_single_repair_report",
    "export_single_repaired_midi",
    "serialize_single_change_report",
]
