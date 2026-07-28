"""Small native-Qt visualizations for MIDI notes and compatibility windows."""

from __future__ import annotations

from PySide6.QtCore import QLineF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from glue.analysis import PairAnalysis, WindowAnalysis
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
    _BEFORE_FILL = QColor(150, 150, 150, 55)
    _BEFORE_EDGE = QColor(100, 100, 100)
    _AFTER_FILL = QColor(55, 175, 95, 190)
    _AFTER_EDGE = QColor(20, 105, 55)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._clip_a: MidiClip | None = None
        self._clip_b: MidiClip | None = None
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
        """Show changed original notes as ghosts and repaired notes as highlights."""

        normalized_slot = repaired_slot.upper()
        if normalized_slot not in {"A", "B"}:
            raise ValueError("repaired_slot must be 'A' or 'B'")
        self._clip_a = clip_a
        self._clip_b = clip_b
        self._comparison_slot = normalized_slot
        self._comparison_clip = repaired_clip
        changed_count = len(self._comparison_note_ids())
        self.setAccessibleDescription(
            f"Before and after comparison for MIDI {normalized_slot}; "
            f"{changed_count} changed note{'s' if changed_count != 1 else ''}."
        )
        self.update()

    @property
    def is_comparing(self) -> bool:
        """Whether a repaired clip is currently compared with its original."""

        return self._comparison_slot is not None and self._comparison_clip is not None

    @property
    def comparison_slot(self) -> str | None:
        """Return the repaired slot currently previewed, if any."""

        return self._comparison_slot

    @property
    def comparison_clip(self) -> MidiClip | None:
        """Return the repaired clip currently previewed, if any."""

        return self._comparison_clip

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint beat and pitch grids followed by both clips' notes."""

        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), self._BACKGROUND)

        notes_a = self._clip_a.notes if self._clip_a is not None else ()
        notes_b = self._clip_b.notes if self._clip_b is not None else ()
        comparison_notes = (
            self._comparison_clip.notes if self._comparison_clip is not None else ()
        )
        pitched_notes = tuple(
            note
            for note in (*notes_a, *notes_b, *comparison_notes)
            if not note.is_percussion
        )
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
            self._clip_end_beat(self._comparison_clip),
            1.0,
        )

        self._paint_pitch_grid(painter, content, low_pitch, high_pitch, pitch_span)
        self._paint_beat_grid(painter, content, max_beat)
        changed_ids = self._comparison_note_ids()
        changed_a = changed_ids if self._comparison_slot == "A" else frozenset()
        changed_b = changed_ids if self._comparison_slot == "B" else frozenset()
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
        original_comparison = (
            self._clip_a if self._comparison_slot == "A" else self._clip_b
        )
        self._paint_clip(
            painter,
            content,
            original_comparison,
            low_pitch,
            pitch_span,
            max_beat,
            self._BEFORE_FILL,
            self._BEFORE_EDGE,
            included_ids=changed_ids,
            pen_style=Qt.PenStyle.DashLine,
        )
        self._paint_clip(
            painter,
            content,
            self._comparison_clip,
            low_pitch,
            pitch_span,
            max_beat,
            self._AFTER_FILL,
            self._AFTER_EDGE,
            included_ids=changed_ids,
        )
        self._paint_legend(painter, comparing=self.is_comparing)

    def _comparison_note_ids(self) -> frozenset[int]:
        if self._comparison_clip is None or self._comparison_slot is None:
            return frozenset()
        original = self._clip_a if self._comparison_slot == "A" else self._clip_b
        if original is None:
            return frozenset()
        original_pitches = {note.id: note.pitch for note in original.notes}
        return frozenset(
            note.id
            for note in self._comparison_clip.notes
            if original_pitches.get(note.id) != note.pitch
        )

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
        *,
        included_ids: frozenset[int] | None = None,
        excluded_ids: frozenset[int] = frozenset(),
        pen_style: Qt.PenStyle = Qt.PenStyle.SolidLine,
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
            painter.setPen(QPen(edge, 1, pen_style))
            painter.drawRect(note_rect)

    def _paint_legend(self, painter: QPainter, *, comparing: bool) -> None:
        painter.fillRect(QRectF(52.0, 5.0, 14.0, 12.0), self._CLIP_A_FILL)
        painter.setPen(self._CLIP_A_EDGE)
        painter.drawText(71, 16, "A")
        painter.fillRect(QRectF(97.0, 5.0, 14.0, 12.0), self._CLIP_B_FILL)
        painter.setPen(self._CLIP_B_EDGE)
        painter.drawText(116, 16, "B")
        if not comparing:
            return
        before_rect = QRectF(142.0, 5.0, 14.0, 12.0)
        painter.fillRect(before_rect, self._BEFORE_FILL)
        painter.setPen(QPen(self._BEFORE_EDGE, 1, Qt.PenStyle.DashLine))
        painter.drawRect(before_rect)
        painter.drawText(161, 16, "Before edit")
        painter.fillRect(QRectF(235.0, 5.0, 14.0, 12.0), self._AFTER_FILL)
        painter.setPen(self._AFTER_EDGE)
        painter.drawText(254, 16, "After edit")


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
