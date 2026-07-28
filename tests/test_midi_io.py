from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import mido
import pytest

from glue.io import (
    MidiContentError,
    MidiParseError,
    MidiWriteError,
    load_midi,
    read_midi,
    save_midi,
    validate_for_analysis,
    write_midi,
)
from glue.models import MidiClip, MidiNote, TempoChange, TimeSignatureChange, TrackInfo


def _write_complex_source(path: Path) -> None:
    midi = mido.MidiFile(type=1, ticks_per_beat=480)
    conductor = mido.MidiTrack()
    midi.tracks.append(conductor)
    conductor.extend(
        (
            mido.MetaMessage("track_name", name="Conductor", time=0),
            mido.MetaMessage("set_tempo", tempo=500_000, time=0),
            mido.MetaMessage("time_signature", numerator=3, denominator=4, time=0),
            mido.MetaMessage("marker", text="middle", time=480),
            mido.MetaMessage("set_tempo", tempo=1_000_000, time=0),
            mido.MetaMessage("time_signature", numerator=4, denominator=4, time=480),
            mido.MetaMessage("end_of_track", time=480),
        )
    )

    music = mido.MidiTrack()
    midi.tracks.append(music)
    music.extend(
        (
            mido.MetaMessage("track_name", name="Piano", time=0),
            mido.Message("program_change", channel=2, program=8, time=0),
            mido.Message("note_on", channel=2, note=60, velocity=91, time=120),
            mido.Message("control_change", channel=2, control=64, value=127, time=120),
            mido.Message("note_off", channel=2, note=60, velocity=19, time=360),
            mido.Message("note_on", channel=2, note=64, velocity=77, time=0),
            mido.Message("note_on", channel=2, note=64, velocity=0, time=480),
            mido.Message("sysex", data=(1, 2, 3), time=0),
            mido.MetaMessage("end_of_track", time=120),
        )
    )
    midi.save(filename=path)


def _message_dicts(path: Path) -> tuple[tuple[dict[str, object], ...], ...]:
    midi = mido.MidiFile(filename=path)
    return tuple(tuple(message.dict() for message in track) for track in midi.tracks)


def test_parser_extracts_multitrack_notes_tempo_and_signatures(tmp_path: Path) -> None:
    source = tmp_path / "complex.mid"
    _write_complex_source(source)

    document = load_midi(source)
    clip = document.clip

    assert clip.midi_type == 1
    assert clip.ticks_per_beat == 480
    assert [(track.index, track.name) for track in clip.tracks] == [
        (0, "Conductor"),
        (1, "Piano"),
    ]
    assert [
        (
            note.pitch,
            note.onset_ticks,
            note.duration_ticks,
            note.velocity,
            note.release_velocity,
            note.track,
            note.channel,
        )
        for note in clip.notes
    ] == [
        (60, 120, 480, 91, 19, 1, 2),
        (64, 600, 480, 77, 0, 1, 2),
    ]
    assert [(change.tick, change.tempo) for change in clip.tempo_changes] == [
        (0, 500_000),
        (480, 1_000_000),
    ]
    assert [
        (change.tick, change.numerator, change.denominator)
        for change in clip.time_signature_changes
    ] == [(0, 3, 4), (960, 4, 4)]
    assert document.warnings == ()
    assert read_midi(source) == clip


def test_parser_pairs_overlapping_equal_pitches_fifo(tmp_path: Path) -> None:
    source = tmp_path / "overlap.mid"
    midi = mido.MidiFile(type=0, ticks_per_beat=480)
    track = mido.MidiTrack()
    midi.tracks.append(track)
    track.extend(
        (
            mido.Message("note_on", note=60, velocity=40, time=0),
            mido.Message("note_on", note=60, velocity=80, time=120),
            mido.Message("note_off", note=60, velocity=0, time=120),
            mido.Message("note_off", note=60, velocity=0, time=120),
        )
    )
    midi.save(filename=source)

    notes = load_midi(source).clip.notes

    assert [(note.velocity, note.onset_ticks, note.duration_ticks) for note in notes] == [
        (40, 0, 240),
        (80, 120, 240),
    ]


