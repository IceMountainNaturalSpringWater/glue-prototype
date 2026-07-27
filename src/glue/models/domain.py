"""Typed, GUI-independent domain models for MIDI analysis.

Ticks are retained as the canonical representation so an imported file can be
exported without floating-point timing drift.  Code that compares clips with
different PPQ resolutions should use :meth:`MidiClip.tick_as_quarter_notes`.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from fractions import Fraction

DEFAULT_TEMPO_US_PER_QUARTER = 500_000
DEFAULT_TIME_SIGNATURE = (4, 4)


def _require_range(name: str, value: int, minimum: int, maximum: int) -> None:
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}, got {value}")


@dataclass(frozen=True, slots=True)
class MidiNote:
    """A paired MIDI note-on/note-off event in absolute ticks."""

    id: int
    pitch: int
    onset_ticks: int
    duration_ticks: int
    velocity: int
    track: int
    channel: int
    release_velocity: int = 0

    def __post_init__(self) -> None:
        if self.id < 0:
            raise ValueError(f"id must be non-negative, got {self.id}")
        _require_range("pitch", self.pitch, 0, 127)
        # Velocity-zero note_on messages are note-offs by MIDI convention and
        # therefore cannot represent the start of a modeled note.
        _require_range("velocity", self.velocity, 1, 127)
        _require_range("release_velocity", self.release_velocity, 0, 127)
        _require_range("channel", self.channel, 0, 15)
        if self.onset_ticks < 0:
            raise ValueError(f"onset_ticks must be non-negative, got {self.onset_ticks}")
        if self.duration_ticks < 0:
            raise ValueError(f"duration_ticks must be non-negative, got {self.duration_ticks}")
        if self.track < 0:
            raise ValueError(f"track must be non-negative, got {self.track}")

    @property
    def end_ticks(self) -> int:
        """Return the note-off position in absolute ticks."""

        return self.onset_ticks + self.duration_ticks

    @property
    def start_tick(self) -> int:
        """Compatibility alias for callers that use ``start_tick``."""

        return self.onset_ticks

    @property
    def end_tick(self) -> int:
        """Compatibility alias for callers that use ``end_tick``."""

        return self.end_ticks

    @property
    def is_percussion(self) -> bool:
        """Whether the note uses the General MIDI percussion channel.

        This is a convention rather than a certainty.  Analysis code may use
        it as a transparent default when excluding drum pitches from harmony.
        """

        return self.channel == 9

    def with_pitch(self, pitch: int) -> MidiNote:
        """Return a copy with a replacement pitch."""

        return replace(self, pitch=pitch)


# A short alias keeps downstream analysis code pleasant without losing the
# explicit public name used by the MIDI I/O API.
Note = MidiNote


@dataclass(frozen=True, slots=True)
class TempoChange:
    """A MIDI set-tempo event at an absolute tick."""

    tick: int
    microseconds_per_quarter: int
    track: int = 0
    event_index: int = 0

    def __post_init__(self) -> None:
        if self.tick < 0:
            raise ValueError(f"tick must be non-negative, got {self.tick}")
        if self.microseconds_per_quarter <= 0:
            raise ValueError("microseconds_per_quarter must be positive")
        if self.track < 0 or self.event_index < 0:
            raise ValueError("track and event_index must be non-negative")

    @property
    def tempo(self) -> int:
        """Return the value using mido's ``tempo`` terminology."""

        return self.microseconds_per_quarter

    @property
    def microseconds_per_beat(self) -> int:
        """Compatibility alias; SMF tempo is measured per quarter note."""

        return self.microseconds_per_quarter

    @property
    def bpm(self) -> float:
        """Return quarter-note beats per minute."""

        return 60_000_000 / self.microseconds_per_quarter


@dataclass(frozen=True, slots=True)
class TimeSignatureChange:
    """A MIDI time-signature event at an absolute tick."""

    tick: int
    numerator: int
    denominator: int
    clocks_per_click: int = 24
    notated_32nd_notes_per_beat: int = 8
    track: int = 0
    event_index: int = 0

    def __post_init__(self) -> None:
        if self.tick < 0:
            raise ValueError(f"tick must be non-negative, got {self.tick}")
        if self.numerator <= 0:
            raise ValueError("numerator must be positive")
        if self.denominator <= 0 or self.denominator & (self.denominator - 1):
            raise ValueError("denominator must be a positive power of two")
        _require_range("clocks_per_click", self.clocks_per_click, 0, 255)
        _require_range(
            "notated_32nd_notes_per_beat",
            self.notated_32nd_notes_per_beat,
            0,
            255,
        )
        if self.track < 0 or self.event_index < 0:
            raise ValueError("track and event_index must be non-negative")

    @property
    def quarter_notes_per_bar(self) -> Fraction:
        """Return the notated bar length in quarter-note units."""

        return Fraction(self.numerator * 4, self.denominator)


