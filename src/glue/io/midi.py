"""Standard MIDI File parsing and preservation-first export."""

from __future__ import annotations

import copy
from collections import defaultdict, deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

import mido

from glue.models import MidiClip, MidiNote, TempoChange, TimeSignatureChange, TrackInfo

PathLike = str | Path


class MidiIOError(ValueError):
    """Base class for user-facing MIDI I/O errors."""


class MidiParseError(MidiIOError):
    """Raised when a file cannot be represented on GLUE's shared timeline."""


class MidiWriteError(MidiIOError):
    """Raised when a clip cannot be exported without violating invariants."""


@dataclass(frozen=True, slots=True)
class EventReference:
    """Location of a message within a source MIDI track."""

    track: int
    event_index: int


@dataclass(frozen=True, slots=True)
class NoteBinding:
    """Links a domain note to its original note-on and note-off messages."""

    note_id: int
    note_on: EventReference
    note_off: EventReference


@dataclass(frozen=True, slots=True)
class MidiDocument:
    """An analyzed clip plus private source data used for faithful export.

    Analysis and repair functions should consume :attr:`clip` only.  Keeping
    the mido template here lets the writer preserve messages the V0.1 domain
    model does not interpret, including program, controller, marker, and SysEx
    events.
    """

    clip: MidiClip
    source_path: Path
    _template: mido.MidiFile = field(repr=False, compare=False, hash=False)
    _bindings: Mapping[int, NoteBinding] = field(repr=False, compare=False, hash=False)
    warnings: tuple[str, ...] = ()

    @property
    def bindings(self) -> Mapping[int, NoteBinding]:
        """Return read-only note-to-source-event bindings."""

        return self._bindings


@dataclass(frozen=True, slots=True)
class _PendingNote:
    pitch: int
    onset_ticks: int
    velocity: int
    track: int
    channel: int
    note_on: EventReference


@dataclass(frozen=True, slots=True)
class _CompletedNote:
    pending: _PendingNote
    end_ticks: int
    release_velocity: int
    note_off: EventReference


def load_midi(path: PathLike) -> MidiDocument:
    """Load a type-0 or type-1 Standard MIDI File.

    Delta times are converted to absolute ticks without resampling.  Notes
    with no matching note-off are omitted and reported in ``warnings`` rather
    than assigned an invented duration.
    """

    source_path = Path(path)
    try:
        midi = mido.MidiFile(filename=source_path)
        return _parse_loaded_midi(midi, source_path)
    except MidiParseError:
        raise
    except (EOFError, OSError, TypeError, ValueError) as exc:
        raise MidiParseError(f"Could not read MIDI file '{source_path}': {exc}") from exc


def parse_midi(path: PathLike) -> MidiDocument:
    """Alias for :func:`load_midi`."""

    return load_midi(path)


def read_midi(path: PathLike) -> MidiClip:
    """Load only the pure domain clip.

    Use :func:`load_midi` when the source may later be exported, because its
    :class:`MidiDocument` retains loss-minimizing source-event bindings.
    """

    return load_midi(path).clip


