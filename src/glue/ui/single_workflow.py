"""PySide6 orchestration for the Polish One Clip workflow."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import TypeVar

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from glue.analysis import SingleClipAnalysis, SingleClipSuggestion, analyze_single_clip
from glue.fixes import RepairPreset, SingleRepairResult, generate_single_repair
from glue.fixes.musical import MusicalCandidate, MusicalRepair, generate_musical_repairs
from glue.io import MidiDocument, load_midi, validate_for_analysis
from glue.models import MidiClip
from glue.single_exporting import (
    export_single_change_report,
    export_single_repaired_midi,
)

from .musical_controls import MusicalControls
from .visualizations import PianoRollWidget, midi_pitch_name

_ResultT = TypeVar("_ResultT")
_StatusCallback = Callable[[str, int], None]
_FULLY_PRESERVED_MESSAGE = (
    "This clip is fully preserved. Lower preservation below 100% to allow repair."
)


class SingleClipWorkflowWidget(QWidget):
    """Coordinate single-clip I/O, analysis, repair, and presentation."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        status_callback: _StatusCallback | None = None,
    ) -> None:
        super().__init__(parent)
        self.document: MidiDocument | None = None
        self.analysis: SingleClipAnalysis | None = None
        self.repair_result: SingleRepairResult | None = None
        self.last_repair_attempt: SingleRepairResult | None = None
        self._analysis_cache: dict[MidiClip, SingleClipAnalysis] = {}
        self._busy_depth = 0
        self._status_callback = status_callback
        self._suggestion_items: dict[str, QListWidgetItem] = {}

        self.setObjectName("polishOneClipPage")
        self._build_ui()
        self._connect_signals()
        self._reset_document_display()

    @property
    def selected_preset(self) -> RepairPreset:
        """Return the repair preset currently selected."""

        index = self.preset_combo.currentIndex()
        presets = tuple(RepairPreset)
        if not 0 <= index < len(presets):
            raise RuntimeError("The selected repair preset is invalid")
        return presets[index]

    @property
    def preservation(self) -> int:
        """Return the selected preservation percentage."""

        return self.preservation_slider.value()

    @property
    def enabled_suggestion_ids(self) -> frozenset[str]:
        """Return all checked suggestion identifiers."""

        return frozenset(
            suggestion_id
            for suggestion_id, item in self._suggestion_items.items()
            if item.checkState() == Qt.CheckState.Checked
        )

    @property
    def is_busy(self) -> bool:
        """Whether analysis or repair is currently running."""

        return self._busy_depth > 0

    def set_preservation(self, value: int) -> None:
        """Set preservation after validating the public GUI contract."""

        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("preservation must be an integer between 0 and 100")
        if not 0 <= value <= 100:
            raise ValueError("preservation must be between 0 and 100")
        self.preservation_slider.setValue(value)

    def load_clip(self, path: str | Path) -> MidiDocument:
        """Load and analyze one MIDI file without opening a dialog."""

        document = validate_for_analysis(load_midi(path))
        self.document = document
        self.analysis = None
        self.repair_result = None
        self._update_document_summary(document)
        self.before_piano_roll.set_single_clip(document.clip)
        self.after_piano_roll.set_single_clip(document.clip)
        self.piano_roll_tabs.setTabEnabled(1, False)
        self._clear_suggestions()
        self._clear_repair_display()
        self.analyze()
        warning_status = (
            f" with {len(document.warnings)} parser warning"
            f"{'s' if len(document.warnings) != 1 else ''}"
            if document.warnings
            else ""
        )
        self._show_status(
            f"Loaded {document.source_path.name} for polishing{warning_status}.",
            7000 if document.warnings else 5000,
        )
        return document

    def analyze(self) -> SingleClipAnalysis:
        """Analyze the loaded clip, reusing immutable content from the cache."""

        document = self._require_document()
        if self.analysis is not None:
            return self.analysis
        result = self._analysis_cache.get(document.clip)
        reused = result is not None
        if result is None:
            result = self._run_busy(
                "Analyzing suggestions...",
                lambda: analyze_single_clip(document.clip),
            )
            if len(self._analysis_cache) >= 4:
                self._analysis_cache.pop(next(iter(self._analysis_cache)))
            self._analysis_cache[document.clip] = result
        self.analysis = result
        self._display_analysis(result)
        self._update_enabled()
        self._show_status(
            (
                "Single-clip analysis reused"
                if reused
                else "Single-clip analysis complete"
            )
            + f": {result.internal_consistency_score:.1f}/100.",
            5000,
        )
        return result

    def generate_repair(self) -> SingleRepairResult:
        """Generate one repair using only the currently enabled suggestions."""

        document = self._require_document()
        self.musical_controls.clear()
        self.legacy_results.show()
        analysis = self.analysis or self.analyze()
        result = self._run_busy(
            f"Generating {self.selected_preset.label} repair...",
            lambda: generate_single_repair(
                document.clip,
                analysis=analysis,
                enabled_suggestion_ids=self.enabled_suggestion_ids,
                preset=self.selected_preset,
                preservation=self.preservation,
            ),
        )
        self.last_repair_attempt = result
        if result.has_improvement:
            self.repair_result = result
            self.after_piano_roll.set_single_comparison(
                result.original_clip,
                result.repaired_clip,
            )
            self.piano_roll_tabs.setTabEnabled(1, True)
            self.piano_roll_tabs.setCurrentIndex(1)
            self._display_repair(result)
            self._show_status(
                f"{result.changed_note_count} pitch "
                f"change{'s' if result.changed_note_count != 1 else ''} generated.",
                5000,
            )
        else:
            self.repair_result = None
            self.after_piano_roll.set_single_clip(document.clip)
            self.piano_roll_tabs.setTabEnabled(1, False)
            self._display_no_improvement(result)
            self._show_status(result.stop_reason, 7000)
        self._update_enabled()
        return result

    def repair_musical(self) -> MusicalRepair:
        """Compare musical passages under the current independent permissions."""
        document = self._require_document()
        analysis = self.analysis or self.analyze()
        choices: dict[int, set[int]] = {s.target_note_id: set() for s in analysis.suggestions}
        for suggestion in analysis.suggestions:
            if suggestion.suggestion_id in self.enabled_suggestion_ids:
                choices[suggestion.target_note_id].update(suggestion.alternatives)
        self._clear_repair_display()
        result = self._run_busy(
            "Comparing bounded musical passages…",
            lambda: generate_musical_repairs(
                document.clip, permissions=self.musical_controls.permissions,
                pitch_choices={key: frozenset(values) for key, values in choices.items()},
                preservation=(self.preservation,), preset=self.selected_preset),
        )
        self.legacy_results.hide()
        self.musical_controls.display(result, (document,))
        return result

    def _preview_musical(self, candidate: MusicalCandidate) -> None:
        self.after_piano_roll.set_single_comparison(self._require_document().clip, candidate.clips[0])
        self.piano_roll_tabs.setTabEnabled(1, True)
        self.piano_roll_tabs.setCurrentIndex(1)

    def export_repaired(
        self,
        path: str | Path,
        *,
        overwrite: bool = False,
    ) -> Path:
        """Export the selected repaired MIDI without opening a dialog."""

        result = self._require_repair()
        document = self._require_document()
        output = export_single_repaired_midi(
            result,
            document,
            path,
            overwrite=overwrite,
        )
        self._show_status(f"Exported repaired MIDI to {output}.", 7000)
        return output

    def export_report(
        self,
        path: str | Path,
        *,
        overwrite: bool = False,
    ) -> Path:
        """Export the selected single-clip JSON report."""

        result = self._require_repair()
        document = self._require_document()
        output = export_single_change_report(
            result,
            document,
            path,
            overwrite=overwrite,
        )
        self._show_status(f"Exported change report to {output}.", 7000)
        return output

    def select_all_suggestions(self) -> None:
        """Enable every primary and secondary suggestion."""

        self._set_all_suggestion_states(Qt.CheckState.Checked)

    def clear_all_suggestions(self) -> None:
        """Disable every primary and secondary suggestion."""

        self._set_all_suggestion_states(Qt.CheckState.Unchecked)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        header = QHBoxLayout()
        title = QLabel("Polish One Clip", self)
        title.setObjectName("polishWorkflowTitle")
        header.addWidget(title)
        header.addStretch(1)
        root.addLayout(header)

        file_group = QGroupBox("MIDI file", self)
        file_layout = QGridLayout(file_group)
        self.load_button = QPushButton("Load MIDI...", file_group)
        self.load_button.setObjectName("singleLoadButton")
        self.path_label = QLabel("No file loaded", file_group)
        self.path_label.setObjectName("singlePathLabel")
        self.path_label.setWordWrap(True)
        self.metadata_label = QLabel(
            "Notes: -  |  Length: -  |  Tempo: -  |  Meter: -",
            file_group,
        )
        self.metadata_label.setObjectName("singleMetadataLabel")
        self.metadata_label.setWordWrap(True)
        self.key_label = QLabel("Estimated key / mode: -", file_group)
        self.key_label.setObjectName("singleKeyLabel")
        self.consistency_label = QLabel(
            "Estimated internal consistency: -",
            file_group,
        )
        self.consistency_label.setObjectName("singleConsistencyLabel")
        self.analysis_toggle_button = QPushButton(
            "Show analysis details",
            file_group,
        )
        self.analysis_toggle_button.setObjectName("singleAnalysisDetailsToggle")
        self.analysis_toggle_button.setCheckable(True)
        self.busy_status_label = QLabel("Ready", file_group)
        self.busy_status_label.setObjectName("singleBusyStatusLabel")
        self.busy_indicator = QProgressBar(file_group)
        self.busy_indicator.setObjectName("singleBusyIndicator")
        self.busy_indicator.setRange(0, 0)
        self.busy_indicator.setTextVisible(False)
        self.busy_indicator.setFixedWidth(96)
        self.busy_indicator.hide()
        file_layout.addWidget(self.load_button, 0, 0)
        file_layout.addWidget(self.path_label, 0, 1, 1, 3)
        file_layout.addWidget(self.metadata_label, 1, 0, 1, 4)
        file_layout.addWidget(self.key_label, 2, 0, 1, 2)
        file_layout.addWidget(self.consistency_label, 2, 2, 1, 2)
        file_layout.addWidget(self.analysis_toggle_button, 3, 0)
        file_layout.addWidget(self.busy_status_label, 3, 1)
        file_layout.addWidget(self.busy_indicator, 3, 2)
        file_layout.setColumnStretch(1, 1)
        file_layout.setColumnStretch(3, 1)
        root.addWidget(file_group)

        self.analysis_details_panel = self._build_analysis_details()
        self.analysis_details_panel.setObjectName("singleAnalysisDetailsPanel")
        self.analysis_details_panel.hide()
        root.addWidget(self.analysis_details_panel)

        workspace = QSplitter(Qt.Orientation.Horizontal, self)
        workspace.setObjectName("singleWorkflowSplitter")
        visual_group = QGroupBox("Before / after piano roll", workspace)
        visual_layout = QVBoxLayout(visual_group)
        self.piano_roll_tabs = QTabWidget(visual_group)
        self.piano_roll_tabs.setObjectName("singlePianoRollTabs")
        self.before_piano_roll = PianoRollWidget(self.piano_roll_tabs)
        self.before_piano_roll.setObjectName("singleBeforePianoRoll")
        self.after_piano_roll = PianoRollWidget(self.piano_roll_tabs)
        self.after_piano_roll.setObjectName("singleAfterPianoRoll")
        self.piano_roll_tabs.addTab(self.before_piano_roll, "Before")
        self.piano_roll_tabs.addTab(self.after_piano_roll, "After")
        self.piano_roll_tabs.setTabEnabled(1, False)
        visual_layout.addWidget(self.piano_roll_tabs)

        controls_scroll = QScrollArea(workspace)
        controls_scroll.setObjectName("singleControlsScrollArea")
        controls_scroll.setMinimumWidth(360)
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        controls = QWidget(controls_scroll)
        controls_layout = QVBoxLayout(controls)
        controls_layout.addWidget(self._build_repair_controls(controls))
        controls_layout.addWidget(self._build_result_group(controls))
        controls_layout.addWidget(self._build_suggestions(controls), 1)
        controls.setMinimumHeight(controls.minimumSizeHint().height())
        controls.setMinimumWidth(1)
        controls.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred,
        )
        controls_scroll.setWidget(controls)

        workspace.addWidget(visual_group)
        workspace.addWidget(controls_scroll)
        workspace.setStretchFactor(0, 5)
        workspace.setStretchFactor(1, 4)
        workspace.setSizes([700, 440])
        root.addWidget(workspace, 1)

    def _build_analysis_details(self) -> QWidget:
        panel = QGroupBox("Analysis details", self)
        layout = QGridLayout(panel)
        component_names = (
            ("Harmonic", "harmonic"),
            ("Melodic", "melodic"),
            ("Voice leading", "voice_leading"),
            ("Overlap", "overlap"),
            ("Register", "register"),
            ("Bass", "bass"),
            ("Motif", "motif"),
        )
        self.component_score_labels: dict[str, QLabel] = {}
        for index, (title, field_name) in enumerate(component_names):
            layout.addWidget(QLabel(f"{title}:", panel), index // 4, (index % 4) * 2)
            value = QLabel("-", panel)
            value.setObjectName(f"single{field_name.title().replace('_', '')}Score")
            layout.addWidget(value, index // 4, (index % 4) * 2 + 1)
            self.component_score_labels[field_name] = value
        return panel

    def _build_repair_controls(self, parent: QWidget) -> QGroupBox:
        group = QGroupBox("Repair settings", parent)
        layout = QGridLayout(group)
        layout.addWidget(QLabel("Preservation:", group), 0, 0)
        self.preservation_slider = QSlider(Qt.Orientation.Horizontal, group)
        self.preservation_slider.setObjectName("singlePreservationSlider")
        self.preservation_slider.setRange(0, 100)
        self.preservation_slider.setValue(100)
        self.preservation_slider.setSingleStep(1)
        self.preservation_slider.setPageStep(10)
        self.preservation_slider.setToolTip(
            "Higher values make pitch edits more expensive; 100% locks the clip."
        )
        self.preservation_value_label = QLabel("100%", group)
        self.preservation_value_label.setObjectName("singlePreservationValue")
        self.preservation_locked_indicator = QLabel("Locked", group)
        self.preservation_locked_indicator.setObjectName(
            "singlePreservationLockedIndicator"
        )
        layout.addWidget(self.preservation_slider, 0, 1)
        layout.addWidget(self.preservation_value_label, 0, 2)
        layout.addWidget(self.preservation_locked_indicator, 0, 3)
        layout.addWidget(QLabel("Preset:", group), 1, 0)
        self.preset_combo = QComboBox(group)
        self.preset_combo.setObjectName("singlePresetCombo")
        for preset in RepairPreset:
            self.preset_combo.addItem(preset.label, preset.value)
        layout.addWidget(self.preset_combo, 1, 1, 1, 3)
        self.musical_controls = MusicalControls(1, group)
        self.musical_controls.permissions_changed.connect(self._clear_repair_display)
        self.musical_controls.permissions_changed.connect(self._update_enabled)
        self.musical_controls.candidate_changed.connect(self._preview_musical)
        layout.addWidget(self.musical_controls, 2, 0, 1, 4)
        return group

    def _build_suggestions(self, parent: QWidget) -> QGroupBox:
        group = QGroupBox("Suggestions", parent)
        layout = QVBoxLayout(group)
        selection_row = QHBoxLayout()
        self.select_all_button = QPushButton("Select all", group)
        self.select_all_button.setObjectName("singleSelectAllSuggestionsButton")
        self.clear_all_button = QPushButton("Clear all", group)
        self.clear_all_button.setObjectName("singleClearAllSuggestionsButton")
        selection_row.addWidget(self.select_all_button)
        selection_row.addWidget(self.clear_all_button)
        selection_row.addStretch(1)
        layout.addLayout(selection_row)

        self.primary_suggestion_list = QListWidget(group)
        self.primary_suggestion_list.setObjectName("singlePrimarySuggestionList")
        self.primary_suggestion_list.setWordWrap(True)
        self.primary_suggestion_list.setMinimumHeight(115)
        self.primary_suggestion_list.setMaximumHeight(160)
        layout.addWidget(self.primary_suggestion_list)

        self.secondary_toggle_button = QPushButton(
            "Show low-confidence suggestions (0)",
            group,
        )
        self.secondary_toggle_button.setObjectName(
            "singleLowConfidenceSuggestionsToggle"
        )
        self.secondary_toggle_button.setCheckable(True)
        layout.addWidget(self.secondary_toggle_button)
        self.secondary_suggestion_panel = QWidget(group)
        self.secondary_suggestion_panel.setObjectName(
            "singleLowConfidenceSuggestionsPanel"
        )
        secondary_layout = QVBoxLayout(self.secondary_suggestion_panel)
        secondary_layout.setContentsMargins(0, 0, 0, 0)
        self.secondary_suggestion_list = QListWidget(
            self.secondary_suggestion_panel
        )
        self.secondary_suggestion_list.setObjectName(
            "singleLowConfidenceSuggestionList"
        )
        self.secondary_suggestion_list.setWordWrap(True)
        self.secondary_suggestion_list.setMinimumHeight(90)
        secondary_layout.addWidget(self.secondary_suggestion_list)
        self.secondary_suggestion_panel.hide()
        layout.addWidget(self.secondary_suggestion_panel)

        self.suggestion_detail_label = QLabel(
            "Select a suggestion to inspect its explanation and alternatives.",
            group,
        )
        self.suggestion_detail_label.setObjectName("singleSuggestionDetail")
        self.suggestion_detail_label.setWordWrap(True)
        layout.addWidget(self.suggestion_detail_label)
        return group

    def _build_result_group(self, parent: QWidget) -> QGroupBox:
        group = QGroupBox("Repair result", parent)
        layout = QVBoxLayout(group)
        self.generate_button = QPushButton("Generate Minimal repair", group)
        self.generate_button.setObjectName("singleGenerateRepairButton")
        self.score_summary_label = QLabel(
            "Estimated internal consistency before: -  |  after: -  |  improvement: -",
            group,
        )
        self.score_summary_label.setObjectName("singleRepairScoreSummary")
        self.score_summary_label.setWordWrap(True)
        self.stop_reason_label = QLabel("No repair generated.", group)
        self.stop_reason_label.setObjectName("singleRepairStopReason")
        self.stop_reason_label.setWordWrap(True)
        self.edit_list = QListWidget(group)
        self.edit_list.setObjectName("singleRepairEditList")
        self.edit_list.setWordWrap(True)
        self.edit_list.setMinimumHeight(85)
        self.export_midi_button = QPushButton("Export Repaired MIDI...", group)
        self.export_midi_button.setObjectName("singleExportMidiButton")
        self.advanced_export_toggle = QPushButton("Advanced Export", group)
        self.advanced_export_toggle.setObjectName("singleAdvancedExportToggle")
        self.advanced_export_toggle.setCheckable(True)
        self.advanced_export_panel = QWidget(group)
        self.advanced_export_panel.setObjectName("singleAdvancedExportPanel")
        advanced_layout = QVBoxLayout(self.advanced_export_panel)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        self.export_json_button = QPushButton(
            "Export JSON change report...",
            self.advanced_export_panel,
        )
        self.export_json_button.setObjectName("singleExportJsonButton")
        advanced_layout.addWidget(self.export_json_button)
        self.advanced_export_panel.hide()
        layout.addWidget(self.generate_button)
        layout.addWidget(self.musical_controls.results)
        self.legacy_results = QWidget(group)
        layout.addWidget(self.legacy_results)
        layout = QVBoxLayout(self.legacy_results)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.score_summary_label)
        layout.addWidget(self.stop_reason_label)
        layout.addWidget(QLabel("Exact pitch edits", group))
        layout.addWidget(self.edit_list)
        layout.addWidget(self.export_midi_button)
        layout.addWidget(self.advanced_export_toggle)
        layout.addWidget(self.advanced_export_panel)
        return group

    def _connect_signals(self) -> None:
        self.load_button.clicked.connect(self._choose_clip)
        self.analysis_toggle_button.toggled.connect(
            self._toggle_analysis_details
        )
        self.secondary_toggle_button.toggled.connect(
            self._toggle_secondary_suggestions
        )
        self.advanced_export_toggle.toggled.connect(
            self._toggle_advanced_export
        )
        self.select_all_button.clicked.connect(self.select_all_suggestions)
        self.clear_all_button.clicked.connect(self.clear_all_suggestions)
        self.primary_suggestion_list.itemChanged.connect(
            self._on_suggestion_state_changed
        )
        self.secondary_suggestion_list.itemChanged.connect(
            self._on_suggestion_state_changed
        )
        self.primary_suggestion_list.currentItemChanged.connect(
            self._on_suggestion_selected
        )
        self.secondary_suggestion_list.currentItemChanged.connect(
            self._on_suggestion_selected
        )
        self.preservation_slider.valueChanged.connect(
            self._on_preservation_changed
        )
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        self.generate_button.clicked.connect(self._repair_interactive)
        self.export_midi_button.clicked.connect(self._export_midi_interactive)
        self.export_json_button.clicked.connect(self._export_json_interactive)

    def _choose_clip(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load MIDI to polish",
            "",
            "MIDI files (*.mid *.midi);;All files (*)",
        )
        if filename:
            self._run_interactive(
                "Could not load this MIDI file",
                lambda: self.load_clip(filename),
            )

    def _repair_interactive(self) -> None:
        if not self.is_busy:
            self._run_interactive(
                f"Could not generate a {self.selected_preset.label} repair",
                self.repair_musical,
            )

    def _export_midi_interactive(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export repaired MIDI",
            "glue_polished.mid",
            "MIDI files (*.mid *.midi);;All files (*)",
        )
        if not filename:
            return
        destination = Path(filename)
        if destination.suffix.lower() not in {".mid", ".midi"}:
            destination = destination.with_suffix(".mid")
        overwrite = self._confirm_overwrite(destination)
        if overwrite is None:
            return
        self._run_interactive(
            "Could not export repaired MIDI",
            lambda: self.export_repaired(destination, overwrite=overwrite),
        )

    def _export_json_interactive(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export JSON change report",
            "glue_polished_changes.json",
            "JSON files (*.json);;All files (*)",
        )
        if not filename:
            return
        destination = Path(filename)
        if destination.suffix.lower() != ".json":
            destination = destination.with_suffix(".json")
        overwrite = self._confirm_overwrite(destination)
        if overwrite is None:
            return
        self._run_interactive(
            "Could not export change report",
            lambda: self.export_report(destination, overwrite=overwrite),
        )

    def _confirm_overwrite(self, path: Path) -> bool | None:
        if not path.exists():
            return False
        answer = QMessageBox.warning(
            self,
            "Confirm export overwrite",
            f"This export file already exists and will be replaced:\n{path}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return True if answer is QMessageBox.StandardButton.Yes else None

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

    def _run_busy(
        self,
        message: str,
        operation: Callable[[], _ResultT],
    ) -> _ResultT:
        outermost = self._busy_depth == 0
        self._busy_depth += 1
        if outermost:
            self.busy_status_label.setText(message)
            self.busy_indicator.show()
            self._set_controls_busy(True)
            QApplication.processEvents()
        try:
            return operation()
        finally:
            self._busy_depth -= 1
            if outermost:
                self.busy_indicator.hide()
                self.busy_status_label.setText("Ready")
                self._set_controls_busy(False)
                self._update_enabled()

    def _set_controls_busy(self, busy: bool) -> None:
        self.musical_controls.setEnabled(not busy)
        for widget in (
            self.load_button,
            self.analysis_toggle_button,
            self.preservation_slider,
            self.preset_combo,
            self.select_all_button,
            self.clear_all_button,
            self.primary_suggestion_list,
            self.secondary_toggle_button,
            self.secondary_suggestion_list,
            self.generate_button,
            self.export_midi_button,
            self.advanced_export_toggle,
            self.export_json_button,
        ):
            widget.setEnabled(not busy)

    def _toggle_analysis_details(self, expanded: bool) -> None:
        self.analysis_details_panel.setVisible(expanded)
        self.analysis_toggle_button.setText(
            "Hide analysis details" if expanded else "Show analysis details"
        )

    def _toggle_secondary_suggestions(self, expanded: bool) -> None:
        self.secondary_suggestion_panel.setVisible(expanded)
        action = "Hide" if expanded else "Show"
        count = self.secondary_suggestion_list.count()
        self.secondary_toggle_button.setText(
            f"{action} low-confidence suggestions ({count})"
        )

    def _toggle_advanced_export(self, expanded: bool) -> None:
        self.advanced_export_panel.setVisible(expanded)
        self.advanced_export_toggle.setText(
            "Hide Advanced Export" if expanded else "Advanced Export"
        )

    def _on_preservation_changed(self, value: int) -> None:
        self.preservation_value_label.setText(f"{value}%")
        self.preservation_locked_indicator.setVisible(value == 100)
        self._clear_repair_display()
        self._update_enabled()

    def _on_preset_changed(self, _index: int) -> None:
        self.generate_button.setText(
            f"Generate {self.selected_preset.label} repair"
        )
        self._clear_repair_display()
        self._update_enabled()

    def _on_suggestion_state_changed(self, _item: QListWidgetItem) -> None:
        self._clear_repair_display()
        self._update_enabled()

    def _on_suggestion_selected(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        if current is None or self.analysis is None:
            return
        suggestion_id = current.data(Qt.ItemDataRole.UserRole)
        suggestion = next(
            (
                item
                for item in self.analysis.suggestions
                if item.suggestion_id == suggestion_id
            ),
            None,
        )
        if suggestion is not None:
            alternatives = ", ".join(
                midi_pitch_name(pitch) for pitch in suggestion.alternatives
            )
            self.suggestion_detail_label.setText(
                f"{suggestion.explanation}\n"
                f"Possible alternatives: {alternatives or 'none suggested'}"
            )

    def _set_all_suggestion_states(self, state: Qt.CheckState) -> None:
        blockers = (
            QSignalBlocker(self.primary_suggestion_list),
            QSignalBlocker(self.secondary_suggestion_list),
        )
        try:
            for item in self._suggestion_items.values():
                item.setCheckState(state)
        finally:
            del blockers
        self._clear_repair_display()
        self._update_enabled()

    def _display_analysis(self, result: SingleClipAnalysis) -> None:
        self.key_label.setText(
            f"Estimated key / mode: {result.key.label} "
            f"({result.key.confidence * 100:.0f}% confidence)"
        )
        self.consistency_label.setText(
            "Estimated internal consistency: "
            f"{result.internal_consistency_score:.1f}/100"
        )
        for field_name, label in self.component_score_labels.items():
            label.setText(f"{getattr(result, f'{field_name}_score'):.1f}/100")
        self._populate_suggestions(
            result.high_confidence_suggestions,
            result.secondary_suggestions,
            result.default_enabled_suggestion_ids,
        )

    def _populate_suggestions(
        self,
        primary: Iterable[SingleClipSuggestion],
        secondary: Iterable[SingleClipSuggestion],
        enabled_ids: frozenset[str],
    ) -> None:
        primary_items = tuple(primary)
        secondary_items = tuple(secondary)
        blockers = (
            QSignalBlocker(self.primary_suggestion_list),
            QSignalBlocker(self.secondary_suggestion_list),
        )
        try:
            self.primary_suggestion_list.clear()
            self.secondary_suggestion_list.clear()
            self._suggestion_items.clear()
            for suggestion in primary_items:
                self._add_suggestion_item(
                    self.primary_suggestion_list,
                    suggestion,
                    enabled=suggestion.suggestion_id in enabled_ids,
                )
            for suggestion in secondary_items:
                self._add_suggestion_item(
                    self.secondary_suggestion_list,
                    suggestion,
                    enabled=False,
                )
        finally:
            del blockers
        count = len(secondary_items)
        action = "Hide" if self.secondary_toggle_button.isChecked() else "Show"
        self.secondary_toggle_button.setText(
            f"{action} low-confidence suggestions ({count})"
        )
        self.secondary_toggle_button.setEnabled(count > 0)
        if count == 0:
            self.secondary_toggle_button.setChecked(False)
            self.secondary_suggestion_panel.hide()
        if not primary_items:
            self.suggestion_detail_label.setText(
                "No high-confidence suggestions. Expand the secondary section "
                "to review lower-confidence possibilities."
                if secondary_items
                else "No repair suggestions were detected."
            )
        else:
            self.suggestion_detail_label.setText(
                "Select a suggestion to inspect its explanation and alternatives."
            )

    def _add_suggestion_item(
        self,
        widget: QListWidget,
        suggestion: SingleClipSuggestion,
        *,
        enabled: bool,
    ) -> None:
        category = suggestion.category.label
        alternatives = ", ".join(
            midi_pitch_name(pitch) for pitch in suggestion.alternatives
        )
        item = QListWidgetItem(
            f"Beat {suggestion.onset_beats + 1:g} - "
            f"{midi_pitch_name(suggestion.original_pitch)} - {category} - "
            f"{suggestion.confidence * 100:.0f}%\n"
            f"{suggestion.explanation}\n"
            f"Alternatives: {alternatives or 'none suggested'}",
            widget,
        )
        item.setData(Qt.ItemDataRole.UserRole, suggestion.suggestion_id)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(
            Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked
        )
        item.setToolTip(
            f"Note {suggestion.target_note_id}, track {suggestion.track + 1}, "
            f"channel {suggestion.channel + 1}"
        )
        self._suggestion_items[suggestion.suggestion_id] = item

    def _display_repair(self, result: SingleRepairResult) -> None:
        self.score_summary_label.setText(
            "Estimated internal consistency before: "
            f"{result.original_score:.1f}/100  |  "
            f"after: {result.repaired_score:.1f}/100  |  "
            f"improvement: {result.score_improvement:+.1f}"
        )
        self.stop_reason_label.setText(result.stop_reason)
        self.edit_list.clear()
        original_by_id = {note.id: note for note in result.original_clip.notes}
        for edit in result.edits:
            note = original_by_id[edit.note_id]
            onset = note.onset_ticks / result.original_clip.ticks_per_beat
            direction = "+" if edit.delta > 0 else ""
            self.edit_list.addItem(
                f"Note {edit.note_id} at beat {onset + 1:g}: "
                f"{midi_pitch_name(edit.original_pitch)} -> "
                f"{midi_pitch_name(edit.repaired_pitch)} "
                f"({direction}{edit.delta} semitones)"
            )

    def _display_no_improvement(self, result: SingleRepairResult) -> None:
        self.score_summary_label.setText(
            "Estimated internal consistency before: "
            f"{result.original_score:.1f}/100  |  after: -  |  improvement: none"
        )
        reason = result.no_improvement_reason or result.stop_reason
        self.stop_reason_label.setText(reason)
        self.edit_list.clear()
        self.edit_list.addItem("No improving pitch edit was retained.")

    def _update_document_summary(self, document: MidiDocument) -> None:
        clip = document.clip
        self.path_label.setText(str(document.source_path))
        self.path_label.setToolTip(str(document.source_path.resolve()))
        beats = float(clip.duration_quarter_notes)
        tempo_bpm = 60_000_000 / clip.tempo_at(0)
        numerator, denominator = clip.time_signature_at(0)
        warning_suffix = (
            f"  |  Warnings: {len(document.warnings)}" if document.warnings else ""
        )
        self.metadata_label.setText(
            f"Notes: {len(clip.notes)}  |  Tracks: {len(clip.tracks) or 1}  |  "
            f"Length: {beats:g} beats  |  Tempo: {tempo_bpm:.1f} BPM  |  "
            f"Meter: {numerator}/{denominator}{warning_suffix}"
        )
        self.metadata_label.setToolTip(
            "\n".join(document.warnings)
            if document.warnings
            else "No parser warnings."
        )

    def _reset_document_display(self) -> None:
        self.before_piano_roll.set_single_clip(None)
        self.after_piano_roll.set_single_clip(None)
        self._clear_suggestions()
        self._clear_repair_display()
        self._update_enabled()

    def _clear_suggestions(self) -> None:
        self.primary_suggestion_list.clear()
        self.secondary_suggestion_list.clear()
        self._suggestion_items.clear()
        self.secondary_toggle_button.setChecked(False)
        self.secondary_suggestion_panel.hide()
        self.secondary_toggle_button.setText("Show low-confidence suggestions (0)")
        self.suggestion_detail_label.setText(
            "Load a MIDI file to review possible pitch-repair suggestions."
        )

    def _clear_repair_display(self) -> None:
        self.musical_controls.clear()
        self.legacy_results.hide()
        self.repair_result = None
        self.last_repair_attempt = None
        self.score_summary_label.setText(
            "Estimated internal consistency before: -  |  after: -  |  improvement: -"
        )
        self.stop_reason_label.setText("No repair generated.")
        self.edit_list.clear()
        self.export_midi_button.setEnabled(False)
        self.export_json_button.setEnabled(False)
        if self.document is not None:
            self.after_piano_roll.set_single_clip(self.document.clip)
        else:
            self.after_piano_roll.set_single_clip(None)
        self.piano_roll_tabs.setTabEnabled(1, False)
        self.piano_roll_tabs.setCurrentIndex(0)

    def _update_enabled(self) -> None:
        ready = self.document is not None and self.analysis is not None
        has_enabled_suggestions = bool(self.enabled_suggestion_ids)
        permissions = self.musical_controls.permissions[0]
        has_permission = permissions.pitch or permissions.timing or permissions.duration
        can_repair = (
            ready
            and self.preservation < 100
            and has_permission
            and (has_enabled_suggestions or not self._suggestion_items
                 or permissions.timing or permissions.duration)
            and not self.is_busy
        )
        self.generate_button.setEnabled(can_repair)
        self.musical_controls.hint.setText(
            _FULLY_PRESERVED_MESSAGE if self.preservation == 100 else
            "Timing and Duration remain off unless you enable them.")
        self.select_all_button.setEnabled(
            bool(self._suggestion_items) and not self.is_busy
        )
        self.clear_all_button.setEnabled(
            bool(self._suggestion_items) and not self.is_busy
        )
        self.analysis_toggle_button.setEnabled(ready and not self.is_busy)
        self.secondary_toggle_button.setEnabled(
            self.secondary_suggestion_list.count() > 0 and not self.is_busy
        )
        self.export_midi_button.setEnabled(
            self.repair_result is not None and not self.is_busy
        )
        self.export_json_button.setEnabled(
            self.repair_result is not None and not self.is_busy
        )
        if self.repair_result is None and self.last_repair_attempt is None:
            if self.preservation == 100:
                self.generate_button.setToolTip(_FULLY_PRESERVED_MESSAGE)
                self.stop_reason_label.setText(_FULLY_PRESERVED_MESSAGE)
            elif ready and not has_enabled_suggestions:
                message = (
                    "Enable at least one suggestion before generating a repair."
                )
                self.generate_button.setToolTip(message)
                self.stop_reason_label.setText(message)
            elif ready:
                self.generate_button.setToolTip("")
            else:
                self.generate_button.setToolTip(
                    "Load a MIDI file before generating a repair."
                )

    def _require_document(self) -> MidiDocument:
        if self.document is None:
            raise RuntimeError("Load a MIDI file before analyzing or repairing")
        return self.document

    def _require_repair(self) -> SingleRepairResult:
        if self.repair_result is None:
            raise RuntimeError("Generate an improving repair before exporting")
        return self.repair_result

    def _show_status(self, message: str, timeout: int) -> None:
        if self._status_callback is not None:
            self._status_callback(message, timeout)


__all__ = ["SingleClipWorkflowWidget"]
