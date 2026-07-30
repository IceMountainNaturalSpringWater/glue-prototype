from __future__ import annotations

import os
from dataclasses import replace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_OPENGL", "software")
os.environ.setdefault("QT_API", "pyside6")

from PySide6.QtWidgets import QApplication

from glue.models import MidiClip, MidiNote
from glue.ui import PianoRollWidget


def _clip(*notes: tuple[int, int, int]) -> MidiClip:
    return MidiClip(
        ticks_per_beat=480,
        notes=tuple(
            MidiNote(
                id=note_id,
                pitch=pitch,
                onset_ticks=onset_ticks,
                duration_ticks=480,
                velocity=90,
                track=0,
                channel=0,
            )
            for note_id, pitch, onset_ticks in notes
        ),
    )


def _with_pitch(clip: MidiClip, note_id: int, pitch: int) -> MidiClip:
    return clip.with_notes(
        replace(note, pitch=pitch) if note.id == note_id else note
        for note in clip.notes
    )


def test_pair_comparison_tracks_both_change_sets_independently_and_renders() -> None:
    application = QApplication.instance() or QApplication([])
    original_a = _clip((0, 60, 0), (1, 67, 480))
    original_b = _clip((2, 64, 0), (0, 69, 480))
    repaired_a = _with_pitch(original_a, 0, 62)
    repaired_b = _with_pitch(original_b, 2, 62)
    widget = PianoRollWidget()
    widget.resize(760, 320)

    widget.set_pair_comparison(
        original_a,
        original_b,
        repaired_a,
        repaired_b,
    )
    widget.show()
    application.processEvents()

    assert widget.is_comparing
    assert widget.changed_note_ids_a == frozenset({0})
    assert widget.changed_note_ids_b == frozenset({2})
    assert widget.comparison_clip_a is repaired_a
    assert widget.comparison_clip_b is repaired_b
    assert widget.comparison_slot is None
    assert widget.comparison_clip is None
    assert "MIDI A has 1 changed note" in widget.accessibleDescription()
    assert "MIDI B has 1 changed note" in widget.accessibleDescription()
    assert not widget.grab().toImage().isNull()
    widget.close()


def test_pair_comparison_keeps_one_sided_legacy_properties_unambiguous() -> None:
    original_a = _clip((0, 60, 0))
    original_b = _clip((0, 64, 0))
    repaired_a = _with_pitch(original_a, 0, 61)
    widget = PianoRollWidget()

    widget.set_pair_comparison(
        original_a,
        original_b,
        repaired_a,
        original_b,
    )

    assert widget.is_comparing
    assert widget.comparison_slot == "A"
    assert widget.comparison_clip is repaired_a
    assert widget.changed_note_ids_a == frozenset({0})
    assert widget.changed_note_ids_b == frozenset()


def test_legacy_comparison_and_reset_preserve_the_v02_contract() -> None:
    original_a = _clip((0, 60, 0))
    original_b = _clip((0, 64, 0))
    repaired_b = _with_pitch(original_b, 0, 65)
    widget = PianoRollWidget()

    widget.set_comparison(original_a, original_b, "b", repaired_b)

    assert widget.is_comparing
    assert widget.comparison_slot == "B"
    assert widget.comparison_clip is repaired_b
    assert widget.comparison_clip_a is original_a
    assert widget.comparison_clip_b is repaired_b
    assert widget.changed_note_ids_a == frozenset()
    assert widget.changed_note_ids_b == frozenset({0})

    widget.set_clips(original_a, original_b)

    assert not widget.is_comparing
    assert widget.comparison_slot is None
    assert widget.comparison_clip is None
    assert widget.comparison_clip_a is None
    assert widget.comparison_clip_b is None
    assert widget.changed_note_ids_a == frozenset()
    assert widget.changed_note_ids_b == frozenset()

    with pytest.raises(ValueError, match="repaired_slot"):
        widget.set_comparison(original_a, original_b, "both", repaired_b)
