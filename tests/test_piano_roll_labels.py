from __future__ import annotations

import os
from itertools import pairwise

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_OPENGL", "software")
os.environ.setdefault("QT_API", "pyside6")

from PySide6.QtCore import QPoint, QRectF
from PySide6.QtGui import QColor, QFontMetricsF, QPalette
from PySide6.QtWidgets import QApplication, QScrollArea

from glue.models import MidiClip, MidiNote
from glue.ui.visualizations import PianoRollWidget, midi_pitch_name


def _application() -> QApplication:
    return QApplication.instance() or QApplication([])


def _clip(*pitches: int) -> MidiClip:
    return MidiClip(
        ticks_per_beat=480,
        notes=tuple(
            MidiNote(
                id=note_id,
                pitch=pitch,
                onset_ticks=note_id * 480,
                duration_ticks=480,
                velocity=90,
                track=0,
                channel=0,
            )
            for note_id, pitch in enumerate(pitches)
        ),
    )


def _contrast_ratio(first: QColor, second: QColor) -> float:
    def luminance(color: QColor) -> float:
        def linear(channel: int) -> float:
            normalized = channel / 255.0
            if normalized <= 0.04045:
                return normalized / 12.92
            return ((normalized + 0.055) / 1.055) ** 2.4

        return (
            0.2126 * linear(color.red())
            + 0.7152 * linear(color.green())
            + 0.0722 * linear(color.blue())
        )

    lighter = max(luminance(first), luminance(second))
    darker = min(luminance(first), luminance(second))
    return (lighter + 0.05) / (darker + 0.05)


def _assert_labels_do_not_overlap(widget: PianoRollWidget) -> None:
    ordered = sorted(widget.pitch_labels, key=lambda label: label.rect.top())
    for upper, lower in pairwise(ordered):
        assert upper.rect.bottom() <= lower.rect.top()


def test_pitch_names_and_labels_match_their_note_rows() -> None:
    application = _application()
    widget = PianoRollWidget()
    widget.resize(760, 320)
    widget.set_clips(_clip(60, 61, 62), None)
    widget.show()
    application.processEvents()

    labels = {label.pitch: label for label in widget.pitch_labels}
    assert midi_pitch_name(60) == "C4"
    assert midi_pitch_name(61) == "C#4"
    assert midi_pitch_name(62) == "D4"
    assert [labels[pitch].text for pitch in (60, 61, 62)] == ["C4", "C#4", "D4"]
    assert labels[60].emphasized
    assert not labels[61].emphasized
    assert not labels[62].emphasized
    assert widget.pitch_label_area_width >= 64.0

    metrics = QFontMetricsF(widget.font())
    viewport = QRectF(widget.rect())
    for pitch, label in labels.items():
        row = widget.pitch_row_rect(pitch)
        assert row is not None
        assert label.rect.center().y() == pytest.approx(row.center().y())
        assert label.rect.right() < widget.pitch_content_rect.left()
        assert viewport.contains(label.rect)
        assert label.rect.height() >= 14.0
        assert metrics.horizontalAdvance(label.text) < label.rect.width()
    _assert_labels_do_not_overlap(widget)
    assert not widget.grab().toImage().isNull()
    widget.close()


def test_dense_pitch_ranges_select_octave_landmarks_without_overlap() -> None:
    application = _application()
    widget = PianoRollWidget()
    widget.resize(640, 260)
    widget.set_clips(_clip(0, 127), None)
    widget.show()
    application.processEvents()

    labels = widget.pitch_labels
    assert {label.pitch for label in labels} == set(range(0, 121, 12))
    assert all(label.emphasized for label in labels)
    assert all(label.text.startswith("C") for label in labels)
    assert all(QRectF(widget.rect()).contains(label.rect) for label in labels)
    _assert_labels_do_not_overlap(widget)
    widget.close()


def test_pitch_labels_remain_aligned_after_resize_and_parent_scrolling() -> None:
    application = _application()
    widget = PianoRollWidget()
    widget.resize(760, 500)
    widget.setMinimumSize(760, 500)
    widget.set_clips(_clip(48, 60, 61, 62, 72, 84), None)

    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(False)
    scroll_area.setWidget(widget)
    scroll_area.resize(620, 260)
    scroll_area.show()
    application.processEvents()

    widget.resize(900, 540)
    application.processEvents()
    labels = {label.pitch: label for label in widget.pitch_labels}
    for pitch, label in labels.items():
        row = widget.pitch_row_rect(pitch)
        assert row is not None
        assert label.rect.center().y() == pytest.approx(row.center().y())
    assert all(label.rect.width() == 58.0 for label in labels.values())

    target = labels[60]
    target_scroll = round(target.rect.center().y() - scroll_area.viewport().height() / 2)
    scroll_area.verticalScrollBar().setValue(target_scroll)
    application.processEvents()
    mapped_label_center = widget.mapTo(
        scroll_area.viewport(),
        QPoint(round(target.rect.center().x()), round(target.rect.center().y())),
    )
    row = widget.pitch_row_rect(60)
    assert row is not None
    mapped_row_center = widget.mapTo(
        scroll_area.viewport(),
        QPoint(round(row.center().x()), round(row.center().y())),
    )
    assert mapped_label_center.y() == mapped_row_center.y()
    assert 0 <= mapped_label_center.y() <= scroll_area.viewport().height()
    assert not scroll_area.viewport().grab().toImage().isNull()
    scroll_area.close()


@pytest.mark.parametrize(
    ("background", "text"),
    [
        (QColor(250, 250, 250), QColor(35, 35, 35)),
        (QColor(30, 32, 35), QColor(238, 240, 243)),
    ],
)
def test_pitch_labels_keep_readable_contrast_for_light_and_dark_palettes(
    background: QColor,
    text: QColor,
) -> None:
    application = _application()
    widget = PianoRollWidget()
    palette = QPalette(widget.palette())
    palette.setColor(QPalette.ColorRole.Base, background)
    palette.setColor(QPalette.ColorRole.Text, text)
    widget.setPalette(palette)
    widget.resize(760, 320)
    widget.set_clips(_clip(60, 61, 62), None)
    widget.show()
    application.processEvents()

    assert _contrast_ratio(widget.pitch_label_color, widget.pitch_background_color) >= 4.5
    assert not widget.grab().toImage().isNull()
    widget.close()


@pytest.mark.parametrize("pitch", [-1, 128])
def test_pitch_name_rejects_values_outside_midi_range(pitch: int) -> None:
    with pytest.raises(ValueError, match="between 0 and 127"):
        midi_pitch_name(pitch)
