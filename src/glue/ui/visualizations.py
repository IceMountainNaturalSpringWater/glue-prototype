"""Small native-Qt visualizations for MIDI notes and compatibility windows."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from PySide6.QtCore import QLineF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetricsF,
    QPainter,
    QPaintEvent,
    QPalette,
    QPen,
)
from PySide6.QtWidgets import QWidget

from glue.analysis import PairAnalysis, WindowAnalysis
from glue.models import MidiClip, MidiNote

_PITCH_CLASS_NAMES = (
    "C",
    "C#",
    "D",
    "D#",
    "E",
    "F",
    "F#",
    "G",
    "G#",
    "A",
    "A#",
    "B",
)


def midi_pitch_name(pitch: int) -> str:
    """Return a scientific-pitch name for a MIDI note number."""

    if not 0 <= pitch <= 127:
        raise ValueError("MIDI pitch must be between 0 and 127")
    return f"{_PITCH_CLASS_NAMES[pitch % 12]}{pitch // 12 - 1}"


@dataclass(frozen=True, slots=True)
class PitchLabelLayout:
    """A deterministic pitch label and its painted rectangle."""

    pitch: int
    text: str
    rect: QRectF
    emphasized: bool


class PianoRollWidget(QWidget):
    """Draw two MIDI clips on one read-only piano-roll timeline."""

    _BACKGROUND = QColor(250, 250, 250)
    _GRID = QColor(220, 220, 220)
    _OCTAVE_GRID = QColor(185, 185, 185)
    _CLIP_A_FILL = QColor(45, 115, 210, 155)
    _CLIP_A_EDGE = QColor(30, 78, 150)
    _CLIP_B_FILL = QColor(235, 135, 40, 155)
    _CLIP_B_EDGE = QColor(175, 85, 10)
    _CLIP_A_BEFORE_FILL = QColor(45, 115, 210, 45)
    _CLIP_A_AFTER_FILL = QColor(35, 155, 245, 220)
    _CLIP_A_AFTER_EDGE = QColor(5, 75, 155)
    _CLIP_B_BEFORE_FILL = QColor(235, 135, 40, 45)
    _CLIP_B_AFTER_FILL = QColor(250, 105, 35, 220)
    _CLIP_B_AFTER_EDGE = QColor(155, 45, 5)
    _PITCH_GUTTER_WIDTH = 72.0
    _PITCH_LABEL_LEFT = 4.0
    _PITCH_LABEL_WIDTH = 58.0
    _TOP_MARGIN = 25.0
    _RIGHT_MARGIN = 12.0
    _BOTTOM_MARGIN = 24.0

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._clip_a: MidiClip | None = None
        self._clip_b: MidiClip | None = None
        self._comparison_clip_a: MidiClip | None = None
        self._comparison_clip_b: MidiClip | None = None
        self._pair_comparison_active = False
        # These two fields retain the V0.2 one-sided comparison API.  For a
        # dual-edit comparison there is deliberately no single repaired slot.
        self._comparison_slot: str | None = None
        self._comparison_clip: MidiClip | None = None
        self.setMinimumHeight(260)
        self.setAccessibleName("Overlay piano roll")

    def sizeHint(self) -> QSize:
        """Return a useful initial canvas size."""

        return QSize(760, 320)

    def set_clips(
        self,
        clip_a: MidiClip | None,
        clip_b: MidiClip | None,
    ) -> None:
        """Replace the clips shown by the piano roll."""

        self._clip_a = clip_a
        self._clip_b = clip_b
        self._comparison_clip_a = None
        self._comparison_clip_b = None
        self._pair_comparison_active = False
        self._comparison_slot = None
        self._comparison_clip = None
        self.setAccessibleDescription("Original MIDI A and MIDI B notes.")
        self.update()

    def set_comparison(
        self,
        clip_a: MidiClip,
        clip_b: MidiClip,
        repaired_slot: str,
        repaired_clip: MidiClip,
    ) -> None:
        """Show a V0.2-compatible one-sided before/after comparison."""

        normalized_slot = repaired_slot.upper()
        if normalized_slot not in {"A", "B"}:
            raise ValueError("repaired_slot must be 'A' or 'B'")
        repaired_a = repaired_clip if normalized_slot == "A" else clip_a
        repaired_b = repaired_clip if normalized_slot == "B" else clip_b
        self.set_pair_comparison(clip_a, clip_b, repaired_a, repaired_b)
        # Preserve the legacy slot/clip properties even for an unchanged
        # candidate, when change-set inference alone would be ambiguous.
        self._comparison_slot = normalized_slot
        self._comparison_clip = repaired_clip
        self.setAccessibleDescription(
            f"Before and after comparison for MIDI {normalized_slot}; "
            f"{len(self._comparison_note_ids())} changed "
            f"note{'s' if len(self._comparison_note_ids()) != 1 else ''}."
        )
        self.update()

    def set_pair_comparison(
        self,
        original_a: MidiClip,
        original_b: MidiClip,
        repaired_a: MidiClip,
        repaired_b: MidiClip,
    ) -> None:
        """Show independent pitch changes to MIDI A and MIDI B.

        The widget only compares stable note identifiers and pitches.  Repair
        eligibility and musical scoring remain responsibilities of the repair
        and analysis layers.
        """

        self._clip_a = original_a
        self._clip_b = original_b
        self._comparison_clip_a = repaired_a
        self._comparison_clip_b = repaired_b
        self._pair_comparison_active = True

        changed_a = self.changed_note_ids_a
        changed_b = self.changed_note_ids_b
        if changed_a and not changed_b:
            self._comparison_slot = "A"
            self._comparison_clip = repaired_a
        elif changed_b and not changed_a:
            self._comparison_slot = "B"
            self._comparison_clip = repaired_b
        else:
            self._comparison_slot = None
            self._comparison_clip = None

        count_a = len(changed_a)
        count_b = len(changed_b)
        self.setAccessibleDescription(
            "Before and after comparison; "
            f"MIDI A has {count_a} changed note{'s' if count_a != 1 else ''}; "
            f"MIDI B has {count_b} changed note{'s' if count_b != 1 else ''}."
        )
        self.update()

    @property
    def is_comparing(self) -> bool:
        """Whether repaired clips are currently compared with their originals."""

        return self._pair_comparison_active

    @property
    def comparison_slot(self) -> str | None:
        """Return the repaired slot currently previewed, if any."""

        return self._comparison_slot

    @property
    def comparison_clip(self) -> MidiClip | None:
        """Return the sole repaired clip for a one-sided comparison, if any."""

        return self._comparison_clip

    @property
    def comparison_clip_a(self) -> MidiClip | None:
        """Return revised MIDI A while a pair comparison is active."""

        return self._comparison_clip_a

    @property
    def comparison_clip_b(self) -> MidiClip | None:
        """Return revised MIDI B while a pair comparison is active."""

        return self._comparison_clip_b

    @property
    def changed_note_ids_a(self) -> frozenset[int]:
        """Return stable MIDI A note identifiers whose pitches changed."""

        return self._changed_note_ids(self._clip_a, self._comparison_clip_a)

    @property
    def changed_note_ids_b(self) -> frozenset[int]:
        """Return stable MIDI B note identifiers whose pitches changed."""

        return self._changed_note_ids(self._clip_b, self._comparison_clip_b)

    @property
    def pitch_label_area_width(self) -> float:
        """Return the fixed width reserved for readable pitch names."""

        return self._PITCH_GUTTER_WIDTH

    @property
    def pitch_content_rect(self) -> QRectF:
        """Return the note-grid rectangle for the current widget size."""

        return self._content_rect()

    @property
    def pitch_label_area_rect(self) -> QRectF:
        """Return the fixed label area next to the note grid."""

        content = self._content_rect()
        return QRectF(
            self._PITCH_LABEL_LEFT,
            content.top(),
            self._PITCH_LABEL_WIDTH,
            content.height(),
        )

    @property
    def pitch_labels(self) -> tuple[PitchLabelLayout, ...]:
        """Return labels that will be painted at the current size."""

        bounds = self._pitch_bounds()
        if bounds is None:
            return ()
        low_pitch, high_pitch, pitch_span = bounds
        return self._layout_pitch_labels(
            self._content_rect(),
            low_pitch,
            high_pitch,
            pitch_span,
        )

    @property
    def pitch_background_color(self) -> QColor:
        """Return the palette-aware piano-roll background color."""

        color = self.palette().color(QPalette.ColorRole.Base)
        return color if color.isValid() else QColor(self._BACKGROUND)

    @property
    def pitch_label_color(self) -> QColor:
        """Return a readable label color for the current palette."""

        background = self.pitch_background_color
        preferred = self.palette().color(QPalette.ColorRole.Text)
        if preferred.isValid() and self._contrast_ratio(preferred, background) >= 4.5:
            return preferred
        black = QColor(20, 20, 20)
        white = QColor(245, 245, 245)
        return max(
            (black, white),
            key=lambda color: self._contrast_ratio(color, background),
        )

    def pitch_row_rect(self, pitch: int) -> QRectF | None:
        """Return the painted note row for ``pitch``, if currently visible."""

        bounds = self._pitch_bounds()
        if bounds is None:
            return None
        low_pitch, high_pitch, pitch_span = bounds
        if not low_pitch <= pitch <= high_pitch:
            return None
        content = self._content_rect()
        row_height = content.height() / pitch_span
        top = content.bottom() - (pitch - low_pitch + 1) * row_height
        return QRectF(content.left(), top, content.width(), row_height)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint beat and pitch grids followed by both clips' notes."""

        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), self.pitch_background_color)

        pitched_notes = self._pitched_notes()
        if not pitched_notes:
            painter.setPen(self.pitch_label_color)
            painter.drawText(
                QRectF(self.rect()),
                Qt.AlignmentFlag.AlignCenter,
                "Load two MIDI files to view their notes.",
            )
            return

        content = self._content_rect()
        if content.width() <= 1 or content.height() <= 1:
            return

        bounds = self._pitch_bounds()
        if bounds is None:
            return
        low_pitch, high_pitch, pitch_span = bounds
        max_beat = max(
            self._clip_end_beat(self._clip_a),
            self._clip_end_beat(self._clip_b),
            self._clip_end_beat(self._comparison_clip_a),
            self._clip_end_beat(self._comparison_clip_b),
            1.0,
        )

        self._paint_pitch_grid(painter, content, low_pitch, high_pitch, pitch_span)
        self._paint_beat_grid(painter, content, max_beat)
        changed_a = self.changed_note_ids_a
        changed_b = self.changed_note_ids_b
        self._paint_clip(
            painter,
            content,
            self._clip_a,
            low_pitch,
            pitch_span,
            max_beat,
            self._CLIP_A_FILL,
            self._CLIP_A_EDGE,
            excluded_ids=changed_a,
        )
        self._paint_clip(
            painter,
            content,
            self._clip_b,
            low_pitch,
            pitch_span,
            max_beat,
            self._CLIP_B_FILL,
            self._CLIP_B_EDGE,
            excluded_ids=changed_b,
        )
        self._paint_clip(
            painter,
            content,
            self._clip_a,
            low_pitch,
            pitch_span,
            max_beat,
            self._CLIP_A_BEFORE_FILL,
            self._CLIP_A_EDGE,
            included_ids=changed_a,
            pen_style=Qt.PenStyle.DashLine,
        )
        self._paint_clip(
            painter,
            content,
            self._clip_b,
            low_pitch,
            pitch_span,
            max_beat,
            self._CLIP_B_BEFORE_FILL,
            self._CLIP_B_EDGE,
            included_ids=changed_b,
            pen_style=Qt.PenStyle.DashLine,
        )
        self._paint_clip(
            painter,
            content,
            self._comparison_clip_a,
            low_pitch,
            pitch_span,
            max_beat,
            self._CLIP_A_AFTER_FILL,
            self._CLIP_A_AFTER_EDGE,
            included_ids=changed_a,
            pen_width=2,
        )
        # The patterned B fill keeps both revised lines visible when they
        # occupy exactly the same pitch and time rectangle.
        self._paint_clip(
            painter,
            content,
            self._comparison_clip_b,
            low_pitch,
            pitch_span,
            max_beat,
            QBrush(self._CLIP_B_AFTER_FILL, Qt.BrushStyle.Dense4Pattern),
            self._CLIP_B_AFTER_EDGE,
            included_ids=changed_b,
            pen_width=2,
        )
        self._paint_legend(painter, comparing=self.is_comparing)

    def _comparison_note_ids(self) -> frozenset[int]:
        if self._comparison_slot == "A":
            return self.changed_note_ids_a
        if self._comparison_slot == "B":
            return self.changed_note_ids_b
        return frozenset()

    @staticmethod
    def _changed_note_ids(
        original: MidiClip | None,
        repaired: MidiClip | None,
    ) -> frozenset[int]:
        if original is None or repaired is None:
            return frozenset()
        original_pitches = {note.id: note.pitch for note in original.notes}
        repaired_pitches = {note.id: note.pitch for note in repaired.notes}
        all_note_ids = original_pitches.keys() | repaired_pitches.keys()
        return frozenset(
            note_id
            for note_id in all_note_ids
            if original_pitches.get(note_id) != repaired_pitches.get(note_id)
        )

    @staticmethod
    def _clip_end_beat(clip: MidiClip | None) -> float:
        if clip is None:
            return 0.0
        return float(clip.duration_quarter_notes)

    def _pitched_notes(self) -> tuple[MidiNote, ...]:
        clips = (
            self._clip_a,
            self._clip_b,
            self._comparison_clip_a,
            self._comparison_clip_b,
        )
        return tuple(
            note
            for clip in clips
            if clip is not None
            for note in clip.notes
            if not note.is_percussion
        )

    def _pitch_bounds(self) -> tuple[int, int, int] | None:
        pitched_notes = self._pitched_notes()
        if not pitched_notes:
            return None
        low_pitch = max(0, min(note.pitch for note in pitched_notes) - 1)
        high_pitch = min(127, max(note.pitch for note in pitched_notes) + 1)
        return low_pitch, high_pitch, max(1, high_pitch - low_pitch + 1)

    def _content_rect(self) -> QRectF:
        return QRectF(self.rect()).adjusted(
            self._PITCH_GUTTER_WIDTH,
            self._TOP_MARGIN,
            -self._RIGHT_MARGIN,
            -self._BOTTOM_MARGIN,
        )

    def _pitch_label_font(self, *, emphasized: bool) -> QFont:
        font = QFont(self.font())
        if font.pointSizeF() > 0:
            font.setPointSizeF(max(8.5, font.pointSizeF()))
        elif font.pixelSize() > 0:
            font.setPixelSize(max(12, font.pixelSize()))
        font.setBold(emphasized)
        return font

    def _layout_pitch_labels(
        self,
        content: QRectF,
        low_pitch: int,
        high_pitch: int,
        pitch_span: int,
    ) -> tuple[PitchLabelLayout, ...]:
        row_height = content.height() / pitch_span
        normal_metrics = QFontMetricsF(self._pitch_label_font(emphasized=False))
        bold_metrics = QFontMetricsF(self._pitch_label_font(emphasized=True))
        label_height = float(ceil(max(normal_metrics.height(), bold_metrics.height())) + 2)

        if row_height >= label_height + 1.0:
            pitch_classes = frozenset(range(12))
        elif row_height * 2.0 >= label_height + 1.0:
            # Natural-note landmarks with at least one blank row between most
            # labels remain useful when every semitone would overlap.
            pitch_classes = frozenset({0, 2, 4, 7, 9})
        else:
            pitch_classes = frozenset({0})

        labels: list[PitchLabelLayout] = []
        for pitch in range(low_pitch, high_pitch + 1):
            if pitch % 12 not in pitch_classes:
                continue
            row_center = content.bottom() - (pitch - low_pitch + 0.5) * row_height
            rect = QRectF(
                self._PITCH_LABEL_LEFT,
                row_center - label_height / 2.0,
                self._PITCH_LABEL_WIDTH,
                label_height,
            )
            # Header/footer margins are normally enough for edge pitches.  If
            # a custom font exceeds them, omitting the clipped landmark is
            # preferable to drawing unreadable text outside the viewport.
            if rect.top() < 0.0 or rect.bottom() > self.height():
                continue
            labels.append(
                PitchLabelLayout(
                    pitch=pitch,
                    text=midi_pitch_name(pitch),
                    rect=rect,
                    emphasized=pitch % 12 == 0,
                )
            )
        return tuple(labels)

    def _paint_pitch_grid(
        self,
        painter: QPainter,
        content: QRectF,
        low_pitch: int,
        high_pitch: int,
        pitch_span: int,
    ) -> None:
        row_height = content.height() / pitch_span
        for pitch in range(low_pitch, high_pitch + 2):
            y = content.bottom() - (pitch - low_pitch) * row_height
            is_octave = pitch % 12 == 0
            grid_color = self._palette_mix(0.28 if is_octave else 0.14)
            painter.setPen(QPen(grid_color, 1))
            painter.drawLine(QLineF(content.left(), y, content.right(), y))
        painter.setPen(QPen(self._palette_mix(0.38), 1))
        painter.drawLine(
            QLineF(content.left(), content.top(), content.left(), content.bottom())
        )
        painter.save()
        for label in self._layout_pitch_labels(
            content,
            low_pitch,
            high_pitch,
            pitch_span,
        ):
            painter.setFont(self._pitch_label_font(emphasized=label.emphasized))
            painter.setPen(self.pitch_label_color)
            painter.drawText(
                label.rect,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                label.text,
            )
        painter.restore()

    def _paint_beat_grid(
        self,
        painter: QPainter,
        content: QRectF,
        max_beat: float,
    ) -> None:
        beat = 0
        while beat <= int(max_beat + 0.999_999):
            x = content.left() + beat / max_beat * content.width()
            painter.setPen(QPen(self._palette_mix(0.28 if beat % 4 == 0 else 0.14), 1))
            painter.drawLine(QLineF(x, content.top(), x, content.bottom()))
            painter.setPen(self.pitch_label_color)
            painter.drawText(
                QRectF(x + 2.0, content.bottom() + 2.0, 38.0, 18.0),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                str(beat + 1),
            )
            beat += 1

    def _palette_mix(self, foreground_fraction: float) -> QColor:
        background = self.pitch_background_color
        foreground = self.pitch_label_color
        fraction = max(0.0, min(1.0, foreground_fraction))
        return QColor(
            round(background.red() * (1.0 - fraction) + foreground.red() * fraction),
            round(background.green() * (1.0 - fraction) + foreground.green() * fraction),
            round(background.blue() * (1.0 - fraction) + foreground.blue() * fraction),
        )

    @classmethod
    def _contrast_ratio(cls, first: QColor, second: QColor) -> float:
        lighter = max(cls._relative_luminance(first), cls._relative_luminance(second))
        darker = min(cls._relative_luminance(first), cls._relative_luminance(second))
        return (lighter + 0.05) / (darker + 0.05)

    @staticmethod
    def _relative_luminance(color: QColor) -> float:
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

    @staticmethod
    def _paint_clip(
        painter: QPainter,
        content: QRectF,
        clip: MidiClip | None,
        low_pitch: int,
        pitch_span: int,
        max_beat: float,
        fill: QColor | QBrush,
        edge: QColor,
        *,
        included_ids: frozenset[int] | None = None,
        excluded_ids: frozenset[int] = frozenset(),
        pen_style: Qt.PenStyle = Qt.PenStyle.SolidLine,
        pen_width: int = 1,
    ) -> None:
        if clip is None:
            return
        row_height = content.height() / pitch_span
        for note in clip.notes:
            if (
                note.is_percussion
                or note.id in excluded_ids
                or (included_ids is not None and note.id not in included_ids)
            ):
                continue
            onset = note.onset_ticks / clip.ticks_per_beat
            duration = note.duration_ticks / clip.ticks_per_beat
            x = content.left() + onset / max_beat * content.width()
            width = max(2.0, duration / max_beat * content.width())
            y = content.bottom() - (note.pitch - low_pitch + 1) * row_height
            note_rect = QRectF(x, y + 0.5, width, max(2.0, row_height - 1.0))
            painter.fillRect(note_rect, fill)
            painter.setPen(QPen(edge, pen_width, pen_style))
            painter.drawRect(note_rect)

    def _paint_legend(self, painter: QPainter, *, comparing: bool) -> None:
        self._paint_legend_item(
            painter,
            52.0,
            "A",
            self._CLIP_A_FILL,
            self._CLIP_A_EDGE,
        )
        self._paint_legend_item(
            painter,
            97.0,
            "B",
            self._CLIP_B_FILL,
            self._CLIP_B_EDGE,
        )
        if not comparing:
            return
        self._paint_legend_item(
            painter,
            142.0,
            "A old",
            self._CLIP_A_BEFORE_FILL,
            self._CLIP_A_EDGE,
            pen_style=Qt.PenStyle.DashLine,
        )
        self._paint_legend_item(
            painter,
            218.0,
            "A revised",
            self._CLIP_A_AFTER_FILL,
            self._CLIP_A_AFTER_EDGE,
        )
        self._paint_legend_item(
            painter,
            310.0,
            "B old",
            self._CLIP_B_BEFORE_FILL,
            self._CLIP_B_EDGE,
            pen_style=Qt.PenStyle.DashLine,
        )
        self._paint_legend_item(
            painter,
            386.0,
            "B revised",
            QBrush(self._CLIP_B_AFTER_FILL, Qt.BrushStyle.Dense4Pattern),
            self._CLIP_B_AFTER_EDGE,
        )

    @staticmethod
    def _paint_legend_item(
        painter: QPainter,
        x: float,
        label: str,
        fill: QColor | QBrush,
        edge: QColor,
        *,
        pen_style: Qt.PenStyle = Qt.PenStyle.SolidLine,
    ) -> None:
        swatch = QRectF(x, 5.0, 14.0, 12.0)
        painter.fillRect(swatch, fill)
        painter.setPen(QPen(edge, 1, pen_style))
        painter.drawRect(swatch)
        painter.drawText(
            QRectF(x + 19.0, 1.0, 72.0, 18.0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            label,
        )


class CompatibilityTimelineWidget(QWidget):
    """Draw per-window compatibility as a compact colored timeline."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._analysis: PairAnalysis | None = None
        self._comparison_analysis: PairAnalysis | None = None
        self.setMinimumHeight(125)
        self.setAccessibleName("Per-window compatibility timeline")

    def sizeHint(self) -> QSize:
        """Return a useful initial timeline size."""

        return QSize(760, 145)

    def set_analysis(self, analysis: PairAnalysis | None) -> None:
        """Replace the pair analysis shown by the timeline."""

        self._analysis = analysis
        self._comparison_analysis = None
        self.setAccessibleDescription("Compatibility for the original clip pair.")
        self.update()

    def set_comparison(
        self,
        before: PairAnalysis,
        after: PairAnalysis,
    ) -> None:
        """Show aligned before and after compatibility rows."""

        self._analysis = before
        self._comparison_analysis = after
        self.setAccessibleDescription(
            f"Compatibility before {before.overall_score:.1f} and "
            f"after {after.overall_score:.1f}."
        )
        self.update()

    @property
    def before_analysis(self) -> PairAnalysis | None:
        """Return the original analysis currently displayed."""

        return self._analysis

    @property
    def after_analysis(self) -> PairAnalysis | None:
        """Return the repaired analysis currently displayed, if any."""

        return self._comparison_analysis

    @property
    def is_comparing(self) -> bool:
        """Whether both before and after analyses are displayed."""

        return self._analysis is not None and self._comparison_analysis is not None

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint a colored cell for every analysis window."""

        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), QColor(250, 250, 250))

        before_windows = self._analysis.windows if self._analysis is not None else ()
        after_windows = (
            self._comparison_analysis.windows
            if self._comparison_analysis is not None
            else ()
        )
        if not before_windows and not after_windows:
            painter.setPen(QColor(100, 100, 100))
            painter.drawText(
                QRectF(self.rect()),
                Qt.AlignmentFlag.AlignCenter,
                "Analyze two clips to view compatibility by beat.",
            )
            return

        comparing = self._comparison_analysis is not None
        left_margin = 62.0 if comparing else 12.0
        content = QRectF(self.rect()).adjusted(left_margin, 22.0, -12.0, -25.0)
        if comparing:
            gap = 5.0
            row_height = max(1.0, (content.height() - gap) / 2.0)
            before_rect = QRectF(
                content.left(),
                content.top(),
                content.width(),
                row_height,
            )
            after_rect = QRectF(
                content.left(),
                before_rect.bottom() + gap,
                content.width(),
                row_height,
            )
            self._paint_row(
                painter,
                before_rect,
                before_windows,
                show_beats=False,
            )
            self._paint_row(
                painter,
                after_rect,
                after_windows,
                show_beats=True,
            )
            painter.setPen(QColor(65, 65, 65))
            painter.drawText(
                QRectF(4.0, before_rect.top(), 54.0, before_rect.height()),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                "Before",
            )
            painter.drawText(
                QRectF(4.0, after_rect.top(), 54.0, after_rect.height()),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                "After",
            )
        else:
            self._paint_row(
                painter,
                content,
                before_windows,
                show_beats=True,
            )

        painter.setPen(QColor(75, 75, 75))
        painter.drawText(
            QRectF(content.left(), 1.0, content.width(), 18.0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "Compatibility per beat (red = more conflict, green = less detected conflict)",
        )

    def _paint_row(
        self,
        painter: QPainter,
        content: QRectF,
        windows: tuple[WindowAnalysis, ...],
        *,
        show_beats: bool,
    ) -> None:
        if not windows:
            painter.fillRect(content, QColor(235, 235, 235))
            return
        cell_width = content.width() / len(windows)
        previous_bar = windows[0].bar_index
        for position, window in enumerate(windows):
            left = content.left() + position * cell_width
            right = content.left() + (position + 1) * cell_width
            cell = QRectF(left, content.top(), max(1.0, right - left), content.height())
            color = (
                QColor(210, 210, 210)
                if window.activity_weight <= 0
                else self._score_color(window.overall_score)
            )
            painter.fillRect(cell, color)
            painter.setPen(QPen(QColor(255, 255, 255, 180), 1))
            painter.drawRect(cell)

            if cell_width >= 35:
                painter.setPen(QColor(25, 25, 25))
                painter.drawText(
                    cell,
                    Qt.AlignmentFlag.AlignCenter,
                    f"{window.overall_score:.0f}",
                )
            if position and window.bar_index != previous_bar:
                painter.setPen(QPen(QColor(45, 45, 45), 2))
                painter.drawLine(QLineF(left, content.top(), left, content.bottom()))
            previous_bar = window.bar_index

            if show_beats and cell_width >= 45:
                painter.setPen(QColor(75, 75, 75))
                painter.drawText(
                    QRectF(left + 2.0, content.bottom() + 2.0, cell_width - 4.0, 18.0),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    f"{window.start_beat + 1:g}",
                )

    @staticmethod
    def _score_color(score: float) -> QColor:
        hue = round(max(0.0, min(100.0, score)) * 1.2)
        return QColor.fromHsv(hue, 165, 225)
