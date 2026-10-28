"""Main PySide6 shell for GLUE's single-clip and two-clip workflows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeVar, cast

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import (
    QApplication,
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
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from glue.analysis import (
    KeyEstimate,
    PairAnalysis,
    SingleClipAnalysis,
    analyze_pair,
    estimate_key,
)
from glue.exporting import (
    RepairExportPaths,
    RepairExportResult,
)
from glue.exporting import (
    export_change_report as write_change_report,
)
from glue.exporting import (
    export_combined_repair_preview as write_combined_repair_preview,
)
from glue.exporting import (
    export_repair_bundle as write_repair_bundle,
)
from glue.exporting import (
    export_revised_clip as write_revised_clip,
)
from glue.fixes import (
    BalanceSuggestion,
    EditingStrategy,
    NoteEdit,
    PairRepairResult,
    RepairPreset,
    SingleRepairResult,
    generate_pair_repair,
    suggest_preservation_balance,
)
from glue.fixes.musical import MusicalCandidate, MusicalRepair, generate_musical_repairs
from glue.io import (
    MidiDocument,
    load_midi,
    validate_for_analysis,
)
from glue.models import MidiClip

from .musical_controls import MusicalControls
from .single_workflow import SingleClipWorkflowWidget
from .visualizations import CompatibilityTimelineWidget, PianoRollWidget

ClipSlot = Literal["A", "B"]
_ResultT = TypeVar("_ResultT")
_BOTH_LOCKED_MESSAGE = (
    "Both clips are fully preserved. Lower at least one preservation value "
    "to generate a repair."
)


@dataclass(frozen=True, slots=True)
class _CandidatePreview:
    """One complete pair candidate plus its optional legacy export slot."""

    result: PairRepairResult
    repaired_slot: ClipSlot | None


class MainWindow(QMainWindow):
    """Coordinate file I/O, analysis, repair, export, and read-only displays."""

    def __init__(self) -> None:
        super().__init__()
        self.document_a: MidiDocument | None = None
        self.document_b: MidiDocument | None = None
        self.pair_analysis: PairAnalysis | None = None
        self.repair_result: PairRepairResult | None = None
        self.repaired_slot: ClipSlot | None = None
        self._repair_candidates: list[_CandidatePreview] = []
        self._analysis_cache: dict[tuple[MidiClip, MidiClip], PairAnalysis] = {}
        self._busy_depth = 0
        self._pending_balance_suggestion: BalanceSuggestion | None = None

        self.setWindowTitle("GLUE — MIDI Compatibility")
        self.resize(1180, 820)
        self.setMinimumSize(900, 650)
        self._build_ui()
        self._connect_signals()
        self._reset_analysis()

    @property
    def current_workflow(self) -> Literal["combine", "polish"]:
        """Return the workflow page currently shown."""

        return (
            "polish"
            if self.workflow_stack.currentWidget() is self.polish_page
            else "combine"
        )

    def select_combine_workflow(self) -> None:
        """Show the existing two-file workflow without changing its state."""

        self.workflow_stack.setCurrentWidget(self.combine_page)
        self.combine_workflow_button.setChecked(True)

    def select_polish_workflow(self) -> None:
        """Show the single-file workflow without changing its state."""

        self.workflow_stack.setCurrentWidget(self.polish_page)
        self.polish_workflow_button.setChecked(True)

    def load_single_clip(self, path: str | Path) -> MidiDocument:
        """Load one MIDI document into the Polish One Clip workflow."""

        self.select_polish_workflow()
        return self.polish_page.load_clip(path)

    def analyze_single_clip(self) -> SingleClipAnalysis:
        """Analyze the loaded Polish One Clip document."""

        self.select_polish_workflow()
        return self.polish_page.analyze()

    def repair_single_clip(self) -> SingleRepairResult:
        """Generate the currently requested Polish One Clip repair."""

        self.select_polish_workflow()
        return self.polish_page.generate_repair()

    def export_single_repaired(
        self,
        path: str | Path,
        *,
        overwrite: bool = False,
    ) -> Path:
        """Export the active single-file repaired MIDI."""

        return self.polish_page.export_repaired(path, overwrite=overwrite)

    def export_single_report(
        self,
        path: str | Path,
        *,
        overwrite: bool = False,
    ) -> Path:
        """Export the active single-file JSON report."""

        return self.polish_page.export_report(path, overwrite=overwrite)

    def load_clip(self, slot: ClipSlot | str, path: str | Path) -> MidiDocument:
        """Load one MIDI file into slot A or B without opening a dialog."""

        normalized_slot = self._normalize_slot(slot)
        document = validate_for_analysis(load_midi(path))
        self.select_combine_workflow()
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
        cache_key = (document_a.clip, document_b.clip)
        result = self._analysis_cache.get(cache_key)
        reused = result is not None
        if result is None:
            result = self._run_busy(
                "Analyzing compatibility…",
                lambda: analyze_pair(document_a.clip, document_b.clip),
            )
            # A small content-keyed cache handles repeated button events and
            # reloading the same immutable clips without growing indefinitely.
            if len(self._analysis_cache) >= 4:
                self._analysis_cache.pop(next(iter(self._analysis_cache)))
            self._analysis_cache[cache_key] = result
        self.pair_analysis = result
        if self.musical_controls.result is None:
            self._clear_candidate(restore_original=False)
            self.piano_roll.set_clips(document_a.clip, document_b.clip)
        self._display_analysis(result, update_keys=True)
        self._update_repair_enabled()
        status = (
            f"Analysis {'reused' if reused else 'complete'}: "
            f"{result.overall_score:.1f}/100."
            if _has_comparable_overlap(result)
            else (
                "Analysis reused: no comparable overlap."
                if reused
                else "Analysis complete: no comparable overlap."
            )
        )
        self.statusBar().showMessage(status, 5000)
        return result

    def repair_minimal(self) -> PairRepairResult:
        """Generate the backward-compatible V0.1 Minimal repair candidate."""

        return self._generate_repair_candidate(RepairPreset.MINIMAL)

    def repair_selected(self) -> PairRepairResult:
        """Generate and preview a repair using the selected UI controls."""

        return self._generate_repair_candidate(self.selected_preset)

    def repair_musical(self) -> MusicalRepair:
        """V0.5 interactive passage repair; legacy pitch-only APIs stay available."""
        documents = self._require_documents()
        self._clear_candidate(restore_original=True)
        result = self._run_busy(
            "Comparing bounded musical passages…",
            lambda: generate_musical_repairs(
                *(d.clip for d in documents), permissions=self.musical_controls.permissions,
                preservation=self._effective_preservation(), preset=self.selected_preset),
        )
        self.legacy_results.hide()
        self.musical_controls.display(result, documents)
        return result

    def _preview_musical(self, candidate: MusicalCandidate) -> None:
        documents = self._require_documents()
        self.piano_roll.set_pair_comparison(
            documents[0].clip, documents[1].clip, *candidate.clips)

    @property
    def pending_balance_suggestion(self) -> BalanceSuggestion | None:
        """Return the unapplied preservation suggestion, if one is previewed."""

        return self._pending_balance_suggestion

    def suggest_balance(self) -> BalanceSuggestion:
        """Analyze the loaded pair and preview a deterministic balance suggestion."""

        document_a, document_b = self._require_documents()
        analysis = self.pair_analysis or self.analyze()
        suggestion = self._run_busy(
            "Suggesting preservation balance…",
            lambda: suggest_preservation_balance(
                document_a.clip,
                document_b.clip,
                analysis,
            ),
        )
        if not suggestion.is_confident and (
            suggestion.preservation_a,
            suggestion.preservation_b,
        ) != (50, 50):
            suggestion = BalanceSuggestion(
                preservation_a=50,
                preservation_b=50,
                confidence=suggestion.confidence,
                explanation=(
                    "No strong recommendation: GLUE is previewing the balanced "
                    f"50/50 fallback. {suggestion.explanation}"
                ),
            )
        self._pending_balance_suggestion = suggestion
        confidence_text = (
            f"{suggestion.confidence_label} "
            f"({suggestion.confidence * 100:.0f}% confidence)"
        )
        prefix = (
            "Low-confidence balanced fallback"
            if not suggestion.is_confident
            else "Suggested preservation"
        )
        self.balance_suggestion_label.setText(
            f"{prefix}: A {suggestion.preservation_a}% · "
            f"B {suggestion.preservation_b}% · {confidence_text}.\n"
            f"{suggestion.explanation}\n"
            "Preview only—click Apply suggestion to change the sliders."
        )
        self.apply_suggestion_button.setEnabled(True)
        self.statusBar().showMessage(
            "Balance suggestion ready; preservation controls are unchanged.",
            5000,
        )
        return suggestion

    def apply_balance_suggestion(self) -> tuple[int, int]:
        """Apply the currently previewed suggestion to both sliders."""

        suggestion = self._pending_balance_suggestion
        if suggestion is None:
            raise RuntimeError("Generate a balance suggestion before applying it")
        values = (suggestion.preservation_a, suggestion.preservation_b)
        self.set_preservation_values(*values)
        self._pending_balance_suggestion = None
        self.apply_suggestion_button.setEnabled(False)
        self.balance_suggestion_label.setText(
            f"Applied preservation balance: A {values[0]}% · B {values[1]}%. "
            "You can still adjust either slider manually."
        )
        self.statusBar().showMessage("Applied the preservation suggestion.", 5000)
        return values

    @property
    def selected_preset(self) -> RepairPreset:
        """Return the preset selected in the repair controls."""

        index = self.preset_combo.currentIndex()
        presets = tuple(RepairPreset)
        if not 0 <= index < len(presets):
            raise RuntimeError("The selected repair preset is invalid")
        return presets[index]

    def set_preservation_values(
        self,
        preservation_a: int,
        preservation_b: int,
    ) -> None:
        """Set both preservation controls as one coordinated user action."""

        for name, value in (
            ("preservation_a", preservation_a),
            ("preservation_b", preservation_b),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer between 0 and 100")
            if not 0 <= value <= 100:
                raise ValueError(f"{name} must be between 0 and 100")
        blockers = (
            QSignalBlocker(self.preservation_a_slider),
            QSignalBlocker(self.preservation_b_slider),
        )
        try:
            self.preservation_a_slider.setValue(preservation_a)
            self.preservation_b_slider.setValue(preservation_b)
        finally:
            del blockers
        self._sync_preservation_labels()
        self._clear_active_candidate(restore_original=True)
        self._update_repair_enabled()

    @property
    def repair_candidate_count(self) -> int:
        """Return the number of retained repair candidates."""

        return len(self._repair_candidates)

    def _generate_repair_candidate(
        self,
        preset: RepairPreset,
    ) -> PairRepairResult:
        document_a, document_b = self._require_documents()
        preservation_a, preservation_b = self._effective_preservation()
        editable_a = preservation_a < 100 and _has_editable_pitched_notes(
            document_a.clip
        )
        editable_b = preservation_b < 100 and _has_editable_pitched_notes(
            document_b.clip
        )
        if not editable_a and not editable_b:
            if preservation_a == preservation_b == 100:
                raise RuntimeError(
                    "Both clips are fully preserved; lower preservation for at least "
                    "one clip before generating a repair"
                )
            raise RuntimeError("The editable MIDI clips have no pitched notes available")

        if self.pair_analysis is None:
            self.analyze()
        if self.pair_analysis is None or not _has_comparable_overlap(
            self.pair_analysis
        ):
            raise RuntimeError(
                "The clips have no comparable overlap to repair"
            )

        result = self._run_busy(
            f"Generating {preset.label} repair…",
            lambda: generate_pair_repair(
                document_a.clip,
                document_b.clip,
                strategy=EditingStrategy.CUSTOM,
                preset=preset,
                preservation_a=preservation_a,
                preservation_b=preservation_b,
            ),
        )
        if not self._is_improving_repair(result):
            self._display_no_improvement(result)
            return result

        repaired_slot = self._repaired_slot_from_edits(result)
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
            f"{preset.label} candidate generated with "
            f"{result.changed_note_count} pitch "
            f"change{'s' if result.changed_note_count != 1 else ''}.",
            5000,
        )
        return result

    @staticmethod
    def _is_improving_repair(result: PairRepairResult) -> bool:
        """Return whether a result is safe to present as a repair candidate."""

        engine_decision = getattr(result, "has_improvement", None)
        if engine_decision is not None:
            return bool(engine_decision)
        return result.changed_note_count > 0 and result.score_improvement > 1e-9

    def _display_no_improvement(self, result: PairRepairResult) -> None:
        """Explain a bounded search miss without retaining unchanged MIDI."""

        self._clear_active_candidate(restore_original=True)
        engine_reason = getattr(result, "no_improvement_reason", None)
        if not isinstance(engine_reason, str) or not engine_reason.strip():
            engine_reason = "No valid pitch edit improved the estimated result."
        elif "no valid pitch edit improved" not in engine_reason.lower():
            engine_reason = (
                f"{engine_reason.rstrip()} "
                "No valid pitch edit improved the estimated result."
            )
        self.candidate_label.setText(
            f"No improving {result.preset.label} candidate found.\n{engine_reason} "
            "Preservation may be too high, or the selected preset may be too "
            "restrictive."
        )
        self.repair_score_summary_label.setText(
            f"Estimated compatibility before: {result.original_score:.1f}/100  |  "
            "after: —  |  improvement: none"
        )
        self.edit_a_list.addItem("No improving pitch edit was retained for Clip A.")
        self.edit_b_list.addItem("No improving pitch edit was retained for Clip B.")
        self.statusBar().showMessage(
            "No improving candidate found; try lower preservation or a broader preset.",
            7000,
        )

    def _effective_preservation(self) -> tuple[int, int]:
        return (
            self.preservation_a_slider.value(),
            self.preservation_b_slider.value(),
        )

    @staticmethod
    def _repaired_slot_from_edits(result: PairRepairResult) -> ClipSlot | None:
        """Return the sole edited clip, independent of repair strategy labels."""

        if result.changed_note_count_a and not result.changed_note_count_b:
            return "A"
        if result.changed_note_count_b and not result.changed_note_count_a:
            return "B"
        return None

    def export_candidate(self, path: str | Path) -> Path:
        """Export the current repaired clip without opening a dialog."""

        if self.repair_result is None or self.repaired_slot is None:
            raise RuntimeError("Generate and select a repair candidate before exporting")
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
        document_a, document_b = self._require_documents()
        output_path = write_revised_clip(
            self.repair_result,
            document_a,
            document_b,
            self.repaired_slot,
            destination,
        )
        self.statusBar().showMessage(f"Exported repaired MIDI to {output_path}.", 7000)
        return output_path

    def export_revised_clip(
        self,
        slot: ClipSlot | str,
        path: str | Path,
        *,
        overwrite: bool = False,
    ) -> Path:
        """Export revised A or B without opening a dialog."""

        if self.repair_result is None:
            raise RuntimeError("Generate and select a repair candidate before exporting")
        document_a, document_b = self._require_documents()
        normalized = self._normalize_slot(slot)
        output = write_revised_clip(
            self.repair_result,
            document_a,
            document_b,
            normalized,
            path,
            overwrite=overwrite,
        )
        self.statusBar().showMessage(f"Exported revised Clip {normalized} to {output}.", 7000)
        return output

    def export_combined_preview(
        self,
        path: str | Path,
        *,
        overwrite: bool = False,
    ) -> Path:
        """Export the selected repaired pair on two preview tracks."""

        if self.repair_result is None:
            raise RuntimeError("Generate and select a repair candidate before exporting")
        document_a, document_b = self._require_documents()
        output = write_combined_repair_preview(
            self.repair_result,
            document_a,
            document_b,
            path,
            overwrite=overwrite,
        )
        self.statusBar().showMessage(f"Exported combined preview to {output}.", 7000)
        return output

    def export_change_report(
        self,
        path: str | Path,
        *,
        overwrite: bool = False,
    ) -> Path:
        """Export deterministic JSON for the selected candidate."""

        if self.repair_result is None:
            raise RuntimeError("Generate and select a repair candidate before exporting")
        document_a, document_b = self._require_documents()
        output = write_change_report(
            self.repair_result,
            document_a,
            document_b,
            path,
            overwrite=overwrite,
        )
        self.statusBar().showMessage(f"Exported change report to {output}.", 7000)
        return output

    def export_repair_bundle(
        self,
        base_path: str | Path,
        *,
        overwrite: bool = False,
    ) -> RepairExportResult:
        """Export revised A/B, combined preview, and JSON from one base name."""

        if self.repair_result is None:
            raise RuntimeError("Generate and select a repair candidate before exporting")
        document_a, document_b = self._require_documents()
        exported = write_repair_bundle(
            self.repair_result,
            document_a,
            document_b,
            RepairExportPaths.from_base(base_path),
            overwrite=overwrite,
        )
        self.statusBar().showMessage(
            f"Exported four repair artifacts beside {exported.revised_a}.",
            7000,
        )
        return exported

    def _build_ui(self) -> None:
        central = QWidget(self)
        root = QVBoxLayout(central)
        navigation = QHBoxLayout()
        navigation.addWidget(QLabel("Workflow:", central))
        self.combine_workflow_button = QPushButton(
            "Combine Two Clips",
            central,
        )
        self.combine_workflow_button.setObjectName(
            "combineTwoClipsWorkflowButton"
        )
        self.combine_workflow_button.setCheckable(True)
        self.combine_workflow_button.setToolTip(
            "Open the two-file compatibility and repair workflow."
        )
        self.polish_workflow_button = QPushButton("Polish One Clip", central)
        self.polish_workflow_button.setObjectName("polishOneClipWorkflowButton")
        self.polish_workflow_button.setCheckable(True)
        self.polish_workflow_button.setToolTip(
            "Analyze one MIDI clip, review suggestions, and export a pitch-only repair."
        )
        self.workflow_button_group = QButtonGroup(central)
        self.workflow_button_group.setExclusive(True)
        self.workflow_button_group.addButton(self.combine_workflow_button)
        self.workflow_button_group.addButton(self.polish_workflow_button)
        navigation.addWidget(self.combine_workflow_button)
        navigation.addWidget(self.polish_workflow_button)
        navigation.addStretch(1)
        root.addLayout(navigation)

        self.workflow_stack = QStackedWidget(central)
        self.workflow_stack.setObjectName("workflowStack")
        self.combine_page = self._build_combine_page(self.workflow_stack)
        self.polish_page = SingleClipWorkflowWidget(
            self.workflow_stack,
            status_callback=self.statusBar().showMessage,
        )
        self.workflow_stack.addWidget(self.combine_page)
        self.workflow_stack.addWidget(self.polish_page)
        self.workflow_stack.setCurrentWidget(self.combine_page)
        self.combine_workflow_button.setChecked(True)
        root.addWidget(self.workflow_stack)
        self.setCentralWidget(central)

    def _build_combine_page(self, parent: QWidget) -> QWidget:
        page = QWidget(parent)
        page.setObjectName("combineTwoClipsPage")
        root = QVBoxLayout(page)
        header = QHBoxLayout()
        title = QLabel("Combine Two Clips", page)
        title.setObjectName("combineWorkflowTitle")
        header.addWidget(title)
        header.addStretch(1)
        root.addLayout(header)
        root.addLayout(self._build_file_controls())

        self.analysis_details_panel = self._build_analysis_details(page)
        self.analysis_details_panel.setObjectName("analysisDetailsPanel")
        self.analysis_details_panel.hide()
        root.addWidget(self.analysis_details_panel)

        workspace = QSplitter(Qt.Orientation.Horizontal, page)
        workspace.setObjectName("workspaceSplitter")
        visual_panel = QWidget(workspace)
        visual_layout = QVBoxLayout(visual_panel)
        piano_group = QGroupBox("Overlay piano roll", visual_panel)
        piano_layout = QVBoxLayout(piano_group)
        self.piano_roll = PianoRollWidget(piano_group)
        self.piano_roll.setObjectName("pianoRoll")
        piano_layout.addWidget(self.piano_roll)
        visual_layout.addWidget(piano_group, 1)

        self.details_scroll_area = QScrollArea(workspace)
        self.details_scroll_area.setObjectName("detailsScrollArea")
        self.details_scroll_area.setWidgetResizable(True)
        self.details_scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        details_panel = QWidget(self.details_scroll_area)
        details_layout = QVBoxLayout(details_panel)
        self.repair_group = self._build_repair_group(details_panel)
        details_layout.addWidget(self.repair_group, 1)
        # Preserve usable list/control heights on smaller displays; the scroll
        # area, rather than the child layout, absorbs the vertical shortfall.
        details_panel.setMinimumHeight(details_panel.minimumSizeHint().height())
        details_panel.setMinimumWidth(1)
        details_panel.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred,
        )
        self.details_scroll_area.setWidget(details_panel)

        workspace.addWidget(visual_panel)
        workspace.addWidget(self.details_scroll_area)
        workspace.setStretchFactor(0, 5)
        workspace.setStretchFactor(1, 4)
        root.addWidget(workspace, 1)
        return page

    def _build_busy_row(self, parent: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        self.busy_status_label = QLabel("Ready", parent)
        self.busy_status_label.setObjectName("busyStatusLabel")
        row.addWidget(self.busy_status_label)
        self.busy_indicator = QProgressBar(parent)
        self.busy_indicator.setObjectName("busyIndicator")
        self.busy_indicator.setRange(0, 0)
        self.busy_indicator.setTextVisible(False)
        self.busy_indicator.setFixedWidth(96)
        self.busy_indicator.hide()
        row.addWidget(self.busy_indicator)
        row.addStretch(1)
        return row

    def _build_analysis_details(self, parent: QWidget) -> QWidget:
        panel = QWidget(parent)
        layout = QVBoxLayout(panel)

        key_group = QGroupBox("Estimated keys", panel)
        key_layout = QHBoxLayout(key_group)
        key_layout.addWidget(self.key_a_label)
        key_layout.addWidget(self.key_b_label)
        layout.addWidget(key_group)
        layout.addLayout(self._build_score_row())

        detail_row = QHBoxLayout()
        timeline_group = QGroupBox("Compatibility timeline", panel)
        timeline_layout = QVBoxLayout(timeline_group)
        self.timeline = CompatibilityTimelineWidget(timeline_group)
        self.timeline.setObjectName("compatibilityTimeline")
        self.timeline.setMinimumHeight(150)
        timeline_layout.addWidget(self.timeline)
        detail_row.addWidget(timeline_group, 3)

        diagnosis_group = QGroupBox("Diagnosis", panel)
        diagnosis_layout = QVBoxLayout(diagnosis_group)
        self.diagnosis_list = QListWidget(diagnosis_group)
        self.diagnosis_list.setObjectName("diagnosisList")
        self.diagnosis_list.setWordWrap(True)
        self.diagnosis_list.setMinimumHeight(120)
        diagnosis_layout.addWidget(self.diagnosis_list)
        detail_row.addWidget(diagnosis_group, 2)
        layout.addLayout(detail_row)
        return panel

    def _build_file_controls(self) -> QHBoxLayout:
        row = QHBoxLayout()
        group_a = self._build_clip_group("A")
        group_b = self._build_clip_group("B")
        row.addWidget(group_a)
        row.addWidget(group_b)

        self.compatibility_estimate_group = QGroupBox("Compatibility estimate")
        self.compatibility_estimate_group.setObjectName("compatibilityEstimateGroup")
        controls = QVBoxLayout(self.compatibility_estimate_group)
        self.analyze_button = QPushButton(
            "Estimate compatibility",
            self.compatibility_estimate_group,
        )
        self.analyze_button.setObjectName("analyzeButton")
        controls.addWidget(self.analyze_button)

        overall_row = QHBoxLayout()
        overall_row.addWidget(QLabel("Overall:", self.compatibility_estimate_group))
        self.overall_score_label = QLabel("—", self.compatibility_estimate_group)
        self.overall_score_label.setObjectName("overallScore")
        self.overall_score_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.overall_score_label.setMinimumWidth(90)
        overall_row.addWidget(self.overall_score_label, 1)
        controls.addLayout(overall_row)

        self.analysis_toggle_button = QPushButton(
            "Show analysis details",
            self.compatibility_estimate_group,
        )
        self.analysis_toggle_button.setObjectName("analysisDetailsToggle")
        self.analysis_toggle_button.setCheckable(True)
        self.analysis_toggle_button.setChecked(False)
        controls.addWidget(self.analysis_toggle_button)
        controls.addLayout(self._build_busy_row(self.compatibility_estimate_group))
        controls.addStretch(1)
        row.addWidget(
            self.compatibility_estimate_group,
            0,
            Qt.AlignmentFlag.AlignTop,
        )
        return row

    def _build_clip_group(self, slot: ClipSlot) -> QGroupBox:
        group = QGroupBox(f"MIDI {slot}")
        layout = QGridLayout(group)
        load_button = QPushButton(f"Load MIDI {slot}…", group)
        load_button.setObjectName(f"load{slot}Button")
        path_label = QLabel("No file loaded", group)
        path_label.setObjectName(f"path{slot}Label")
        path_label.setWordWrap(True)
        metadata_label = QLabel("Notes: —  |  Length: —  |  Tempo: —  |  Meter: —", group)
        metadata_label.setObjectName(f"metadata{slot}Label")
        metadata_label.setWordWrap(True)
        key_label = QLabel(f"Clip {slot} estimated key: —", group)
        key_label.setObjectName(f"key{slot}Label")

        layout.addWidget(load_button, 0, 0, 1, 2)
        layout.addWidget(path_label, 1, 0, 1, 2)
        layout.addWidget(metadata_label, 2, 0, 1, 2)
        layout.setColumnStretch(0, 1)

        if slot == "A":
            self.file_a_button = load_button
            self.path_a_label = path_label
            self.metadata_a_label = metadata_label
            self.key_a_label = key_label
        else:
            self.file_b_button = load_button
            self.path_b_label = path_label
            self.metadata_b_label = metadata_label
            self.key_b_label = key_label
        return group

    def _build_score_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
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
        group = QGroupBox("Repair workflow", parent)
        group.setObjectName("repairWorkflowGroup")
        layout = QVBoxLayout(group)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Preset:", group))
        self.preset_combo = QComboBox(group)
        self.preset_combo.setObjectName("repairPresetCombo")
        for preset in RepairPreset:
            self.preset_combo.addItem(preset.label, preset.value)
        preset_row.addWidget(self.preset_combo, 1)
        layout.addLayout(preset_row)

        (
            self.preservation_a_slider,
            self.preservation_a_value_label,
            self.preservation_a_locked_indicator,
        ) = self._build_preservation_row(layout, group, "A", 100)
        (
            self.preservation_b_slider,
            self.preservation_b_value_label,
            self.preservation_b_locked_indicator,
        ) = self._build_preservation_row(layout, group, "B", 100)
        shortcut_row = QHBoxLayout()
        shortcut_row.addWidget(QLabel("Quick balance:", group))
        self.keep_a_button = QPushButton("Keep A", group)
        self.keep_a_button.setObjectName("keepAShortcutButton")
        self.balanced_button = QPushButton("Balanced", group)
        self.balanced_button.setObjectName("balancedShortcutButton")
        self.keep_b_button = QPushButton("Keep B", group)
        self.keep_b_button.setObjectName("keepBShortcutButton")
        shortcut_row.addWidget(self.keep_a_button)
        shortcut_row.addWidget(self.balanced_button)
        shortcut_row.addWidget(self.keep_b_button)
        layout.addLayout(shortcut_row)

        suggestion_row = QHBoxLayout()
        self.suggest_balance_button = QPushButton("Suggest balance", group)
        self.suggest_balance_button.setObjectName("suggestBalanceButton")
        self.apply_suggestion_button = QPushButton("Apply suggestion", group)
        self.apply_suggestion_button.setObjectName("applyBalanceSuggestionButton")
        self.apply_suggestion_button.setEnabled(False)
        suggestion_row.addWidget(self.suggest_balance_button)
        suggestion_row.addWidget(self.apply_suggestion_button)
        layout.addLayout(suggestion_row)
        self.balance_suggestion_label = QLabel(
            "No balance suggestion yet. Your preservation values remain in control.",
            group,
        )
        self.balance_suggestion_label.setObjectName("balanceSuggestionSummary")
        self.balance_suggestion_label.setWordWrap(True)
        layout.addWidget(self.balance_suggestion_label)

        self.musical_controls = MusicalControls(2, group)
        self.musical_controls.permissions_changed.connect(
            lambda: self._clear_active_candidate(restore_original=True))
        self.musical_controls.permissions_changed.connect(self._update_repair_enabled)
        self.musical_controls.candidate_changed.connect(self._preview_musical)
        layout.addWidget(self.musical_controls)

        self.repair_button = QPushButton("Generate Minimal repair", group)
        self.repair_button.setObjectName("minimalRepairButton")
        self.candidate_list = QListWidget(group)
        self.candidate_list.setObjectName("candidateList")
        self.candidate_list.setWordWrap(True)
        self.candidate_list.setMaximumHeight(105)
        self.repair_score_summary_label = QLabel(
            "Estimated compatibility before: —  |  after: —  |  improvement: —",
            group,
        )
        self.repair_score_summary_label.setObjectName("repairCompatibilitySummary")
        self.repair_score_summary_label.setWordWrap(True)
        self.candidate_label = QLabel("No candidate generated.", group)
        self.candidate_label.setObjectName("candidateSummary")
        self.candidate_label.setWordWrap(True)
        self.edit_list = QListWidget(group)
        self.edit_list.setObjectName("editList")
        self.edit_list.setWordWrap(True)
        edit_rows = QHBoxLayout()
        edit_a_column = QVBoxLayout()
        edit_a_column.addWidget(QLabel("Clip A edits", group))
        self.edit_a_list = QListWidget(group)
        self.edit_a_list.setMinimumHeight(60)
        self.edit_a_list.setObjectName("editAList")
        self.edit_a_list.setWordWrap(True)
        edit_a_column.addWidget(self.edit_a_list)
        edit_b_column = QVBoxLayout()
        edit_b_column.addWidget(QLabel("Clip B edits", group))
        self.edit_b_list = QListWidget(group)
        self.edit_b_list.setMinimumHeight(60)
        self.edit_b_list.setObjectName("editBList")
        self.edit_b_list.setWordWrap(True)
        edit_b_column.addWidget(self.edit_b_list)
        edit_rows.addLayout(edit_a_column)
        edit_rows.addLayout(edit_b_column)
        self.export_button = QPushButton("Export repaired MIDI…", group)
        self.export_button.setObjectName("exportButton")
        export_grid = QGridLayout()
        self.export_a_button = QPushButton("Export revised A…", group)
        self.export_a_button.setObjectName("exportAButton")
        self.export_b_button = QPushButton("Export revised B…", group)
        self.export_b_button.setObjectName("exportBButton")
        self.export_combined_button = QPushButton("Export combined preview…", group)
        self.export_combined_button.setObjectName("exportCombinedButton")
        self.export_report_button = QPushButton("Export JSON report…", group)
        self.export_report_button.setObjectName("exportReportButton")
        self.export_bundle_button = QPushButton("Export all four artifacts…", group)
        self.export_bundle_button.setObjectName("exportBundleButton")
        export_grid.addWidget(self.export_a_button, 0, 0)
        export_grid.addWidget(self.export_b_button, 0, 1)
        export_grid.addWidget(self.export_combined_button, 1, 0)
        export_grid.addWidget(self.export_report_button, 1, 1)
        export_grid.addWidget(self.export_bundle_button, 2, 0, 1, 2)
        layout.addWidget(self.repair_button)
        layout.addWidget(self.musical_controls.results)
        self.legacy_results = QWidget(group)
        layout.addWidget(self.legacy_results)
        layout = QVBoxLayout(self.legacy_results)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.candidate_list)
        layout.addWidget(self.repair_score_summary_label)
        layout.addWidget(self.candidate_label)
        # Keep the original combined edit list available to V0.2 callers while
        # the visible pair lists make file ownership explicit.
        self.edit_list.hide()
        layout.addLayout(edit_rows, 1)
        layout.addWidget(self.edit_list)
        layout.addWidget(self.export_button)
        layout.addLayout(export_grid)
        return group

    @staticmethod
    def _build_preservation_row(
        layout: QVBoxLayout,
        parent: QWidget,
        slot: ClipSlot,
        value: int,
    ) -> tuple[QSlider, QLabel, QLabel]:
        row = QHBoxLayout()
        row.addWidget(QLabel(f"Preserve {slot}:", parent))
        slider = QSlider(Qt.Orientation.Horizontal, parent)
        slider.setObjectName(f"preservation{slot}Slider")
        slider.setRange(0, 100)
        slider.setValue(value)
        slider.setSingleStep(1)
        slider.setPageStep(10)
        slider.setToolTip(
            "Higher values make pitch edits to this clip more expensive; "
            "100% locks it."
        )
        value_label = QLabel(f"{value}%", parent)
        value_label.setObjectName(f"preservation{slot}Value")
        value_label.setMinimumWidth(42)
        locked_indicator = QLabel("Locked", parent)
        locked_indicator.setObjectName(f"preservation{slot}LockedIndicator")
        locked_indicator.setToolTip(
            f"Clip {slot} is fully preserved and will receive zero pitch edits."
        )
        locked_indicator.hide()
        row.addWidget(slider, 1)
        row.addWidget(value_label)
        row.addWidget(locked_indicator)
        layout.addLayout(row)
        return slider, value_label, locked_indicator

    def _connect_signals(self) -> None:
        self.polish_workflow_button.clicked.connect(
            self.select_polish_workflow
        )
        self.combine_workflow_button.clicked.connect(
            self.select_combine_workflow
        )
        self.file_a_button.clicked.connect(lambda _checked=False: self._choose_clip("A"))
        self.file_b_button.clicked.connect(lambda _checked=False: self._choose_clip("B"))
        self.analyze_button.clicked.connect(self._analyze_interactive)
        self.repair_button.clicked.connect(self._repair_interactive)
        self.keep_a_button.clicked.connect(
            lambda _checked=False: self.set_preservation_values(100, 0)
        )
        self.balanced_button.clicked.connect(
            lambda _checked=False: self.set_preservation_values(50, 50)
        )
        self.keep_b_button.clicked.connect(
            lambda _checked=False: self.set_preservation_values(0, 100)
        )
        self.suggest_balance_button.clicked.connect(
            self._suggest_balance_interactive
        )
        self.apply_suggestion_button.clicked.connect(
            self._apply_balance_suggestion_interactive
        )
        self.export_button.clicked.connect(self._export_interactive)
        self.export_a_button.clicked.connect(
            lambda _checked=False: self._export_revised_interactive("A")
        )
        self.export_b_button.clicked.connect(
            lambda _checked=False: self._export_revised_interactive("B")
        )
        self.export_combined_button.clicked.connect(
            self._export_combined_interactive
        )
        self.export_report_button.clicked.connect(self._export_report_interactive)
        self.export_bundle_button.clicked.connect(self._export_bundle_interactive)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        self.preservation_a_slider.valueChanged.connect(
            lambda value: self._on_preservation_changed("A", value)
        )
        self.preservation_b_slider.valueChanged.connect(
            lambda value: self._on_preservation_changed("B", value)
        )
        self.candidate_list.currentItemChanged.connect(
            self._on_candidate_item_changed
        )
        self.analysis_toggle_button.toggled.connect(
            self._on_analysis_details_toggled
        )
        self._sync_preservation_labels()

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
        if self.is_busy:
            return
        self._run_interactive("Could not analyze these MIDI files", self.analyze)

    def _repair_interactive(self) -> None:
        if self.is_busy:
            return
        self._run_interactive(
            f"Could not generate a {self.selected_preset.label} repair",
            self.repair_musical,
        )

    def _suggest_balance_interactive(self) -> None:
        if self.is_busy:
            return
        self._run_interactive(
            "Could not suggest a preservation balance",
            self.suggest_balance,
        )

    def _apply_balance_suggestion_interactive(self) -> None:
        if self.is_busy:
            return
        self._run_interactive(
            "Could not apply the preservation suggestion",
            self.apply_balance_suggestion,
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

    def _export_revised_interactive(self, slot: ClipSlot) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            f"Export revised Clip {slot}",
            f"glue_revised_{slot.lower()}.mid",
            "MIDI files (*.mid *.midi);;All files (*)",
        )
        if not filename:
            return
        destination = Path(filename)
        if destination.suffix.lower() not in {".mid", ".midi"}:
            destination = destination.with_suffix(".mid")
        overwrite = self._confirm_overwrite((destination,))
        if overwrite is None:
            return
        self._run_interactive(
            f"Could not export revised Clip {slot}",
            lambda: self.export_revised_clip(
                slot,
                destination,
                overwrite=overwrite,
            ),
        )

    def _export_combined_interactive(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export combined preview",
            "glue_combined.mid",
            "MIDI files (*.mid *.midi);;All files (*)",
        )
        if not filename:
            return
        destination = Path(filename)
        if destination.suffix.lower() not in {".mid", ".midi"}:
            destination = destination.with_suffix(".mid")
        overwrite = self._confirm_overwrite((destination,))
        if overwrite is None:
            return
        self._run_interactive(
            "Could not export combined preview",
            lambda: self.export_combined_preview(
                destination,
                overwrite=overwrite,
            ),
        )

    def _export_report_interactive(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export JSON change report",
            "glue_changes.json",
            "JSON files (*.json);;All files (*)",
        )
        if not filename:
            return
        destination = Path(filename)
        if destination.suffix.lower() != ".json":
            destination = destination.with_suffix(".json")
        overwrite = self._confirm_overwrite((destination,))
        if overwrite is None:
            return
        self._run_interactive(
            "Could not export change report",
            lambda: self.export_change_report(
                destination,
                overwrite=overwrite,
            ),
        )

    def _export_bundle_interactive(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Choose repair export base name",
            "glue_repair.mid",
            "MIDI files (*.mid *.midi);;All files (*)",
        )
        if not filename:
            return
        paths = RepairExportPaths.from_base(filename)
        overwrite = self._confirm_overwrite(paths.all_paths)
        if overwrite is None:
            return
        self._run_interactive(
            "Could not export repair artifacts",
            lambda: self.export_repair_bundle(filename, overwrite=overwrite),
        )

    def _confirm_overwrite(self, paths: tuple[Path, ...]) -> bool | None:
        existing = tuple(path for path in paths if path.exists())
        if not existing:
            return False
        names = "\n".join(str(path) for path in existing)
        answer = QMessageBox.warning(
            self,
            "Confirm export overwrite",
            "The following export files already exist and will be replaced:\n"
            f"{names}",
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

    @property
    def is_busy(self) -> bool:
        """Whether a foreground analysis or repair operation is active."""

        return self._busy_depth > 0

    def _run_busy(
        self,
        message: str,
        operation: Callable[[], _ResultT],
    ) -> _ResultT:
        """Run a synchronous operation with a visible, re-entry-safe indicator."""

        outermost = self._busy_depth == 0
        self._busy_depth += 1
        if outermost:
            self.musical_controls.setEnabled(False)
            self.busy_status_label.setText(message)
            self.busy_indicator.show()
            self.analyze_button.setEnabled(False)
            self.repair_button.setEnabled(False)
            self.suggest_balance_button.setEnabled(False)
            self.apply_suggestion_button.setEnabled(False)
            self.keep_a_button.setEnabled(False)
            self.balanced_button.setEnabled(False)
            self.keep_b_button.setEnabled(False)
            self.preservation_a_slider.setEnabled(False)
            self.preservation_b_slider.setEnabled(False)
            self.preset_combo.setEnabled(False)
            self.file_a_button.setEnabled(False)
            self.file_b_button.setEnabled(False)
            QApplication.processEvents()
        try:
            return operation()
        finally:
            self._busy_depth -= 1
            if outermost:
                self.musical_controls.setEnabled(True)
                self.busy_indicator.hide()
                self.busy_status_label.setText("Ready")
                self.file_a_button.setEnabled(True)
                self.file_b_button.setEnabled(True)
                self.preservation_a_slider.setEnabled(True)
                self.preservation_b_slider.setEnabled(True)
                self.preset_combo.setEnabled(True)
                self.keep_a_button.setEnabled(True)
                self.balanced_button.setEnabled(True)
                self.keep_b_button.setEnabled(True)
                self.analyze_button.setEnabled(
                    self.document_a is not None and self.document_b is not None
                )
                self._update_repair_enabled()

    def _on_analysis_details_toggled(self, expanded: bool) -> None:
        self.analysis_details_panel.setVisible(expanded)
        self.analysis_toggle_button.setText(
            "Hide analysis details" if expanded else "Show analysis details"
        )

    def _on_preset_changed(self, _index: int) -> None:
        self.repair_button.setText(
            f"Generate {self.selected_preset.label} repair"
        )
        self._clear_active_candidate(restore_original=True)

    def _on_preservation_changed(self, slot: ClipSlot, value: int) -> None:
        del slot, value
        self._sync_preservation_labels()
        self._clear_active_candidate(restore_original=True)
        self._update_repair_enabled()

    def _sync_preservation_labels(self) -> None:
        for slider, value_label, locked_indicator in (
            (
                self.preservation_a_slider,
                self.preservation_a_value_label,
                self.preservation_a_locked_indicator,
            ),
            (
                self.preservation_b_slider,
                self.preservation_b_value_label,
                self.preservation_b_locked_indicator,
            ),
        ):
            value = slider.value()
            value_label.setText(f"{value}%")
            locked_indicator.setVisible(value == 100)

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
        self.musical_controls.clear()
        self.legacy_results.show()
        document_a, document_b = self._require_documents()
        result = preview.result
        self.repair_result = result
        self.repaired_slot = preview.repaired_slot
        self._display_analysis(result.after_analysis, update_keys=False)
        self.timeline.set_comparison(
            result.before_analysis,
            result.after_analysis,
        )
        self.piano_roll.set_pair_comparison(
            document_a.clip,
            document_b.clip,
            result.repaired_clip_a,
            result.repaired_clip_b,
        )
        self._display_candidate(result)
        self.export_button.setEnabled(preview.repaired_slot is not None)
        for button in (
            self.export_a_button,
            self.export_b_button,
            self.export_combined_button,
            self.export_report_button,
            self.export_bundle_button,
        ):
            button.setEnabled(True)

    @staticmethod
    def _candidate_list_text(preview: _CandidatePreview) -> str:
        result = preview.result
        return (
            f"{result.preset.label} | preserve A "
            f"{result.preservation_a * 100:.0f}%, B "
            f"{result.preservation_b * 100:.0f}% | estimated "
            f"{result.original_score:.1f} → {result.repaired_score:.1f} "
            f"({result.score_improvement:+.1f}) | "
            f"A {result.changed_note_count_a}, B {result.changed_note_count_b} edits | "
            f"displacement {result.total_pitch_displacement}"
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
        self._set_key_label(key_label, estimate_key(clip), slot=slot)

    @staticmethod
    def _set_key_label(
        label: QLabel,
        estimate: KeyEstimate,
        *,
        slot: ClipSlot,
    ) -> None:
        label.setText(
            f"Clip {slot} estimated key: {estimate.label} "
            f"({estimate.confidence * 100:.0f}% confidence)"
        )

    def _reset_analysis(self) -> None:
        self.pair_analysis = None
        self._pending_balance_suggestion = None
        self.apply_suggestion_button.setEnabled(False)
        self.balance_suggestion_label.setText(
            "No balance suggestion yet. Your preservation values remain in control."
        )
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
        self._update_repair_enabled()

    def _clear_candidate(self, *, restore_original: bool) -> None:
        self._clear_active_candidate(restore_original=restore_original)
        self._repair_candidates.clear()
        self.candidate_list.clear()

    def _clear_active_candidate(self, *, restore_original: bool) -> None:
        self.musical_controls.clear()
        self.legacy_results.hide()
        self.repair_result = None
        self.repaired_slot = None
        self.candidate_list.setCurrentItem(None)
        self.candidate_label.setText("No candidate generated.")
        self.repair_score_summary_label.setText(
            "Estimated compatibility before: —  |  after: —  |  improvement: —"
        )
        self.edit_list.clear()
        self.edit_a_list.clear()
        self.edit_b_list.clear()
        self.export_button.setEnabled(False)
        for button in (
            self.export_a_button,
            self.export_b_button,
            self.export_combined_button,
            self.export_report_button,
            self.export_bundle_button,
        ):
            button.setEnabled(False)
        if restore_original:
            if self.pair_analysis is not None:
                self._display_analysis(self.pair_analysis, update_keys=False)
            self.piano_roll.set_clips(
                self.document_a.clip if self.document_a is not None else None,
                self.document_b.clip if self.document_b is not None else None,
            )

    def _update_repair_enabled(self) -> None:
        preservation_a, preservation_b = self._effective_preservation()
        editable = (
            preservation_a < 100
            and _has_editable_pitched_notes(
                self.document_a.clip if self.document_a is not None else None
            )
        ) or (
            preservation_b < 100
            and _has_editable_pitched_notes(
                self.document_b.clip if self.document_b is not None else None
            )
        )
        documents_ready = self.document_a is not None and self.document_b is not None
        overlap_allows_repair = self.pair_analysis is None or _has_comparable_overlap(
            self.pair_analysis
        )
        enabled = documents_ready and overlap_allows_repair and editable
        enabled = enabled and any(
            preserve < 100 and (allow.pitch or allow.timing or allow.duration)
            for preserve, allow in zip(self._effective_preservation(),
                                       self.musical_controls.permissions, strict=True))
        if self.is_busy:
            enabled = False
        self.repair_button.setEnabled(enabled)
        self.suggest_balance_button.setEnabled(documents_ready and not self.is_busy)
        self.apply_suggestion_button.setEnabled(
            self._pending_balance_suggestion is not None and not self.is_busy
        )
        if preservation_a == preservation_b == 100:
            self.musical_controls.hint.setText(_BOTH_LOCKED_MESSAGE)
            self.repair_button.setToolTip(_BOTH_LOCKED_MESSAGE)
            if self.repair_result is None:
                self.candidate_label.setText(_BOTH_LOCKED_MESSAGE)
        else:
            self.musical_controls.hint.setText(
                "Timing and Duration remain off unless you enable them.")
            self.repair_button.setToolTip(
                "Compatibility will be estimated automatically before repair."
                if enabled and self.pair_analysis is None
                else ""
            )
            if (
                self.repair_result is None
                and self.candidate_label.text() == _BOTH_LOCKED_MESSAGE
            ):
                self.candidate_label.setText("No candidate generated.")

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
            self._set_key_label(self.key_a_label, result.key_a, slot="A")
            self._set_key_label(self.key_b_label, result.key_b, slot="B")

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

    def _display_candidate(self, result: PairRepairResult) -> None:
        if _has_comparable_overlap(result.before_analysis):
            self.repair_score_summary_label.setText(
                f"Estimated compatibility before: {result.original_score:.1f}/100  |  "
                f"after: {result.repaired_score:.1f}/100  |  "
                f"improvement: {result.score_improvement:+.1f}"
            )
            self.candidate_label.setText(
                f"{result.preset.label} repair\n"
                f"Clip A: {result.changed_note_count_a} changed, "
                f"{result.retention_a * 100:.1f}% retained, "
                f"preservation {result.preservation_a * 100:.0f}%  |  "
                f"Clip B: {result.changed_note_count_b} changed, "
                f"{result.retention_b * 100:.1f}% retained, "
                f"preservation {result.preservation_b * 100:.0f}%\n"
                f"Total: {result.changed_note_count} changed, "
                f"{result.total_pitch_displacement} semitones displacement"
            )
        else:
            self.candidate_label.setText(
                f"{result.preset.label} repair: no comparable overlap"
            )
        self.edit_list.clear()
        self.edit_a_list.clear()
        self.edit_b_list.clear()
        self._populate_edit_list(
            "A",
            result.original_clip_a,
            result.edits_a,
            self.edit_a_list,
        )
        self._populate_edit_list(
            "B",
            result.original_clip_b,
            result.edits_b,
            self.edit_b_list,
        )
        for slot, clip, edits in (
            ("A", result.original_clip_a, result.edits_a),
            ("B", result.original_clip_b, result.edits_b),
        ):
            original_by_id = {note.id: note for note in clip.notes}
            for edit in edits:
                note = original_by_id[edit.note_id]
                onset = note.onset_ticks / clip.ticks_per_beat
                self.edit_list.addItem(
                    f"Clip {slot}: {self._edit_description(edit, onset)}"
                )

    def _populate_edit_list(
        self,
        slot: ClipSlot,
        clip: MidiClip,
        edits: tuple[NoteEdit, ...],
        widget: QListWidget,
    ) -> None:
        if not edits:
            widget.addItem(f"Clip {slot} unchanged.")
            return
        original_by_id = {note.id: note for note in clip.notes}
        for edit in edits:
            note = original_by_id[edit.note_id]
            onset = note.onset_ticks / clip.ticks_per_beat
            widget.addItem(self._edit_description(edit, onset))

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
