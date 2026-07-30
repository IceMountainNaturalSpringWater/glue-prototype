"""Deterministic two-track MIDI previews for repaired clip pairs."""

from __future__ import annotations

from fractions import Fraction
from itertools import groupby
from math import lcm
from pathlib import Path

from glue.models import (
    DEFAULT_TEMPO_US_PER_QUARTER,
    MidiClip,
    MidiNote,
    TempoChange,
    TimeSignatureChange,
    TrackInfo,
)

from .midi import MidiWriteError, _paths_refer_to_same_file, write_midi

PathLike = str | Path
MAX_SMF_TICKS_PER_BEAT = 0x7FFF
_DEFAULT_SIGNATURE = (4, 4, 24, 8)


class CombinedPreviewError(MidiWriteError):
    """Raised when two clips cannot share one faithful preview timeline."""


def _reject_flattening_ambiguity(clip: MidiClip, label: str) -> None:
    """Reject source-track overlaps whose note-off identity would be lost.

    The preview deliberately gives each clip one track. MIDI pairs overlapping
    equal-pitch notes by channel within that track, so notes that were isolated
    on different source tracks can acquire different durations after flattening.
    """

    notes = tuple(note for note in clip.notes if note.duration_ticks > 0)
    for index, note in enumerate(notes):
        for other in notes[index + 1 :]:
            if other.onset_ticks >= note.end_ticks:
                break
            if (
                note.track != other.track
                and note.channel == other.channel
                and note.pitch == other.pitch
                and note.onset_ticks < other.end_ticks
                and other.onset_ticks < note.end_ticks
            ):
                raise CombinedPreviewError(
                    f"Cannot create combined preview: Clip {label} has overlapping "
                    f"pitch {note.pitch} on channel {note.channel + 1} across source "
                    f"tracks {note.track} and {other.track}; flattening would make "
                    "note-off identity ambiguous"
                )


def _canonical_tempo_map(clip: MidiClip) -> tuple[tuple[Fraction, int], ...]:
    """Return only effective tempo transitions in exact quarter-note time."""

    current = DEFAULT_TEMPO_US_PER_QUARTER
    transitions: list[tuple[Fraction, int]] = []
    for tick, changes in groupby(clip.tempo_changes, key=lambda change: change.tick):
        final = tuple(changes)[-1].microseconds_per_quarter
        if final == current:
            continue
        transitions.append((Fraction(tick, clip.ticks_per_beat), final))
        current = final
    return tuple(transitions)


def _signature_value(change: TimeSignatureChange) -> tuple[int, int, int, int]:
    return (
        change.numerator,
        change.denominator,
        change.clocks_per_click,
        change.notated_32nd_notes_per_beat,
    )


def _canonical_signature_map(
    clip: MidiClip,
) -> tuple[tuple[Fraction, tuple[int, int, int, int]], ...]:
    """Return only effective meter transitions in exact quarter-note time."""

    current = _DEFAULT_SIGNATURE
    transitions: list[tuple[Fraction, tuple[int, int, int, int]]] = []
    for tick, changes in groupby(
        clip.time_signature_changes,
        key=lambda change: change.tick,
    ):
        final = _signature_value(tuple(changes)[-1])
        if final == current:
            continue
        transitions.append((Fraction(tick, clip.ticks_per_beat), final))
        current = final
    return tuple(transitions)


def _shared_ticks_per_beat(clip_a: MidiClip, clip_b: MidiClip) -> int:
    ticks_per_beat = lcm(clip_a.ticks_per_beat, clip_b.ticks_per_beat)
    if ticks_per_beat > MAX_SMF_TICKS_PER_BEAT:
        raise CombinedPreviewError(
            "Cannot create combined preview: exact timing requires "
            f"{ticks_per_beat} ticks per beat, above the Standard MIDI File "
            f"limit of {MAX_SMF_TICKS_PER_BEAT}"
        )
    return ticks_per_beat


def _tick_at_resolution(position: Fraction, ticks_per_beat: int) -> int:
    scaled = position * ticks_per_beat
    if scaled.denominator != 1:
        raise CombinedPreviewError(
            "Cannot create combined preview without rounding a timing event"
        )
    return scaled.numerator


