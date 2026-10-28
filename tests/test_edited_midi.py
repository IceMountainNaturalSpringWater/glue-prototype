from dataclasses import replace

import mido
import pytest

from glue.io import load_midi
from glue.io.edited import _unrelated_events, note_semantics, validate_note_edits, write_edited_midi
from scripts.generate_v05_fixtures import generate


def test_onset_duration_export_preserves_unrelated_absolute_events(tmp_path):
    path = generate(tmp_path)["rhythmic_collision_b"]
    midi = mido.MidiFile(path)
    midi.tracks[0].insert(0, mido.Message("control_change", control=64, value=127, time=0))
    midi.tracks[0].insert(0, mido.Message("program_change", program=32, time=0))
    midi.save(path)
    doc = load_midi(path)
    changed = doc.clip.with_notes(
        replace(n, onset_ticks=n.onset_ticks + 60, duration_ticks=n.duration_ticks - 60)
        if n.id == 0
        else n
        for n in doc.clip.notes
    )
    output = tmp_path / "edited.mid"
    write_edited_midi(doc, changed, output, timing=True, duration=True)
    assert note_semantics(load_midi(output).clip) == note_semantics(changed)
    assert mido.MidiFile(output).tracks[0][:2] == midi.tracks[0][:2]
    with pytest.raises(ValueError, match="Onset"):
        write_edited_midi(doc, changed, tmp_path / "forbidden.mid")
    with pytest.raises(ValueError, match="source"):
        write_edited_midi(doc, changed, path, timing=True, duration=True)


def test_rescheduling_preserves_zero_length_notes_and_all_unrelated_events(tmp_path):
    midi = mido.MidiFile(type=0, ticks_per_beat=480)
    midi.tracks.append(
        mido.MidiTrack(
            [
                mido.MetaMessage("set_tempo", tempo=600_000),
                mido.MetaMessage("time_signature", numerator=3, denominator=4),
                mido.Message("note_on", note=72, channel=2, velocity=90),
                mido.Message("note_off", note=72, channel=2, velocity=23),
                mido.Message("note_on", note=60, channel=2, velocity=81),
                mido.Message("control_change", channel=2, control=64, value=127, time=60),
                mido.Message("pitchwheel", channel=2, pitch=819, time=60),
                mido.Message("aftertouch", channel=2, value=19, time=60),
                mido.MetaMessage("marker", text="leave here", time=60),
                mido.Message("note_off", note=60, channel=2, velocity=31, time=240),
                mido.Message("program_change", channel=2, program=32, time=60),
                mido.Message("sysex", data=(0x7D, 1, 2), time=60),
                mido.MetaMessage("end_of_track", time=480),
            ]
        )
    )
    source = tmp_path / "events.mid"
    midi.save(source)
    doc = load_midi(source)
    candidate = doc.clip.with_notes(
        replace(n, pitch=62, onset_ticks=60, duration_ticks=300) if n.pitch == 60 else n
        for n in doc.clip.notes
    )
    output = write_edited_midi(
        doc, candidate, tmp_path / "rescheduled.mid", timing=True, duration=True
    )
    reopened = load_midi(output)
    assert note_semantics(reopened.clip) == note_semantics(candidate)
    assert _unrelated_events(reopened._template) == _unrelated_events(midi)
    assert any(n.duration_ticks == 0 for n in reopened.clip.notes)
    changed = next(n for n in reopened.clip.notes if n.pitch == 62)
    assert (changed.velocity, changed.release_velocity, changed.channel) == (81, 31, 2)


@pytest.mark.parametrize(
    "fields",
    [
        {"onset_ticks": 300},
        {"duration_ticks": 500},
        {"velocity": 1},
        {"channel": 4},
        {"pitch": 80},
    ],
)
def test_unsafe_edits_are_rejected_before_export(tmp_path, fields):
    doc = load_midi(generate(tmp_path)["rhythmic_collision_b"])
    candidate = doc.clip.with_notes(
        replace(n, **fields) if n.id == 0 else n for n in doc.clip.notes
    )
    with pytest.raises(ValueError):
        validate_note_edits(
            doc.clip,
            candidate,
            pitch=True,
            timing=True,
            duration=True,
            onset_limit=0.25,
            duration_limit=0.5,
            duration_fraction=0.5,
        )


def test_new_equal_pitch_overlap_and_changed_metadata_are_rejected(tmp_path):
    from scripts.generate_v05_fixtures import clip

    source = clip([(60, 0, 1, 0), (62, 0.5, 1, 0)])
    overlap = source.with_notes(replace(n, pitch=60) if n.id == 1 else n for n in source.notes)
    for candidate in (overlap, replace(source, name="changed")):
        with pytest.raises(ValueError):
            validate_note_edits(
                source,
                candidate,
                pitch=True,
                timing=True,
                duration=True,
                onset_limit=0.5,
                duration_limit=1,
                duration_fraction=0.75,
            )
