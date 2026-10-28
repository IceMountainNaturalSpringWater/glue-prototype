"""Compact shared permissions, alternatives and expandable musical rationale."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from glue.analysis.musical import analyze_musical
from glue.exporting import RepairExportPaths
from glue.fixes.musical import MusicalCandidate, MusicalRepair
from glue.fixes.musical_config import EditPermissions
from glue.io import MidiDocument
from glue.musical_exporting import (
    calibration_report,
    export_musical_bundle,
    export_musical_candidate,
    export_musical_combined,
)

from .visualizations import midi_pitch_name


class MusicalControls(QWidget):
    """Presentation only: the host owns generation and source invalidation."""

    permissions_changed = Signal()
    candidate_changed = Signal(object)

    def __init__(self, slots: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("musicalControls")
        self.result: MusicalRepair | None = None
        self.documents: tuple[MidiDocument, ...] = ()
        self.checks: list[tuple[QCheckBox, ...]] = []
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 6, 0, 6)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        root.addWidget(QLabel("Allowed edits", self))
        for slot in range(slots):
            row = QHBoxLayout()
            label = chr(65 + slot) if slots == 2 else "clip"
            if slots == 2:
                row.addWidget(QLabel(f"{label}:", self))
            checks = tuple(QCheckBox(name, self) for name in ("Pitch", "Timing", "Duration"))
            for field, check in zip(("pitch", "timing", "duration"), checks, strict=True):
                check.setObjectName(f"{label}{field.title()}Permission")
                check.setChecked(field == "pitch")
                check.toggled.connect(lambda _checked: self.permissions_changed.emit())
                row.addWidget(check)
            checks[1].setToolTip(
                "Explicit opt-in. Bounded beat-based shifts; no full quantization."
            )
            checks[2].setToolTip("Explicit opt-in. Bounded sustain edits; no length normalization.")
            row.addStretch()
            root.addLayout(row)
            self.checks.append(checks)
        self.hint = QLabel("Timing and Duration remain off unless you enable them.", self)
        self.hint.setWordWrap(True)
        self.hint.setMinimumHeight(36)
        root.addWidget(self.hint)
        self.results = QWidget(self)
        layout = QVBoxLayout(self.results)
        layout.setContentsMargins(0, 0, 0, 0)
        self.summary = QLabel(self.results)
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.alternatives = QComboBox(self.results)
        self.alternatives.setObjectName("musicalAlternatives")
        self.alternatives.setMinimumContentsLength(20)
        self.alternatives.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.alternatives.currentIndexChanged.connect(self._select)
        layout.addWidget(self.alternatives)
        self.rationale_toggle = QPushButton("Change inspector", self.results)
        self.rationale_toggle.setCheckable(True)
        self.rationale = QTreeWidget(self.results)
        self.rationale.setHeaderLabels(["Changed note / field", "Before → after / reason"])
        self.rationale.setColumnWidth(0, 125)
        self.rationale.setWordWrap(True)
        self.rationale.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.rationale.setMinimumHeight(140)
        self.rationale.setMaximumHeight(250)
        self.rationale.hide()
        self.rationale_toggle.toggled.connect(self.rationale.setVisible)
        layout.addWidget(self.rationale_toggle)
        layout.addWidget(self.rationale)
        export_row = QHBoxLayout()
        self.export_buttons = []
        for slot in range(slots):
            label = chr(65 + slot) if slots == 2 else "MIDI"
            button = QPushButton(f"Export {label}…", self.results)
            button.clicked.connect(lambda _checked=False, i=slot: self._export_interactive(i))
            export_row.addWidget(button)
            self.export_buttons.append(button)
        layout.addLayout(export_row)
        self.debug_toggle = QPushButton("Advanced exports / musical evidence", self.results)
        self.debug_toggle.setCheckable(True)
        layout.addWidget(self.debug_toggle)
        self.debug_panel = QWidget(self.results)
        debug_layout = QVBoxLayout(self.debug_panel)
        self.debug_text = QTextEdit(self.debug_panel)
        self.debug_text.setReadOnly(True)
        self.debug_text.setMaximumHeight(220)
        debug_layout.addWidget(self.debug_text)
        self.export_report_button = QPushButton(
            "Export calibration / change report…", self.debug_panel
        )
        self.export_report_button.clicked.connect(lambda: self._export_interactive(0, report=True))
        debug_layout.addWidget(self.export_report_button)
        if slots == 2:
            combined = QPushButton("Export combined preview…", self.debug_panel)
            combined.setToolTip(
                "Keeps original tracks and channels. MIDI channel state may be shared."
            )
            combined.clicked.connect(lambda: self._export_interactive(0, combined=True))
            bundle = QPushButton("Export all four artifacts…", self.debug_panel)
            bundle.clicked.connect(lambda: self._export_interactive(0, bundle=True))
            debug_layout.addWidget(combined)
            debug_layout.addWidget(bundle)
            self.export_buttons.extend((combined, bundle))
        self.debug_panel.hide()
        self.debug_toggle.toggled.connect(self.debug_panel.setVisible)
        layout.addWidget(self.debug_panel)
        root.addWidget(self.results)
        self.clear()

    @property
    def permissions(self) -> tuple[EditPermissions, ...]:
        return tuple(EditPermissions(*(check.isChecked() for check in row)) for row in self.checks)

    @property
    def candidate(self) -> MusicalCandidate | None:
        index = self.alternatives.currentIndex()
        return self.result.candidates[index] if self.result and index >= 0 else None

    def clear(self) -> None:
        self.result = None
        self.documents = ()
        self.alternatives.clear()
        self.rationale.clear()
        self.debug_text.clear()
        self.rationale_toggle.setChecked(False)
        self.debug_toggle.setChecked(False)
        self.results.hide()

    def display(self, result: MusicalRepair, documents: tuple[MidiDocument, ...]) -> None:
        self.clear()
        self.result, self.documents = result, documents
        self.results.show()
        for candidate in result.candidates:
            pitch, timing, duration = candidate.counts
            self.alternatives.addItem(
                f"{candidate.description} · {candidate.score.estimate:.1f} · "
                f"P {pitch} / T {timing} / D {duration}"
            )
        available = bool(result.candidates)
        self.alternatives.setEnabled(available)
        self.rationale_toggle.setEnabled(available)
        self.export_report_button.setEnabled(available)
        for button in self.export_buttons:
            button.setEnabled(available)
        if not available:
            self.summary.setText(result.stop_reason)
            self.debug_text.setPlainText(json.dumps(dict(result.before.components), indent=2))

    def _select(self, index: int) -> None:
        candidate = self.candidate
        if candidate is None or self.result is None:
            return
        before, after = self.result.before.estimate, candidate.score.estimate
        preservation = ":".join(str(p) for p in self.result.preservation)
        self.summary.setText(
            f"Estimated musical fit: {before:.1f} → {after:.1f} ({after - before:+.1f})\n"
            f"Preservation {preservation}% · {len(candidate.edits)} changed notes. "
            "Heuristic estimate, not a listening verdict."
        )
        self.rationale.clear()
        for edit in candidate.edits:
            clip = self.result.originals[edit.slot]
            ppq = clip.ticks_per_beat
            item = QTreeWidgetItem(
                self.rationale,
                [f"Clip {chr(65 + edit.slot)} · note {edit.note_id}", ", ".join(edit.kinds)],
            )
            for kind, field in (
                ("Pitch", "pitch"),
                ("Timing", "onset_ticks"),
                ("Duration", "duration_ticks"),
            ):
                old, new = getattr(edit.before, field), getattr(edit.after, field)
                if old != new:
                    values = (
                        f"{midi_pitch_name(old)} → {midi_pitch_name(new)}"
                        if kind == "Pitch"
                        else f"{old / ppq:g} → {new / ppq:g} quarter-note beats"
                    )
                    QTreeWidgetItem(item, [kind, values])
            for reason in edit.reasons:
                child = QTreeWidgetItem(item, ["Reason (estimated)", reason])
                child.setToolTip(1, reason)
            item.setExpanded(True)
        report = calibration_report(self.result, candidate)
        report["musical_evidence"] = [
            {
                "phrases": m.phrase_boundaries,
                "motifs": len(m.motifs),
                "syncopation": m.syncopation,
                "harmony": [
                    {
                        "beat": f.start,
                        "label": f.harmony.label,
                        "confidence": round(f.confidence, 3),
                        "tonicization": f.tonicization,
                    }
                    for f in m.frames
                ],
            }
            for m in (analyze_musical(c) for c in candidate.clips)
        ]
        self.debug_text.setPlainText(json.dumps(report, indent=2))
        self.candidate_changed.emit(candidate)

    def export(
        self,
        path: str | Path,
        *,
        slot: int = 0,
        report: bool = False,
        overwrite: bool = False,
        combined: bool = False,
        bundle: bool = False,
    ) -> Path | RepairExportPaths:
        if self.result is None or self.candidate is None:
            raise RuntimeError("Generate and select an improving candidate before exporting")
        if bundle:
            return export_musical_bundle(
                self.result, self.candidate, self.documents, path, overwrite=overwrite
            )
        if combined:
            return export_musical_combined(
                self.result, self.candidate, self.documents, path, overwrite=overwrite
            )
        return export_musical_candidate(
            self.result,
            self.candidate,
            self.documents,
            path,
            slot=slot,
            report=report,
            overwrite=overwrite,
        )

    def _export_interactive(
        self, slot: int, *, report: bool = False, combined: bool = False, bundle: bool = False
    ) -> None:
        suffix = ".json" if report else ".mid"
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export selected repair",
            f"glue_repaired{suffix}",
            "JSON (*.json)" if report else "MIDI (*.mid *.midi)",
        )
        if not filename:
            return
        path = Path(filename)
        if path.suffix.lower() not in ((".json",) if report else (".mid", ".midi")):
            path = path.with_suffix(suffix)
        targets = RepairExportPaths.from_base(path).all_paths if bundle else (path,)
        existing = tuple(p for p in targets if p.exists())
        overwrite = bool(existing)
        if (
            overwrite
            and QMessageBox.question(
                self,
                "Confirm overwrite",
                "Replace these exports?\n" + "\n".join(str(p) for p in existing),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        try:
            self.export(
                path,
                slot=slot,
                report=report,
                overwrite=overwrite,
                combined=combined,
                bundle=bundle,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            QMessageBox.critical(self, "Could not export repair", str(exc))