def test_parser_reports_unmatched_events_without_inventing_notes(tmp_path: Path) -> None:
    source = tmp_path / "malformed.mid"
    midi = mido.MidiFile(type=0, ticks_per_beat=480)
    track = mido.MidiTrack()
    midi.tracks.append(track)
    track.extend(
        (
            mido.Message("note_off", note=61, velocity=0, time=0),
            mido.Message("note_on", note=60, velocity=80, time=120),
        )
    )
    midi.save(filename=source)

    document = load_midi(source)

    assert document.clip.notes == ()
    assert len(document.warnings) == 2
    assert "unmatched note-off" in document.warnings[0]
    assert "unterminated note-on" in document.warnings[1]
    with pytest.raises(MidiContentError, match="no complete positive-duration notes"):
        validate_for_analysis(document)


def test_analysis_validation_accepts_warning_bearing_midi_with_a_complete_note(
    tmp_path: Path,
) -> None:
    source = tmp_path / "warning-with-note.mid"
    midi = mido.MidiFile(type=0, ticks_per_beat=480)
    track = mido.MidiTrack()
    midi.tracks.append(track)
    track.extend(
        (
            mido.Message("note_off", note=61, velocity=0, time=0),
            mido.Message("note_on", note=60, velocity=80, time=0),
            mido.Message("note_off", note=60, velocity=0, time=480),
        )
    )
    midi.save(filename=source)

    document = load_midi(source)

    assert len(document.warnings) == 1
    assert validate_for_analysis(document) is document


def test_valid_empty_midi_remains_inspectable_but_is_not_analyzable(
    tmp_path: Path,
) -> None:
    source = tmp_path / "empty-track.mid"
    midi = mido.MidiFile(type=1, ticks_per_beat=480)
    midi.tracks.append(mido.MidiTrack([mido.MetaMessage("end_of_track")]))
    midi.save(filename=source)

    document = load_midi(source)

    assert document.clip.notes == ()
    assert document.warnings == ()
    with pytest.raises(MidiContentError, match="empty-track.mid"):
        validate_for_analysis(document)


def test_analysis_validation_accepts_positive_duration_percussion(
    tmp_path: Path,
) -> None:
    source = tmp_path / "percussion.mid"
    write_midi(
        MidiClip(
            ticks_per_beat=480,
            notes=(MidiNote(0, 36, 0, 120, 100, 0, 9),),
            midi_type=0,
        ),
        source,
    )

    document = load_midi(source)

    assert validate_for_analysis(document) is document