@dataclass(frozen=True, slots=True)
class TrackInfo:
    """Metadata needed to identify and faithfully reconstruct a MIDI track."""

    index: int
    name: str = ""
    length_ticks: int = 0

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError(f"index must be non-negative, got {self.index}")
        if self.length_ticks < 0:
            raise ValueError(f"length_ticks must be non-negative, got {self.length_ticks}")


@dataclass(frozen=True, slots=True)
class MidiClip:
    """Musical content and timing metadata extracted from one MIDI file."""

    ticks_per_beat: int
    notes: tuple[MidiNote, ...] = ()
    tempo_changes: tuple[TempoChange, ...] = ()
    time_signature_changes: tuple[TimeSignatureChange, ...] = ()
    tracks: tuple[TrackInfo, ...] = ()
    length_ticks: int = 0
    name: str = ""
    midi_type: int = 1

    def __post_init__(self) -> None:
        if self.ticks_per_beat <= 0:
            raise ValueError("ticks_per_beat must be positive (SMPTE timing is unsupported)")
        if self.midi_type not in (0, 1):
            raise ValueError("only synchronous MIDI file types 0 and 1 are supported")
        if self.length_ticks < 0:
            raise ValueError("length_ticks must be non-negative")

        notes = tuple(sorted(self.notes, key=lambda note: (note.onset_ticks, note.track, note.id)))
        tempos = tuple(
            sorted(self.tempo_changes, key=lambda change: (change.tick, change.track, change.event_index))
        )
        signatures = tuple(
            sorted(
                self.time_signature_changes,
                key=lambda change: (change.tick, change.track, change.event_index),
            )
        )
        tracks = tuple(sorted(self.tracks, key=lambda track: track.index))

        note_ids = [note.id for note in notes]
        if len(note_ids) != len(set(note_ids)):
            raise ValueError("note ids must be unique within a clip")
        track_indices = [track.index for track in tracks]
        if len(track_indices) != len(set(track_indices)):
            raise ValueError("track indices must be unique within a clip")
        if self.midi_type == 0:
            nonzero_tracks = (
                *(note.track for note in notes),
                *(change.track for change in tempos),
                *(change.track for change in signatures),
                *(track.index for track in tracks),
            )
            if any(track_index != 0 for track_index in nonzero_tracks):
                raise ValueError("MIDI type 0 clips may only contain track 0 events")

        inferred_length = max(
            (note.end_ticks for note in notes),
            default=0,
        )
        inferred_length = max(
            inferred_length,
            max((track.length_ticks for track in tracks), default=0),
        )

        object.__setattr__(self, "notes", notes)
        object.__setattr__(self, "tempo_changes", tempos)
        object.__setattr__(self, "time_signature_changes", signatures)
        object.__setattr__(self, "tracks", tracks)
        object.__setattr__(self, "length_ticks", max(self.length_ticks, inferred_length))

    @property
    def duration_quarter_notes(self) -> Fraction:
        """Return the full clip length as an exact quarter-note fraction."""

        return self.tick_as_quarter_notes(self.length_ticks)

    def tick_as_quarter_notes(self, tick: int) -> Fraction:
        """Convert an absolute tick to exact quarter-note units."""

        if tick < 0:
            raise ValueError("tick must be non-negative")
        return Fraction(tick, self.ticks_per_beat)

    def note_onset_quarter_notes(self, note: MidiNote) -> Fraction:
        """Return a note onset in exact quarter-note units."""

        return self.tick_as_quarter_notes(note.onset_ticks)

    def note_duration_quarter_notes(self, note: MidiNote) -> Fraction:
        """Return a note duration in exact quarter-note units."""

        return Fraction(note.duration_ticks, self.ticks_per_beat)

    def tempo_at(self, tick: int) -> int:
        """Return effective microseconds per quarter note at ``tick``."""

        if tick < 0:
            raise ValueError("tick must be non-negative")
        effective = DEFAULT_TEMPO_US_PER_QUARTER
        for change in self.tempo_changes:
            if change.tick > tick:
                break
            effective = change.microseconds_per_quarter
        return effective

    def time_signature_at(self, tick: int) -> tuple[int, int]:
        """Return the effective time signature at ``tick``."""

        if tick < 0:
            raise ValueError("tick must be non-negative")
        effective = DEFAULT_TIME_SIGNATURE
        for change in self.time_signature_changes:
            if change.tick > tick:
                break
            effective = (change.numerator, change.denominator)
        return effective

    def with_notes(self, notes: Iterable[MidiNote]) -> MidiClip:
        """Return a clip with replacement notes and unchanged metadata."""

        return replace(self, notes=tuple(notes))
