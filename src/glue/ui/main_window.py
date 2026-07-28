"""Main PySide6 window for the GLUE V0.2 workflow."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeVar, cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from glue.analysis import KeyEstimate, PairAnalysis, analyze_pair, estimate_key
from glue.fixes import (
    MinimalRepairResult,
    NoteEdit,
    RepairPreset,
    generate_minimal_repair,
    generate_repair,
    repair_config_for,
)
from glue.io import (
    MidiDocument,
    load_midi,
    save_midi,
    validate_for_analysis,
)
from glue.models import MidiClip

from .visualizations import CompatibilityTimelineWidget, PianoRollWidget

ClipSlot = Literal["A", "B"]
_ResultT = TypeVar("_ResultT")


@dataclass(frozen=True, slots=True)
class _CandidatePreview:
    """One generated repair and the slot it is safe to export for."""

    result: MinimalRepairResult
    repaired_slot: ClipSlot


class MainWindow(QMainWindow):
    """Coordinate file I/O, analysis, repair, export, and read-only displays."""

    def __init__(self) -> None:
        super().__init__()
        self.document_a: MidiDocument | None = None
        self.document_b: MidiDocument | None = None
        self.pair_analysis: PairAnalysis | None = None
        self.repair_result: MinimalRepairResult | None = None
        self.repaired_slot: ClipSlot | None = None
        self._repair_candidates: list[_CandidatePreview] = []

        self.setWindowTitle("GLUE — MIDI Compatibility")
        self.resize(1180, 820)
        self.setMinimumSize(900, 650)
        self._build_ui()
        self._connect_signals()
        self._reset_analysis()

    @property
    def locked_slot(self) -> ClipSlot:
        """Return the clip currently protected from repair."""

        return "A" if self.lock_a_radio.isChecked() else "B"

    def load_clip(self, slot: ClipSlot | str, path: str | Path) -> MidiDocument:
        """Load one MIDI file into slot A or B without opening a dialog."""

        normalized_slot = self._normalize_slot(slot)
        document = validate_for_analysis(load_midi(path))
        if normalized_slot == "A":
            self.document_a = document
        else:
            self.document_b = document

        self._update_clip_summary(normalized_slot, document)
        self._reset_analysis()
        warning_status = (
            f" with {len(document.warnings)} parser warning"
            f"{'s' if len(document.warnings) != 1 else ''}"
            if document.warnings
            else ""
        )
        self.statusBar().showMessage(
            f"Loaded {document.source_path.name} into clip "
            f"{normalized_slot}{warning_status}.",
            7000 if document.warnings else 5000,
        )
        return document

    def analyze(self) -> PairAnalysis:
        """Analyze the loaded clips and update every analysis display."""

        document_a, document_b = self._require_documents()
        result = analyze_pair(document_a.clip, document_b.clip)
        self.pair_analysis = result
        self._clear_candidate(restore_original=False)
        self.piano_roll.set_clips(document_a.clip, document_b.clip)
        self._display_analysis(result, update_keys=True)
        self._update_repair_enabled()
        status = (
            f"Analysis complete: {result.overall_score:.1f}/100."
            if _has_comparable_overlap(result)
            else "Analysis complete: no comparable overlap."
        )
        self.statusBar().showMessage(status, 5000)
        return result

    def repair_minimal(self) -> MinimalRepairResult:
        """Generate the backward-compatible V0.1 Minimal repair candidate."""

        return self._generate_repair_candidate(RepairPreset.MINIMAL, 50)

    def repair_selected(self) -> MinimalRepairResult:
        """Generate and preview a repair using the selected UI controls."""

        return self._generate_repair_candidate(
            self.selected_preset,
            self.preservation_slider.value(),
        )

    @property
    def selected_preset(self) -> RepairPreset:
        """Return the preset selected in the repair controls."""

        index = self.preset_combo.currentIndex()
        presets = tuple(RepairPreset)
        if not 0 <= index < len(presets):
            raise RuntimeError("The selected repair preset is invalid")
        return presets[index]

    @property
    def repair_candidate_count(self) -> int:
        """Return the number of retained repair candidates."""

        return len(self._repair_candidates)

    def _generate_repair_candidate(
        self,
        preset: RepairPreset,
        preservation: int,
    ) -> MinimalRepairResult:
        document_a, document_b = self._require_documents()
        if self.pair_analysis is None:
            self.analyze()
        if self.pair_analysis is None or not _has_comparable_overlap(
            self.pair_analysis
        ):
            raise RuntimeError(
                "The clips have no comparable overlap to repair"
            )

        if self.locked_slot == "A":
            locked_clip = document_a.clip
            unlocked_clip = document_b.clip
            repaired_slot: ClipSlot = "B"
        else:
            locked_clip = document_b.clip
            unlocked_clip = document_a.clip
            repaired_slot = "A"
        if not _has_editable_pitched_notes(unlocked_clip):
            raise RuntimeError(
                f"MIDI {repaired_slot} has no pitched notes available for repair"
            )

        if preset is RepairPreset.MINIMAL and preservation == 50:
            result = generate_minimal_repair(locked_clip, unlocked_clip)
        else:
            result = generate_repair(
                locked_clip,
                unlocked_clip,
                repair_config=repair_config_for(preset, preservation),
            )
        preview = _CandidatePreview(result=result, repaired_slot=repaired_slot)
        self._repair_candidates.append(preview)
        item = QListWidgetItem(self._candidate_list_text(preview))
        item.setData(
            Qt.ItemDataRole.UserRole,
            len(self._repair_candidates) - 1,
        )
        self.candidate_list.addItem(item)
        self.candidate_list.setCurrentItem(item)
        self._select_candidate(preview)
        self.statusBar().showMessage(
            f"{preset.label} candidate generated with {result.changed_note_count} pitch "
            f"change{'s' if result.changed_note_count != 1 else ''}.",
            5000,
        )
        return result

    def export_candidate(self, path: str | Path) -> Path:
        """Export the current repaired clip without opening a dialog."""

        if self.repair_result is None or self.repaired_slot is None:
            raise RuntimeError("Generate and select a repair candidate before exporting")
        source_document = (
            self.document_a if self.repaired_slot == "A" else self.document_b
        )
        if source_document is None:
            raise RuntimeError("The source document for the repaired clip is unavailable")

        destination = Path(path)
        loaded_sources = tuple(
            document.source_path
            for document in (self.document_a, self.document_b)
            if document is not None
        )
        if any(
            _paths_refer_to_same_file(destination, source)
            for source in loaded_sources
        ):
            raise RuntimeError(
                "Refusing to overwrite loaded MIDI A or MIDI B; "
                "choose a different export path"
            )
        output_path = save_midi(
            source_document,
            destination,
            clip=self.repair_result.repaired_clip,
        )
        self.statusBar().showMessage(f"Exported repaired MIDI to {output_path}.", 7000)
        return output_path

    def _build_ui(self) -> None:
        central = QWidget(self)
        root = QVBoxLayout(central)
        root.addLayout(self._build_file_controls())
        root.addLayout(self._build_score_row())

        workspace = QSplitter(Qt.Orientation.Horizontal, central)
        visual_panel = QWidget(workspace)
        visual_layout = QVBoxLayout(visual_panel)
        piano_group = QGroupBox("Overlay piano roll", visual_panel)
        piano_layout = QVBoxLayout(piano_group)
        self.piano_roll = PianoRollWidget(piano_group)
        self.piano_roll.setObjectName("pianoRoll")
        piano_layout.addWidget(self.piano_roll)
        visual_layout.addWidget(piano_group, 3)

        timeline_group = QGroupBox("Compatibility timeline", visual_panel)
        timeline_layout = QVBoxLayout(timeline_group)
        self.timeline = CompatibilityTimelineWidget(timeline_group)
        self.timeline.setObjectName("compatibilityTimeline")
        timeline_layout.addWidget(self.timeline)
        visual_layout.addWidget(timeline_group, 1)

        details_panel = QWidget(workspace)
        details_layout = QVBoxLayout(details_panel)
        diagnosis_group = QGroupBox("Diagnosis", details_panel)
        diagnosis_layout = QVBoxLayout(diagnosis_group)
        self.diagnosis_list = QListWidget(diagnosis_group)
        self.diagnosis_list.setObjectName("diagnosisList")
        self.diagnosis_list.setWordWrap(True)
        diagnosis_layout.addWidget(self.diagnosis_list)
        details_layout.addWidget(diagnosis_group, 2)
        details_layout.addWidget(self._build_repair_group(details_panel), 2)

        workspace.addWidget(visual_panel)
        workspace.addWidget(details_panel)
        workspace.setStretchFactor(0, 3)
        workspace.setStretchFactor(1, 2)
        root.addWidget(workspace, 1)
        self.setCentralWidget(central)

    def _build_file_controls(self) -> QHBoxLayout:
        row = QHBoxLayout()
        group_a = self._build_clip_group("A")
        group_b = self._build_clip_group("B")
        row.addWidget(group_a)
        row.addWidget(group_b)

        controls = QVBoxLayout()
        self.analyze_button = QPushButton("Analyze compatibility")
        self.analyze_button.setObjectName("analyzeButton")
        controls.addWidget(self.analyze_button)
        controls.addStretch(1)
        row.addLayout(controls)
        return row

    def _build_clip_group(self, slot: ClipSlot) -> QGroupBox:
        group = QGroupBox(f"MIDI {slot}")
        layout = QGridLayout(group)
        load_button = QPushButton(f"Load MIDI {slot}…", group)
        load_button.setObjectName(f"load{slot}Button")
        lock_radio = QRadioButton(f"Lock {slot}", group)
        lock_radio.setObjectName(f"lock{slot}Radio")
        path_label = QLabel("No file loaded", group)
        path_label.setObjectName(f"path{slot}Label")
        path_label.setWordWrap(True)
        metadata_label = QLabel("Notes: —  |  Length: —  |  Tempo: —  |  Meter: —", group)
        metadata_label.setObjectName(f"metadata{slot}Label")
        metadata_label.setWordWrap(True)
        key_label = QLabel("Estimated key: —", group)
        key_label.setObjectName(f"key{slot}Label")

        layout.addWidget(load_button, 0, 0)
        layout.addWidget(lock_radio, 0, 1)
        layout.addWidget(path_label, 1, 0, 1, 2)
        layout.addWidget(metadata_label, 2, 0, 1, 2)
        layout.addWidget(key_label, 3, 0, 1, 2)
        layout.setColumnStretch(0, 1)

        if slot == "A":
            self.file_a_button = load_button
            self.lock_a_radio = lock_radio
            self.path_a_label = path_label
            self.metadata_a_label = metadata_label
            self.key_a_label = key_label
        else:
            self.file_b_button = load_button
            self.lock_b_radio = lock_radio
            self.path_b_label = path_label
            self.metadata_b_label = metadata_label
            self.key_b_label = key_label
        return group

    def _build_score_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self.overall_score_label = self._score_group(row, "Overall", "overallScore")
        self.harmonic_score_label = self._score_group(row, "Harmonic", "harmonicScore")
        self.bass_score_label = self._score_group(row, "Bass / root", "bassScore")
        self.register_score_label = self._score_group(row, "Register", "registerScore")
        self.rhythm_score_label = self._score_group(row, "Rhythm", "rhythmScore")
        return row

    @staticmethod
    def _score_group(row: QHBoxLayout, title: str, object_name: str) -> QLabel:
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        label = QLabel("—", group)
        label.setObjectName(object_name)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumWidth(90)
        layout.addWidget(label)
        row.addWidget(group)
        return label

    def _build_repair_group(self, parent: QWidget) -> QGroupBox:
        group = QGroupBox("Repair candidates", parent)
        layout = QVBoxLayout(group)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Preset:", group))
        self.preset_combo = QComboBox(group)
        self.preset_combo.setObjectName("repairPresetCombo")
        for preset in RepairPreset:
            self.preset_combo.addItem(preset.label, preset.value)
        preset_row.addWidget(self.preset_combo, 1)
        layout.addLayout(preset_row)

        preservation_row = QHBoxLayout()
        preservation_row.addWidget(QLabel("Preservation:", group))
        self.preservation_slider = QSlider(Qt.Orientation.Horizontal, group)
        self.preservation_slider.setObjectName("preservationSlider")
        self.preservation_slider.setRange(0, 100)
        self.preservation_slider.setValue(50)
        self.preservation_slider.setSingleStep(1)
        self.preservation_slider.setPageStep(10)
        self.preservation_slider.setToolTip(
            "Higher values penalize pitch edits more strongly."
        )
        self.preservation_value_label = QLabel("50%", group)
        self.preservation_value_label.setObjectName("preservationValue")
        self.preservation_value_label.setMinimumWidth(36)
        preservation_row.addWidget(self.preservation_slider, 1)
        preservation_row.addWidget(self.preservation_value_label)
        layout.addLayout(preservation_row)

        self.repair_button = QPushButton("Generate Minimal repair", group)
        self.repair_button.setObjectName("minimalRepairButton")
        self.candidate_list = QListWidget(group)
        self.candidate_list.setObjectName("candidateList")
        self.candidate_list.setWordWrap(True)
        self.candidate_list.setMaximumHeight(105)
        self.candidate_label = QLabel("No candidate generated.", group)
        self.candidate_label.setObjectName("candidateSummary")
        self.candidate_label.setWordWrap(True)
        self.edit_list = QListWidget(group)
        self.edit_list.setObjectName("editList")
        self.edit_list.setWordWrap(True)
        self.export_button = QPushButton("Export repaired MIDI…", group)
        self.export_button.setObjectName("exportButton")
        layout.addWidget(self.repair_button)
        layout.addWidget(self.candidate_list)
        layout.addWidget(self.candidate_label)
        layout.addWidget(self.edit_list, 1)
        layout.addWidget(self.export_button)
        return group

    def _connect_signals(self) -> None:
        self.lock_group = QButtonGroup(self)
        self.lock_group.setExclusive(True)
        self.lock_group.addButton(self.lock_a_radio)
        self.lock_group.addButton(self.lock_b_radio)
        self.lock_a_radio.setChecked(True)

        self.file_a_button.clicked.connect(lambda _checked=False: self._choose_clip("A"))
        self.file_b_button.clicked.connect(lambda _checked=False: self._choose_clip("B"))
        self.analyze_button.clicked.connect(self._analyze_interactive)
        self.repair_button.clicked.connect(self._repair_interactive)
        self.export_button.clicked.connect(self._export_interactive)
        self.lock_a_radio.toggled.connect(self._on_lock_toggled)
        self.lock_b_radio.toggled.connect(self._on_lock_toggled)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        self.preservation_slider.valueChanged.connect(
            self._on_preservation_changed
        )
        self.candidate_list.currentItemChanged.connect(
            self._on_candidate_item_changed
        )

    def _choose_clip(self, slot: ClipSlot) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            f"Load MIDI {slot}",
            "",
            "MIDI files (*.mid *.midi);;All files (*)",
        )
        if not filename:
            return
        self._run_interactive(
            f"Could not load MIDI {slot}",
            lambda: self.load_clip(slot, filename),
        )

    def _analyze_interactive(self) -> None:
        self._run_interactive("Could not analyze these MIDI files", self.analyze)

    def _repair_interactive(self) -> None:
        self._run_interactive(
            f"Could not generate a {self.selected_preset.label} repair",
            self.repair_selected,
        )

    def _export_interactive(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export repaired MIDI",
            "glue_repaired.mid",
            "MIDI files (*.mid *.midi);;All files (*)",
        )
        if not filename:
            return
        destination = Path(filename)
        if destination.suffix.lower() not in {".mid", ".midi"}:
            destination = destination.with_suffix(".mid")
        self._run_interactive(
            "Could not export repaired MIDI",
            lambda: self.export_candidate(destination),
        )

    def _run_interactive(
        self,
        title: str,
        operation: Callable[[], _ResultT],
    ) -> _ResultT | None:
        try:
            return operation()
        except (OSError, RuntimeError, ValueError) as exc:
            QMessageBox.critical(self, title, str(exc))
            return None

    def _on_lock_toggled(self, checked: bool) -> None:
        if checked:
            self._clear_candidate(restore_original=True)
            self._update_repair_enabled()

    def _on_preset_changed(self, _index: int) -> None:
        self.repair_button.setText(
            f"Generate {self.selected_preset.label} repair"
        )

    def _on_preservation_changed(self, value: int) -> None:
        self.preservation_value_label.setText(f"{value}%")

    def _on_candidate_item_changed(
        self,
        current: QListWidgetItem | None,
        previous: QListWidgetItem | None,
    ) -> None:
        del previous
        if current is None:
            return
        index = current.data(Qt.ItemDataRole.UserRole)
        if not isinstance(index, int) or not 0 <= index < len(
            self._repair_candidates
        ):
            return
        self._select_candidate(self._repair_candidates[index])

    def _select_candidate(self, preview: _CandidatePreview) -> None:
        document_a, document_b = self._require_documents()
        result = preview.result
        self.repair_result = result
        self.repaired_slot = preview.repaired_slot
        self._display_analysis(result.after_analysis, update_keys=False)
        self.timeline.set_comparison(
            result.before_analysis,
            result.after_analysis,
        )
        self.piano_roll.set_comparison(
            document_a.clip,
            document_b.clip,
            preview.repaired_slot,
            result.repaired_clip,
        )
        self._display_candidate(result)
        self.export_button.setEnabled(True)

    @staticmethod
    def _candidate_list_text(preview: _CandidatePreview) -> str:
        result = preview.result
        return (
            f"{result.preset.label} | preservation {result.preservation}% | "
            f"repair {preview.repaired_slot} | "
            f"{result.original_score:.1f} -> {result.repaired_score:.1f} | "
            f"{result.changed_note_count} changed"
        )

    def _require_documents(self) -> tuple[MidiDocument, MidiDocument]:
        if self.document_a is None or self.document_b is None:
            raise RuntimeError("Load MIDI A and MIDI B before analyzing")
        return self.document_a, self.document_b

    @staticmethod
    def _normalize_slot(slot: ClipSlot | str) -> ClipSlot:
        normalized = slot.upper()
        if normalized not in {"A", "B"}:
            raise ValueError("slot must be 'A' or 'B'")
        return cast(ClipSlot, normalized)

    def _update_clip_summary(
        self,
        slot: ClipSlot,
        document: MidiDocument,
    ) -> None:
        clip = document.clip
        path_label = self.path_a_label if slot == "A" else self.path_b_label
        metadata_label = self.metadata_a_label if slot == "A" else self.metadata_b_label
        key_label = self.key_a_label if slot == "A" else self.key_b_label
        path_label.setText(str(document.source_path))
        path_label.setToolTip(str(document.source_path.resolve()))

        beats = float(clip.duration_quarter_notes)
        tempo_bpm = 60_000_000 / clip.tempo_at(0)
        numerator, denominator = clip.time_signature_at(0)
        track_count = len(clip.tracks) or 1
        warning_suffix = (
            f"  |  Warnings: {len(document.warnings)}" if document.warnings else ""
        )
        metadata_label.setText(
            f"Notes: {len(clip.notes)}  |  Tracks: {track_count}  |  "
            f"Length: {beats:g} beats  |  Tempo: {tempo_bpm:.1f} BPM  |  "
            f"Meter: {numerator}/{denominator}{warning_suffix}"
        )
        metadata_label.setToolTip(
            "\n".join(document.warnings)
            if document.warnings
            else "No parser warnings."
        )
        self._set_key_label(key_label, estimate_key(clip))

    @staticmethod
    def _set_key_label(label: QLabel, estimate: KeyEstimate) -> None:
        label.setText(
            f"Estimated key: {estimate.label} "
            f"({estimate.confidence * 100:.0f}% confidence)"
        )

    def _reset_analysis(self) -> None:
        self.pair_analysis = None
        self._clear_candidate(restore_original=False)
        self._set_score_labels(None)
        self.timeline.set_analysis(None)
        self.diagnosis_list.clear()
        self.diagnosis_list.addItem("Load and analyze two clips to see possible conflicts.")
        self.piano_roll.set_clips(
            self.document_a.clip if self.document_a is not None else None,
            self.document_b.clip if self.document_b is not None else None,
        )
        ready = self.document_a is not None and self.document_b is not None
        self.analyze_button.setEnabled(ready)
        self.repair_button.setEnabled(False)

    def _clear_candidate(self, *, restore_original: bool) -> None:
        self.repair_result = None
        self.repaired_slot = None
        self._repair_candidates.clear()
        self.candidate_list.clear()
        self.candidate_label.setText("No candidate generated.")
        self.edit_list.clear()
        self.export_button.setEnabled(False)
        if restore_original and self.pair_analysis is not None:
            self._display_analysis(self.pair_analysis, update_keys=False)
            self.piano_roll.set_clips(
                self.document_a.clip if self.document_a is not None else None,
                self.document_b.clip if self.document_b is not None else None,
            )

    def _update_repair_enabled(self) -> None:
        enabled = (
            self.pair_analysis is not None
            and _has_comparable_overlap(self.pair_analysis)
            and _has_editable_pitched_notes(self._unlocked_clip())
        )
        self.repair_button.setEnabled(enabled)

    def _unlocked_clip(self) -> MidiClip | None:
        document = (
            self.document_b if self.locked_slot == "A" else self.document_a
        )
        return document.clip if document is not None else None

    def _display_analysis(
        self,
        result: PairAnalysis,
        *,
        update_keys: bool,
    ) -> None:
        self._set_score_labels(result)
        self.timeline.set_analysis(result)
        self.diagnosis_list.clear()
        if not _has_comparable_overlap(result):
            self.diagnosis_list.addItem(
                "No comparable overlap: the clips are not active together in any "
                "analysis window. Neutral internal scores do not establish compatibility."
            )
        elif result.reasons:
            for reason in result.reasons:
                self.diagnosis_list.addItem(reason.message)
        else:
            self.diagnosis_list.addItem(
                "No strong conflict was detected by the current heuristics."
            )
        if update_keys:
            self._set_key_label(self.key_a_label, result.key_a)
            self._set_key_label(self.key_b_label, result.key_b)

    def _set_score_labels(self, result: PairAnalysis | None) -> None:
        if result is not None and not _has_comparable_overlap(result):
            self.overall_score_label.setText("No comparable overlap")
            for label in (
                self.harmonic_score_label,
                self.bass_score_label,
                self.register_score_label,
                self.rhythm_score_label,
            ):
                label.setText("N/A")
            return

        labels_and_values = (
            (self.overall_score_label, result.overall_score if result else None),
            (self.harmonic_score_label, result.harmonic_score if result else None),
            (self.bass_score_label, result.bass_score if result else None),
            (self.register_score_label, result.register_score if result else None),
            (self.rhythm_score_label, result.rhythm_score if result else None),
        )
        for label, value in labels_and_values:
            label.setText("—" if value is None else f"{value:.1f}/100")

    def _display_candidate(self, result: MinimalRepairResult) -> None:
        changed = (
            f"{result.changed_note_count} note"
            f"{'s' if result.changed_note_count != 1 else ''} changed"
        )
        if _has_comparable_overlap(result.before_analysis):
            self.candidate_label.setText(
                f"{result.preset.label} (preservation {result.preservation}%): "
                f"{result.original_score:.1f} → "
                f"{result.repaired_score:.1f} / 100  |  {changed}"
            )
        else:
            self.candidate_label.setText(
                f"{result.preset.label}: no comparable overlap  |  {changed}"
            )
        self.edit_list.clear()
        if not result.edits:
            self.edit_list.addItem(
                "No pitch edit cleared the preservation penalty; the candidate is unchanged."
            )
            return
        original_by_id = {note.id: note for note in result.original_clip.notes}
        for edit in result.edits:
            note = original_by_id[edit.note_id]
            onset = note.onset_ticks / result.original_clip.ticks_per_beat
            self.edit_list.addItem(self._edit_description(edit, onset))

    @staticmethod
    def _edit_description(edit: NoteEdit, onset: float) -> str:
        direction = "+" if edit.delta > 0 else ""
        return (
            f"Note {edit.note_id} at beat {onset + 1:g}: "
            f"{_pitch_label(edit.original_pitch)} → {_pitch_label(edit.repaired_pitch)} "
            f"({direction}{edit.delta} semitones; affected-window score "
            f"+{edit.score_improvement:.1f})"
        )


def _pitch_label(pitch: int) -> str:
    names = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    return f"{names[pitch % 12]}{pitch // 12 - 1}"


def _has_comparable_overlap(result: PairAnalysis) -> bool:
    """Whether any analysis window contains simultaneous clip activity."""

    return any(window.activity_weight > 0 for window in result.windows)


def _has_editable_pitched_notes(clip: MidiClip | None) -> bool:
    """Whether a clip contains a positive-duration non-percussion note."""

    return clip is not None and any(
        not note.is_percussion and note.duration_ticks > 0
        for note in clip.notes
    )


def _paths_refer_to_same_file(left: Path, right: Path) -> bool:
    """Compare existing paths by identity and new paths by resolved name."""

    try:
        return left.samefile(right)
    except OSError:
        return left.resolve(strict=False) == right.resolve(strict=False)