def test_loader_reports_missing_directory_and_zero_byte_paths_clearly(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing.mid"
    zero_byte = tmp_path / "zero.mid"
    zero_byte.write_bytes(b"")

    with pytest.raises(MidiParseError, match="does not exist.*missing.mid"):
        load_midi(missing)
    with pytest.raises(MidiParseError, match="not a file"):
        load_midi(tmp_path)
    with pytest.raises(MidiParseError, match="is empty.*zero.mid"):
        load_midi(zero_byte)


@pytest.mark.parametrize(
    ("filename", "content"),
    (
        ("random.mid", b"this is not a MIDI file"),
        (
            "truncated.mid",
            b"MThd\x00\x00\x00\x06\x00\x00\x00\x01\x01\xe0"
            + b"MTrk\x00\x00\x00\x04\x00\x90",
        ),
    ),
)
def test_loader_wraps_malformed_files_with_nonblank_context(
    tmp_path: Path,
    filename: str,
    content: bytes,
) -> None:
    source = tmp_path / filename
    source.write_bytes(content)

    with pytest.raises(MidiParseError) as caught:
        load_midi(source)

    message = str(caught.value)
    assert filename in message
    assert message.split(":", maxsplit=1)[-1].strip()


def test_unchanged_template_export_preserves_every_message(tmp_path: Path) -> None:
    source = tmp_path / "source.mid"
    output = tmp_path / "copy.mid"
    _write_complex_source(source)
    document = load_midi(source)

    save_midi(document, output)

    before = mido.MidiFile(filename=source)
    after = mido.MidiFile(filename=output)
    assert (after.type, after.ticks_per_beat) == (before.type, before.ticks_per_beat)
    assert _message_dicts(output) == _message_dicts(source)


def test_template_export_refuses_to_overwrite_its_loaded_source(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.mid"
    _write_complex_source(source)
    before = source.read_bytes()
    document = load_midi(source)

    with pytest.raises(MidiWriteError, match="Refusing to overwrite"):
        save_midi(document, source)

    assert source.read_bytes() == before


def test_repaired_export_changes_only_bound_note_pitch_fields(tmp_path: Path) -> None:
    source = tmp_path / "source.mid"
    output = tmp_path / "repaired.mid"
    _write_complex_source(source)
    document = load_midi(source)
    changed_id = document.clip.notes[0].id
    repaired_notes = tuple(
        note.with_pitch(61) if note.id == changed_id else note for note in document.clip.notes
    )
    repaired = document.clip.with_notes(repaired_notes)

    write_midi(repaired, output, template=document)

    before = _message_dicts(source)
    after = _message_dicts(output)
    changed_refs = {
        (
            document.bindings[changed_id].note_on.track,
            document.bindings[changed_id].note_on.event_index,
        ),
        (
            document.bindings[changed_id].note_off.track,
            document.bindings[changed_id].note_off.event_index,
        ),
    }
    for track_index, (before_track, after_track) in enumerate(
        zip(before, after, strict=True)
    ):
        for event_index, (before_message, after_message) in enumerate(
            zip(before_track, after_track, strict=True)
        ):
            changed_fields = {
                key
                for key in before_message.keys() | after_message.keys()
                if before_message.get(key) != after_message.get(key)
            }
            if (track_index, event_index) in changed_refs:
                assert changed_fields == {"note"}
            else:
                assert changed_fields == set()

    reread = load_midi(output).clip
    changed_note = next(note for note in reread.notes if note.id == changed_id)
    original_note = document.clip.notes[0]
    assert changed_note.pitch == 61
    assert (
        changed_note.onset_ticks,
        changed_note.duration_ticks,
        changed_note.velocity,
        changed_note.track,
        changed_note.channel,
    ) == (
        original_note.onset_ticks,
        original_note.duration_ticks,
        original_note.velocity,
        original_note.track,
        original_note.channel,
    )


def test_template_export_rejects_timing_mutation(tmp_path: Path) -> None:
    source = tmp_path / "source.mid"
    _write_complex_source(source)
    document = load_midi(source)
    first = document.clip.notes[0]
    changed = document.clip.with_notes(
        (replace(first, onset_ticks=first.onset_ticks + 1), *document.clip.notes[1:])
    )

    with pytest.raises(MidiWriteError, match="onset_ticks"):
        write_midi(changed, tmp_path / "invalid.mid", template=document)


@pytest.mark.parametrize(
    ("field_name", "mutate"),
    (
        (
            "tempo_changes",
            lambda clip: replace(
                clip,
                tempo_changes=(
                    *clip.tempo_changes,
                    TempoChange(1_440, 700_000),
                ),
            ),
        ),
        (
            "time_signature_changes",
            lambda clip: replace(
                clip,
                time_signature_changes=(
                    *clip.time_signature_changes,
                    TimeSignatureChange(1_440, 5, 4),
                ),
            ),
        ),
        (
            "tracks",
            lambda clip: replace(
                clip,
                tracks=(
                    replace(clip.tracks[0], name="Changed conductor"),
                    *clip.tracks[1:],
                ),
            ),
        ),
        (
            "length_ticks",
            lambda clip: replace(clip, length_ticks=clip.length_ticks + 1),
        ),
        (
            "name",
            lambda clip: replace(clip, name=f"{clip.name}-changed"),
        ),
    ),
)
def test_template_export_rejects_metadata_mutation(
    tmp_path: Path,
    field_name: str,
    mutate: Callable[[MidiClip], MidiClip],
) -> None:
    source = tmp_path / "source.mid"
    _write_complex_source(source)
    document = load_midi(source)

    with pytest.raises(MidiWriteError, match=field_name):
        write_midi(
            mutate(document.clip),
            tmp_path / f"invalid-{field_name}.mid",
            template=document,
        )


def _write_nested_notes(
    path: Path,
    *,
    outer_pitch: int,
    inner_pitch: int,
) -> None:
    midi = mido.MidiFile(type=0, ticks_per_beat=480)
    track = mido.MidiTrack()
    midi.tracks.append(track)
    track.extend(
        (
            mido.Message("note_on", note=outer_pitch, velocity=90, time=0),
            mido.Message("note_on", note=inner_pitch, velocity=80, time=120),
            mido.Message("note_off", note=inner_pitch, velocity=0, time=120),
            mido.Message("note_off", note=outer_pitch, velocity=0, time=240),
        )
    )
    midi.save(filename=path)


def test_template_export_rejects_new_nested_equal_pitch_overlap(tmp_path: Path) -> None:
    source = tmp_path / "nested-distinct.mid"
    _write_nested_notes(source, outer_pitch=60, inner_pitch=64)
    document = load_midi(source)
    inner = next(note for note in document.clip.notes if note.pitch == 64)
    repaired = document.clip.with_notes(
        note.with_pitch(60) if note.id == inner.id else note
        for note in document.clip.notes
    )

    with pytest.raises(MidiWriteError, match="overlapping equal-pitch pair"):
        write_midi(repaired, tmp_path / "unsafe.mid", template=document)


def test_template_export_preserves_existing_equal_pitch_overlap(tmp_path: Path) -> None:
    source = tmp_path / "nested-equal.mid"
    output = tmp_path / "nested-equal-copy.mid"
    _write_nested_notes(source, outer_pitch=60, inner_pitch=60)
    document = load_midi(source)

    save_midi(document, output)

    assert _message_dicts(output) == _message_dicts(source)


def test_template_export_allows_new_equal_pitch_when_notes_do_not_overlap(
    tmp_path: Path,
) -> None:
    source = tmp_path / "sequential.mid"
    output = tmp_path / "sequential-repaired.mid"
    midi = mido.MidiFile(type=0, ticks_per_beat=480)
    track = mido.MidiTrack()
    midi.tracks.append(track)
    track.extend(
        (
            mido.Message("note_on", note=60, velocity=90, time=0),
            mido.Message("note_off", note=60, velocity=0, time=120),
            mido.Message("note_on", note=64, velocity=80, time=0),
            mido.Message("note_off", note=64, velocity=0, time=120),
        )
    )
    midi.save(filename=source)
    document = load_midi(source)
    repaired = document.clip.with_notes(
        note.with_pitch(60) if note.pitch == 64 else note
        for note in document.clip.notes
    )

    write_midi(repaired, output, template=document)

    reloaded = load_midi(output)
    assert [note.pitch for note in reloaded.clip.notes] == [60, 60]
    assert [
        (note.onset_ticks, note.duration_ticks) for note in reloaded.clip.notes
    ] == [(0, 120), (120, 120)]


def test_generic_writer_round_trips_minimum_positive_note_on_velocity(
    tmp_path: Path,
) -> None:
    path = tmp_path / "velocity-one.mid"
    clip = MidiClip(
        ticks_per_beat=480,
        notes=(MidiNote(0, 60, 0, 120, 1, 0, 0),),
        midi_type=0,
    )

    write_midi(clip, path)

    reloaded = load_midi(path)
    assert reloaded.clip.notes[0].velocity == 1
    note_ons = [
        message
        for message in mido.MidiFile(filename=path).tracks[0]
        if message.type == "note_on" and message.velocity > 0
    ]
    assert [(message.note, message.velocity) for message in note_ons] == [(60, 1)]


def test_generic_writer_round_trips_modeled_events(tmp_path: Path) -> None:
    path = tmp_path / "modeled.mid"
    clip = MidiClip(
        ticks_per_beat=960,
        notes=(
            MidiNote(0, 72, 0, 960, 100, 1, 4, 12),
            MidiNote(1, 36, 480, 240, 110, 1, 9),
        ),
        tempo_changes=(TempoChange(0, 600_000, track=0),),
        time_signature_changes=(TimeSignatureChange(0, 6, 8, track=0),),
        tracks=(
            TrackInfo(0, "Conductor", 1_920),
            TrackInfo(1, "Notes", 1_920),
        ),
        length_ticks=1_920,
        midi_type=1,
    )

    write_midi(clip, path)
    parsed = load_midi(path).clip

    assert parsed.ticks_per_beat == 960
    assert parsed.notes == clip.notes
    assert [(item.tick, item.tempo) for item in parsed.tempo_changes] == [(0, 600_000)]
    assert [
        (item.tick, item.numerator, item.denominator)
        for item in parsed.time_signature_changes
    ] == [(0, 6, 8)]
    assert parsed.length_ticks == 1_920


def test_type_two_midi_is_rejected_as_asynchronous(tmp_path: Path) -> None:
    path = tmp_path / "type2.mid"
    midi = mido.MidiFile(type=2, ticks_per_beat=480)
    midi.tracks.append(mido.MidiTrack())
    midi.save(filename=path)

    with pytest.raises(MidiParseError, match="asynchronous"):
        load_midi(path)