def _parse_loaded_midi(midi: mido.MidiFile, source_path: Path) -> MidiDocument:
    if midi.type not in (0, 1):
        raise MidiParseError(
            f"MIDI type {midi.type} is asynchronous and cannot use one shared analysis timeline"
        )
    if midi.type == 0 and len(midi.tracks) != 1:
        raise MidiParseError("MIDI type 0 must contain exactly one track")
    if midi.ticks_per_beat <= 0:
        raise MidiParseError("SMPTE/non-PPQ MIDI timing is not supported")

    completed: list[_CompletedNote] = []
    tempo_changes: list[TempoChange] = []
    time_signature_changes: list[TimeSignatureChange] = []
    track_infos: list[TrackInfo] = []
    warnings: list[str] = []

    for track_index, track in enumerate(midi.tracks):
        absolute_tick = 0
        track_name = ""
        active: dict[tuple[int, int], deque[_PendingNote]] = defaultdict(deque)

        for event_index, message in enumerate(track):
            if message.time < 0:
                raise MidiParseError(
                    f"Track {track_index}, event {event_index} has a negative delta time"
                )
            absolute_tick += message.time

            if message.type == "track_name" and not track_name:
                track_name = message.name
            elif message.type == "set_tempo":
                tempo_changes.append(
                    TempoChange(
                        tick=absolute_tick,
                        microseconds_per_quarter=message.tempo,
                        track=track_index,
                        event_index=event_index,
                    )
                )
            elif message.type == "time_signature":
                time_signature_changes.append(
                    TimeSignatureChange(
                        tick=absolute_tick,
                        numerator=message.numerator,
                        denominator=message.denominator,
                        clocks_per_click=message.clocks_per_click,
                        notated_32nd_notes_per_beat=message.notated_32nd_notes_per_beat,
                        track=track_index,
                        event_index=event_index,
                    )
                )

            if message.type == "note_on" and message.velocity > 0:
                key = (message.channel, message.note)
                active[key].append(
                    _PendingNote(
                        pitch=message.note,
                        onset_ticks=absolute_tick,
                        velocity=message.velocity,
                        track=track_index,
                        channel=message.channel,
                        note_on=EventReference(track_index, event_index),
                    )
                )
                continue

            is_note_off = message.type == "note_off" or (
                message.type == "note_on" and message.velocity == 0
            )
            if not is_note_off:
                continue

            key = (message.channel, message.note)
            if not active[key]:
                warnings.append(
                    "Ignored unmatched note-off "
                    f"for pitch {message.note} on track {track_index}, "
                    f"channel {message.channel + 1}, tick {absolute_tick}"
                )
                continue

            # MIDI does not define the identity of overlapping equal-pitch
            # voices. FIFO is deterministic and matches common sequencer
            # output; the ambiguity is intentionally documented here.
            pending = active[key].popleft()
            completed.append(
                _CompletedNote(
                    pending=pending,
                    end_ticks=absolute_tick,
                    release_velocity=message.velocity,
                    note_off=EventReference(track_index, event_index),
                )
            )

        for pending_notes in active.values():
            for pending in pending_notes:
                warnings.append(
                    "Ignored unterminated note-on "
                    f"for pitch {pending.pitch} on track {track_index}, "
                    f"channel {pending.channel + 1}, tick {pending.onset_ticks}"
                )

        track_infos.append(
            TrackInfo(index=track_index, name=track_name, length_ticks=absolute_tick)
        )

    completed.sort(
        key=lambda item: (
            item.pending.onset_ticks,
            item.pending.track,
            item.pending.note_on.event_index,
        )
    )
    notes: list[MidiNote] = []
    bindings: dict[int, NoteBinding] = {}
    for note_id, item in enumerate(completed):
        pending = item.pending
        notes.append(
            MidiNote(
                id=note_id,
                pitch=pending.pitch,
                onset_ticks=pending.onset_ticks,
                duration_ticks=item.end_ticks - pending.onset_ticks,
                velocity=pending.velocity,
                release_velocity=item.release_velocity,
                track=pending.track,
                channel=pending.channel,
            )
        )
        bindings[note_id] = NoteBinding(
            note_id=note_id,
            note_on=pending.note_on,
            note_off=item.note_off,
        )

    clip = MidiClip(
        ticks_per_beat=midi.ticks_per_beat,
        notes=tuple(notes),
        tempo_changes=tuple(tempo_changes),
        time_signature_changes=tuple(time_signature_changes),
        tracks=tuple(track_infos),
        length_ticks=max((track.length_ticks for track in track_infos), default=0),
        name=source_path.stem,
        midi_type=midi.type,
    )
    return MidiDocument(
        clip=clip,
        source_path=source_path,
        warnings=tuple(warnings),
        _template=midi,
        _bindings=MappingProxyType(bindings),
    )


def tick_to_seconds(clip: MidiClip, tick: int) -> float:
    """Convert an absolute tick to elapsed seconds using the clip tempo map."""

    if tick < 0:
        raise ValueError("tick must be non-negative")

    previous_tick = 0
    current_tempo = 500_000
    elapsed_seconds = 0.0
    for change in clip.tempo_changes:
        if change.tick > tick:
            break
        if change.tick > previous_tick:
            elapsed_seconds += mido.tick2second(
                change.tick - previous_tick,
                clip.ticks_per_beat,
                current_tempo,
            )
        current_tempo = change.microseconds_per_quarter
        previous_tick = change.tick

    elapsed_seconds += mido.tick2second(
        tick - previous_tick,
        clip.ticks_per_beat,
        current_tempo,
    )
    return elapsed_seconds


def write_midi(
    clip: MidiClip,
    destination: PathLike,
    *,
    template: MidiDocument | None = None,
) -> Path:
    """Write ``clip`` to a Standard MIDI File.

    When ``template`` is supplied, only note pitch may differ from its source
    clip.  Every source message and delta time is copied, and the pitch is
    patched on both halves of each paired note.  Without a template, the
    writer creates a deterministic MIDI file from modeled events.
    """

    output_path = Path(destination)
    if template is None:
        midi = _build_midi(clip)
    else:
        _validate_pitch_only_replacement(template, clip)
        midi = _patched_template(template, clip)

    try:
        midi.save(filename=output_path)
    except (OSError, TypeError, ValueError) as exc:
        raise MidiWriteError(f"Could not write MIDI file '{output_path}': {exc}") from exc
    return output_path


