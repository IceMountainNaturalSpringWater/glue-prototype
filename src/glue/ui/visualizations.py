"""Small native-Qt visualizations for MIDI notes and compatibility windows."""

from __future__ import annotations

from PySide6.QtCore import QLineF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from glue.analysis import PairAnalysis
from glue.models import MidiClip


class PianoRollWidget(QWidget):
    """Draw two MIDI clips on one read-only piano-roll timeline."""

    _BACKGROUND = QColor(250, 250, 250)
    _GRID = QColor(220, 220, 220)
    _OCTAVE_GRID = QColor(185, 185, 185)
    _CLIP_A_FILL = QColor(45, 115, 210, 155)
    _CLIP_A_EDGE = QColor(30, 78, 150)
    _CLIP_B_FILL = QColor(235, 135, 40, 155)
    _CLIP_B_EDGE = QColor(175, 85, 10)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._clip_a: MidiClip | None = None
        self._clip_b: MidiClip | None = None
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
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint beat and pitch grids followed by both clips' notes."""

        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), self._BACKGROUND)

        notes_a = self._clip_a.notes if self._clip_a is not None else ()
        notes_b = self._clip_b.notes if self._clip_b is not None else ()
        pitched_notes = tuple(note for note in (*notes_a, *notes_b) if not note.is_percussion)
        if not pitched_notes:
            painter.setPen(QColor(100, 100, 100))
            painter.drawText(
                QRectF(self.rect()),
                Qt.AlignmentFlag.AlignCenter,
                "Load two MIDI files to view their notes.",
            )
            return

        content = QRectF(self.rect()).adjusted(48.0, 25.0, -12.0, -24.0)
        if content.width() <= 1 or content.height() <= 1:
            return

        low_pitch = max(0, min(note.pitch for note in pitched_notes) - 1)
        high_pitch = min(127, max(note.pitch for note in pitched_notes) + 1)
        pitch_span = max(1, high_pitch - low_pitch + 1)
        max_beat = max(
            self._clip_end_beat(self._clip_a),
            self._clip_end_beat(self._clip_b),
            1.0,
        )

        self._paint_pitch_grid(painter, content, low_pitch, high_pitch, pitch_span)
        self._paint_beat_grid(painter, content, max_beat)
        self._paint_clip(
            painter,
            content,
            self._clip_a,
            low_pitch,
            pitch_span,
            max_beat,
            self._CLIP_A_FILL,
            self._CLIP_A_EDGE,
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
        )
        self._paint_legend(painter)

    @staticmethod
    def _clip_end_beat(clip: MidiClip | None) -> float:
        if clip is None:
            return 0.0
        return float(clip.duration_quarter_notes)

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
            painter.setPen(QPen(self._OCTAVE_GRID if is_octave else self._GRID, 1))
            painter.drawLine(QLineF(content.left(), y, content.right(), y))
            if is_octave and low_pitch <= pitch <= high_pitch:
                octave = pitch // 12 - 1
                painter.setPen(QColor(85, 85, 85))
                painter.drawText(
                    QRectF(2.0, y - row_height, 42.0, row_height),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    f"C{octave}",
                )

    def _paint_beat_grid(
        self,
        painter: QPainter,
        content: QRectF,
        max_beat: float,
    ) -> None:
        beat = 0
        while beat <= int(max_beat + 0.999_999):
            x = content.left() + beat / max_beat * content.width()
            painter.setPen(QPen(self._OCTAVE_GRID if beat % 4 == 0 else self._GRID, 1))
            painter.drawLine(QLineF(x, content.top(), x, content.bottom()))
            painter.setPen(QColor(85, 85, 85))
            painter.drawText(
                QRectF(x + 2.0, content.bottom() + 2.0, 38.0, 18.0),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                str(beat + 1),
            )
            beat += 1

    @staticmethod
    def _paint_clip(
        painter: QPainter,
        content: QRectF,
        clip: MidiClip | None,
        low_pitch: int,
        pitch_span: int,
        max_beat: float,
        fill: QColor,
        edge: QColor,
    ) -> None:
        if clip is None:
            return
        row_height = content.height() / pitch_span
        for note in clip.notes:
            if note.is_percussion:
                continue
            onset = note.onset_ticks / clip.ticks_per_beat
            duration = note.duration_ticks / clip.ticks_per_beat
            x = content.left() + onset / max_beat * content.width()
            width = max(2.0, duration / max_beat * content.width())
            y = content.bottom() - (note.pitch - low_pitch + 1) * row_height
            note_rect = QRectF(x, y + 0.5, width, max(2.0, row_height - 1.0))
            painter.fillRect(note_rect, fill)
            painter.setPen(QPen(edge, 1))
            painter.drawRect(note_rect)

    def _paint_legend(self, painter: QPainter) -> None:
        painter.fillRect(QRectF(52.0, 5.0, 14.0, 12.0), self._CLIP_A_FILL)
        painter.setPen(self._CLIP_A_EDGE)
        painter.drawText(71, 16, "A")
        painter.fillRect(QRectF(97.0, 5.0, 14.0, 12.0), self._CLIP_B_FILL)
        painter.setPen(self._CLIP_B_EDGE)
        painter.drawText(116, 16, "B")


class CompatibilityTimelineWidget(QWidget):
    """Draw per-window compatibility as a compact colored timeline."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._analysis: PairAnalysis | None = None
        self.setMinimumHeight(105)
        self.setAccessibleName("Per-window compatibility timeline")

    def sizeHint(self) -> QSize:
        """Return a useful initial timeline size."""

        return QSize(760, 125)

    def set_analysis(self, analysis: PairAnalysis | None) -> None:
        """Replace the pair analysis shown by the timeline."""

        self._analysis = analysis
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint a colored cell for every analysis window."""

        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), QColor(250, 250, 250))

        windows = self._analysis.windows if self._analysis is not None else ()
        if not windows:
            painter.setPen(QColor(100, 100, 100))
            painter.drawText(
                QRectF(self.rect()),
                Qt.AlignmentFlag.AlignCenter,
                "Analyze two clips to view compatibility by beat.",
            )
            return

        content = QRectF(self.rect()).adjusted(12.0, 22.0, -12.0, -25.0)
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

            if cell_width >= 45:
                painter.setPen(QColor(75, 75, 75))
                painter.drawText(
                    QRectF(left + 2.0, content.bottom() + 2.0, cell_width - 4.0, 18.0),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    f"{window.start_beat + 1:g}",
                )

        painter.setPen(QColor(75, 75, 75))
        painter.drawText(
            QRectF(content.left(), 1.0, content.width(), 18.0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "Compatibility per beat (red = more conflict, green = less detected conflict)",
        )

    @staticmethod
    def _score_color(score: float) -> QColor:
        hue = round(max(0.0, min(100.0, score)) * 1.2)
        return QColor.fromHsv(hue, 165, 225)
