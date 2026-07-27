from fractions import Fraction

import pytest

from glue.io import tick_to_seconds
from glue.models import (
    MidiClip,
    MidiNote,
    TempoChange,
    TimeSignatureChange,
    TrackInfo,
)


def test_clip_keeps_exact_ticks_and_exposes_musical_time() -> None:
    note = MidiNote(
        id=0,
        pitch=60,
        onset_ticks=240,
        duration_ticks=720,
        velocity=90,
        track=0,
        channel=0,
    )
    clip = MidiClip(
        ticks_per_beat=480,
        notes=(note,),
        tracks=(TrackInfo(0, "Piano", 1_440),),
    )

    assert note.end_ticks == 960
    assert clip.length_ticks == 1_440
    assert clip.note_onset_quarter_notes(note) == Fraction(1, 2)
    assert clip.note_duration_quarter_notes(note) == Fraction(3, 2)
    assert clip.duration_quarter_notes == 3


def test_effective_timing_defaults_do_not_require_synthetic_events() -> None:
    clip = MidiClip(ticks_per_beat=960)

    assert clip.tempo_changes == ()
    assert clip.time_signature_changes == ()
    assert clip.tempo_at(0) == 500_000
    assert clip.time_signature_at(0) == (4, 4)


def test_tempo_changes_are_integrated_piecewise() -> None:
    clip = MidiClip(
        ticks_per_beat=480,
        tempo_changes=(
            TempoChange(0, 500_000),
            TempoChange(480, 1_000_000),
        ),
    )

    assert tick_to_seconds(clip, 480) == pytest.approx(0.5)
    assert tick_to_seconds(clip, 960) == pytest.approx(1.5)


def test_time_signature_exposes_exact_bar_length() -> None:
    signature = TimeSignatureChange(0, 6, 8)

    assert signature.quarter_notes_per_bar == 3


@pytest.mark.parametrize(
    ("kwargs", "message"),
    (
        ({"pitch": 128}, "pitch"),
        ({"velocity": -1}, "velocity"),
        ({"velocity": 0}, "velocity"),
        ({"channel": 16}, "channel"),
        ({"duration_ticks": -1}, "duration_ticks"),
    ),
)
def test_note_validation_rejects_invalid_midi_values(
    kwargs: dict[str, int],
    message: str,
) -> None:
    values = {
        "id": 0,
        "pitch": 60,
        "onset_ticks": 0,
        "duration_ticks": 120,
        "velocity": 90,
        "track": 0,
        "channel": 0,
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=message):
        MidiNote(**values)


@pytest.mark.parametrize(
    "kwargs",
    (
        {
            "notes": (
                MidiNote(
                    id=0,
                    pitch=60,
                    onset_ticks=0,
                    duration_ticks=120,
                    velocity=90,
                    track=1,
                    channel=0,
                ),
            )
        },
        {"tracks": (TrackInfo(1, "Invalid type-0 track"),)},
        {"tempo_changes": (TempoChange(0, 500_000, track=1),)},
        {
            "time_signature_changes": (
                TimeSignatureChange(0, 4, 4, track=1),
            )
        },
    ),
)
def test_type_zero_rejects_every_modeled_event_on_nonzero_tracks(
    kwargs: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match="track 0 events"):
        MidiClip(ticks_per_beat=480, midi_type=0, **kwargs)