def save_midi(
    document: MidiDocument,
    destination: PathLike,
    *,
    clip: MidiClip | None = None,
) -> Path:
    """Export a loaded document, optionally using a pitch-repaired clip."""

    return write_midi(clip or document.clip, destination, template=document)


def export_midi(
    clip: MidiClip,
    destination: PathLike,
    *,
    template: MidiDocument | None = None,
) -> Path:
    """Alias for :func:`write_midi` with an export-oriented name."""

    return write_midi(clip, destination, template=template)


def _validate_pitch_only_replacement(document: MidiDocument, replacement: MidiClip) -> None:
    original = document.clip
    original_by_id = {note.id: note for note in original.notes}
    replacement_by_id = {note.id: note for note in replacement.notes}
    if original_by_id.keys() != replacement_by_id.keys():
        raise MidiWriteError("replacement clip must contain exactly the source note ids")

    if replacement.ticks_per_beat != original.ticks_per_beat:
        raise MidiWriteError("replacement clip may not change ticks_per_beat")
    if replacement.midi_type != original.midi_type:
        raise MidiWriteError("replacement clip may not change MIDI file type")

    metadata_fields = (
        "tempo_changes",
        "time_signature_changes",
        "tracks",
        "length_ticks",
        "name",
    )
    for field_name in metadata_fields:
        if getattr(replacement, field_name) != getattr(original, field_name):
            raise MidiWriteError(
                f"replacement clip may not change {field_name}"
            )

    invariant_fields = (
        "onset_ticks",
        "duration_ticks",
        "velocity",
        "release_velocity",
        "track",
        "channel",
    )
    for note_id, source_note in original_by_id.items():
        candidate = replacement_by_id[note_id]
        for field_name in invariant_fields:
            if getattr(candidate, field_name) != getattr(source_note, field_name):
                raise MidiWriteError(
                    f"replacement note {note_id} changed {field_name}; "
                    "template export supports pitch edits only"
                )
    _reject_new_equal_pitch_overlaps(original_by_id, replacement_by_id)


def _reject_new_equal_pitch_overlaps(
    original_by_id: Mapping[int, MidiNote],
    replacement_by_id: Mapping[int, MidiNote],
) -> None:
    """Reject pitch edits whose note-off identity could change on reparse.

    Equal-pitch voices are paired FIFO by the parser.  If originally distinct
    pitches become equal while their half-open time ranges overlap on one
    track/channel, patching their note-off pitches can associate those offs
    with different note-ons.  Existing equal-pitch overlaps remain valid.
    """

    groups: dict[tuple[int, int, int], list[MidiNote]] = defaultdict(list)
    for note in replacement_by_id.values():
        groups[(note.track, note.channel, note.pitch)].append(note)

    for notes in groups.values():
        active: list[MidiNote] = []
        for note in sorted(
            notes,
            key=lambda item: (item.onset_ticks, item.end_ticks, item.id),
        ):
            active = [
                prior for prior in active if prior.end_ticks > note.onset_ticks
            ]
            for prior in active:
                if original_by_id[prior.id].pitch != original_by_id[note.id].pitch:
                    raise MidiWriteError(
                        "replacement creates an overlapping equal-pitch pair "
                        f"from source notes {prior.id} and {note.id} whose "
                        "original pitches differed"
                    )
            active.append(note)


def _patched_template(document: MidiDocument, replacement: MidiClip) -> mido.MidiFile:
    midi = copy.deepcopy(document._template)
    replacement_by_id = {note.id: note for note in replacement.notes}

    for note_id, binding in document.bindings.items():
        pitch = replacement_by_id[note_id].pitch
        for reference in (binding.note_on, binding.note_off):
            try:
                message = midi.tracks[reference.track][reference.event_index]
            except IndexError as exc:
                raise MidiWriteError("source event binding is no longer valid") from exc
            if message.type not in ("note_on", "note_off"):
                raise MidiWriteError("source event binding no longer points to a note message")
            message.note = pitch

    return midi


@dataclass(frozen=True, slots=True)
class _OutputEvent:
    tick: int
    priority: int
    sequence: int
    message: mido.Message | mido.MetaMessage


