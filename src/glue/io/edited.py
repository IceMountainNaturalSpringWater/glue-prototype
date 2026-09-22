"""Explicitly authorized note-event rescheduling with source-event preservation."""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from pathlib import Path

import mido

from glue.models import MidiClip

from .midi import MidiDocument, MidiWriteError, _paths_refer_to_same_file, load_midi


def validate_note_edits(
    source: MidiClip,
    candidate: MidiClip,
    *,
    pitch: bool,
    timing: bool,
    duration: bool,
    onset_limit: float,
    duration_limit: float,
    duration_fraction: float,
) -> None:
    """Validate final-state safety; movement bounds are relative to the source."""
    if replace(candidate, notes=source.notes) != source:
        raise MidiWriteError("Repair changed clip metadata or extended the source timeline")
    originals = {n.id: n for n in source.notes}
    track_ends = {t.index: t.length_ticks for t in source.tracks}
    if originals.keys() != {n.id for n in candidate.notes}:
        raise MidiWriteError("Repair changed source note identities")
    for n in candidate.notes:
        old = originals[n.id]
        if (
            replace(
                n, pitch=old.pitch, onset_ticks=old.onset_ticks, duration_ticks=old.duration_ticks
            )
            != old
        ):
            raise MidiWriteError("Repair changed velocity, track, channel, or unrelated note data")
        if n == old:
            continue
        if (
            old.is_percussion
            or n.duration_ticks <= 0
            or n.end_ticks > min(source.length_ticks, track_ends.get(n.track, source.length_ticks))
        ):
            raise MidiWriteError("Invalid duration, percussion edit, or movement beyond the clip")
        if n.pitch != old.pitch and (not pitch or abs(n.pitch - old.pitch) > 12):
            raise MidiWriteError("Pitch edit is not permitted")
        shift = abs(n.onset_ticks - old.onset_ticks) / source.ticks_per_beat
        resize = abs(n.duration_ticks - old.duration_ticks)
        if shift and (not timing or shift > onset_limit + 1e-9):
            raise MidiWriteError("Onset movement exceeds permission or beat limit")
        if resize and (
            not duration
            or resize / source.ticks_per_beat > duration_limit + 1e-9
            or resize > old.duration_ticks * duration_fraction + 1e-9
        ):
            raise MidiWriteError("Duration movement exceeds permission or limit")
    notes = candidate.notes
    for i, left in enumerate(notes):
        for right in notes[i + 1 :]:
            if right.onset_ticks >= left.end_ticks:
                break
            if (left.track, left.channel, left.pitch) != (right.track, right.channel, right.pitch):
                continue
            a, b = originals[left.id], originals[right.id]
            # Retain imported overlaps only if neither paired note was touched.
            if left != a or right != b:
                raise MidiWriteError("Repair creates or changes ambiguous equal-pitch overlap")


def note_semantics(clip: MidiClip) -> Counter:
    """IDs may reorder after a moved onset; match full audible note semantics."""
    return Counter(
        (
            n.pitch,
            n.onset_ticks,
            n.duration_ticks,
            n.velocity,
            n.release_velocity,
            n.track,
            n.channel,
        )
        for n in clip.notes
    )


def _unrelated_events(midi: mido.MidiFile) -> tuple:
    tracks = []
    for track in midi.tracks:
        tick = 0
        events = []
        for msg in track:
            tick += msg.time
            if msg.type not in ("note_on", "note_off"):
                fields = msg.dict()
                fields.pop("time")
                events.append((tick, fields))
        tracks.append(events)
    return tuple(tracks)


def write_edited_midi(
    document: MidiDocument,
    candidate: MidiClip,
    destination: str | Path,
    *,
    pitch: bool = True,
    timing: bool = False,
    duration: bool = False,
    onset_limit: float = 0.5,
    duration_limit: float = 1.0,
    duration_fraction: float = 0.75,
) -> Path:
    """Move bound on/off events only; preserve other events at absolute ticks.

    The caller stages destinations. Equal-tick events preserve original order,
    except note-offs precede note-ons to keep retriggers unambiguous.
    """
    output = Path(destination)
    if _paths_refer_to_same_file(output, document.source_path):
        raise MidiWriteError("Refusing to overwrite the loaded source MIDI file")
    validate_note_edits(
        document.clip,
        candidate,
        pitch=pitch,
        timing=timing,
        duration=duration,
        onset_limit=onset_limit,
        duration_limit=duration_limit,
        duration_fraction=duration_fraction,
    )
    notes = {n.id: n for n in candidate.notes}
    patches = {}
    zero_events = set()
    for ident, binding in document.bindings.items():
        note = notes[ident]
        patches[binding.note_on.track, binding.note_on.event_index] = (note.onset_ticks, note.pitch)
        patches[binding.note_off.track, binding.note_off.event_index] = (note.end_ticks, note.pitch)
        if note.duration_ticks == 0:
            zero_events.update(
                (
                    (binding.note_on.track, binding.note_on.event_index),
                    (binding.note_off.track, binding.note_off.event_index),
                )
            )
    midi = mido.MidiFile(type=document.clip.midi_type, ticks_per_beat=document.clip.ticks_per_beat)
    for ti, track in enumerate(document._template.tracks):
        tick = 0
        events = []
        for ei, msg in enumerate(track):
            tick += msg.time
            event_tick = tick
            changed = msg.copy()
            if (ti, ei) in patches:
                event_tick, changed.note = patches[ti, ei]
            off = changed.type == "note_off" or (
                changed.type == "note_on" and changed.velocity == 0
            )
            priority = 0 if off else 2 if changed.type == "end_of_track" else 1
            if (ti, ei) in zero_events:
                priority = 1  # Preserve an imported zero-length on/off pair's order.
            events.append((event_tick, priority, ei, changed))
        output_track = mido.MidiTrack()
        prior = 0
        for tick, _, _, msg in sorted(events, key=lambda e: e[:3]):
            output_track.append(msg.copy(time=tick - prior))
            prior = tick
        midi.tracks.append(output_track)
    midi.save(output)
    reopened = load_midi(output)
    if note_semantics(reopened.clip) != note_semantics(candidate):
        raise MidiWriteError("Edited MIDI failed note pairing round-trip validation")
    if _unrelated_events(reopened._template) != _unrelated_events(document._template):
        raise MidiWriteError("Edited MIDI changed unrelated absolute event positions")
    return output