def _preview_notes(
    clip: MidiClip,
    *,
    ticks_per_beat: int,
    track: int,
    first_id: int,
) -> tuple[MidiNote, ...]:
    scale = ticks_per_beat // clip.ticks_per_beat
    return tuple(
        MidiNote(
            id=first_id + index,
            pitch=note.pitch,
            onset_ticks=note.onset_ticks * scale,
            duration_ticks=note.duration_ticks * scale,
            velocity=note.velocity,
            release_velocity=note.release_velocity,
            track=track,
            channel=note.channel,
        )
        for index, note in enumerate(clip.notes)
    )


def build_combined_preview(
    clip_a: MidiClip,
    clip_b: MidiClip,
    *,
    track_name_a: str = "GLUE Revised A",
    track_name_b: str = "GLUE Revised B",
) -> MidiClip:
    """Build a type-1 preview with revised A and B on distinct tracks.

    MIDI has one timing resolution, tempo map, and meter map per synchronous
    file. Differing PPQ values are rescaled exactly to their least common
    multiple. Effective tempo and meter transitions must agree; choosing one
    clip's conflicting playback metadata would misrepresent the other.
    """

    if not track_name_a or not track_name_b:
        raise ValueError("combined preview track names must not be empty")

    _reject_flattening_ambiguity(clip_a, "A")
    _reject_flattening_ambiguity(clip_b, "B")

    tempo_map = _canonical_tempo_map(clip_a)
    if tempo_map != _canonical_tempo_map(clip_b):
        raise CombinedPreviewError(
            "Cannot create combined preview: Clip A and Clip B have "
            "incompatible tempo maps"
        )
    signature_map = _canonical_signature_map(clip_a)
    if signature_map != _canonical_signature_map(clip_b):
        raise CombinedPreviewError(
            "Cannot create combined preview: Clip A and Clip B have "
            "incompatible time-signature maps"
        )

    ticks_per_beat = _shared_ticks_per_beat(clip_a, clip_b)
    notes_a = _preview_notes(
        clip_a,
        ticks_per_beat=ticks_per_beat,
        track=0,
        first_id=0,
    )
    notes_b = _preview_notes(
        clip_b,
        ticks_per_beat=ticks_per_beat,
        track=1,
        first_id=len(notes_a),
    )
    length_a = clip_a.length_ticks * (ticks_per_beat // clip_a.ticks_per_beat)
    length_b = clip_b.length_ticks * (ticks_per_beat // clip_b.ticks_per_beat)
    length = max(length_a, length_b)

    tempos = tuple(
        TempoChange(
            tick=_tick_at_resolution(position, ticks_per_beat),
            microseconds_per_quarter=value,
            track=0,
            event_index=index,
        )
        for index, (position, value) in enumerate(tempo_map)
    )
    signatures = tuple(
        TimeSignatureChange(
            tick=_tick_at_resolution(position, ticks_per_beat),
            numerator=value[0],
            denominator=value[1],
            clocks_per_click=value[2],
            notated_32nd_notes_per_beat=value[3],
            track=0,
            event_index=index,
        )
        for index, (position, value) in enumerate(signature_map)
    )
    return MidiClip(
        ticks_per_beat=ticks_per_beat,
        notes=(*notes_a, *notes_b),
        tempo_changes=tempos,
        time_signature_changes=signatures,
        tracks=(
            TrackInfo(0, track_name_a, length),
            TrackInfo(1, track_name_b, length_b),
        ),
        length_ticks=length,
        name="GLUE combined preview",
        midi_type=1,
    )


def write_combined_preview(
    clip_a: MidiClip,
    clip_b: MidiClip,
    destination: PathLike,
    *,
    protected_sources: tuple[PathLike, ...] = (),
    overwrite: bool = False,
) -> Path:
    """Build and write a combined preview with explicit overwrite policy."""

    output_path = Path(destination)
    for source in protected_sources:
        if _paths_refer_to_same_file(output_path, Path(source)):
            raise CombinedPreviewError(
                "Refusing to overwrite a loaded source MIDI file with a "
                "combined preview"
            )
    if output_path.exists() and not overwrite:
        raise CombinedPreviewError(
            f"Refusing to overwrite existing combined preview '{output_path}'"
        )
    preview = build_combined_preview(clip_a, clip_b)
    return write_midi(preview, output_path)


__all__ = [
    "MAX_SMF_TICKS_PER_BEAT",
    "CombinedPreviewError",
    "build_combined_preview",
    "write_combined_preview",
]