def _build_midi(clip: MidiClip) -> mido.MidiFile:
    referenced_tracks = [
        *(track.index for track in clip.tracks),
        *(note.track for note in clip.notes),
        *(change.track for change in clip.tempo_changes),
        *(change.track for change in clip.time_signature_changes),
    ]
    track_count = max(referenced_tracks, default=0) + 1
    if clip.midi_type == 0 and track_count != 1:
        raise MidiWriteError("MIDI type 0 may only contain track 0 events")

    events: list[list[_OutputEvent]] = [[] for _ in range(track_count)]
    sequence = 0

    track_info_by_index = {track.index: track for track in clip.tracks}
    for track_index, track_info in track_info_by_index.items():
        if track_info.name:
            events[track_index].append(
                _OutputEvent(
                    tick=0,
                    priority=0,
                    sequence=sequence,
                    message=mido.MetaMessage("track_name", name=track_info.name, time=0),
                )
            )
            sequence += 1

    for change in clip.tempo_changes:
        events[change.track].append(
            _OutputEvent(
                tick=change.tick,
                priority=1,
                sequence=sequence,
                message=mido.MetaMessage(
                    "set_tempo",
                    tempo=change.microseconds_per_quarter,
                    time=0,
                ),
            )
        )
        sequence += 1

    for change in clip.time_signature_changes:
        events[change.track].append(
            _OutputEvent(
                tick=change.tick,
                priority=1,
                sequence=sequence,
                message=mido.MetaMessage(
                    "time_signature",
                    numerator=change.numerator,
                    denominator=change.denominator,
                    clocks_per_click=change.clocks_per_click,
                    notated_32nd_notes_per_beat=change.notated_32nd_notes_per_beat,
                    time=0,
                ),
            )
        )
        sequence += 1

    for note in clip.notes:
        events[note.track].append(
            _OutputEvent(
                tick=note.onset_ticks,
                priority=3,
                sequence=sequence,
                message=mido.Message(
                    "note_on",
                    channel=note.channel,
                    note=note.pitch,
                    velocity=note.velocity,
                    time=0,
                ),
            )
        )
        sequence += 1
        events[note.track].append(
            _OutputEvent(
                tick=note.end_ticks,
                priority=4 if note.duration_ticks == 0 else 2,
                sequence=sequence,
                message=mido.Message(
                    "note_off",
                    channel=note.channel,
                    note=note.pitch,
                    velocity=note.release_velocity,
                    time=0,
                ),
            )
        )
        sequence += 1

    midi = mido.MidiFile(type=clip.midi_type, ticks_per_beat=clip.ticks_per_beat)
    for track_index, track_events in enumerate(events):
        output_track = mido.MidiTrack()
        midi.tracks.append(output_track)
        previous_tick = 0
        for event in sorted(
            track_events,
            key=lambda item: (item.tick, item.priority, item.sequence),
        ):
            output_track.append(event.message.copy(time=event.tick - previous_tick))
            previous_tick = event.tick

        requested_length = track_info_by_index.get(
            track_index,
            TrackInfo(track_index),
        ).length_ticks
        if track_index == 0:
            requested_length = max(requested_length, clip.length_ticks)
        output_track.append(
            mido.MetaMessage(
                "end_of_track",
                time=max(0, requested_length - previous_tick),
            )
        )

    return midi


def message_signature(message: mido.Message | mido.MetaMessage) -> tuple[tuple[str, object], ...]:
    """Return a stable, test-friendly representation of one mido message."""

    return tuple(sorted(message.dict().items()))


def track_signatures(
    midi: mido.MidiFile,
) -> tuple[tuple[tuple[tuple[str, object], ...], ...], ...]:
    """Return stable semantic signatures for every message in every track."""

    return tuple(tuple(message_signature(message) for message in track) for track in midi.tracks)


def changed_message_fields(
    before: Sequence[mido.Message | mido.MetaMessage],
    after: Sequence[mido.Message | mido.MetaMessage],
) -> tuple[tuple[int, tuple[str, ...]], ...]:
    """Describe changed fields between equal-length message sequences.

    This small helper is useful for preservation regression tests and does not
    participate in application analysis.
    """

    if len(before) != len(after):
        raise ValueError("message sequences must have equal length")
    changes: list[tuple[int, tuple[str, ...]]] = []
    for index, (left, right) in enumerate(zip(before, after, strict=True)):
        left_dict = left.dict()
        right_dict = right.dict()
        fields = tuple(
            sorted(
                key
                for key in left_dict.keys() | right_dict.keys()
                if left_dict.get(key) != right_dict.get(key)
            )
        )
        if fields:
            changes.append((index, fields))
    return tuple(changes)
