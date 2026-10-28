"""Deterministic, suggestion-constrained repair for one MIDI clip.

The optimizer deliberately reuses GLUE's existing repair presets, calibrated
preservation/search bounds, pitch-only edit model, and collision/contour/motif
guards.  Single-clip analysis supplies the editable notes and musically
qualified alternatives; every candidate is then rescored as a complete clip.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass, field, replace
from itertools import combinations
from typing import TypeAlias

from glue.analysis import (
    DEFAULT_SINGLE_ANALYSIS_CONFIG,
    SingleAnalysisConfig,
    SingleClipAnalysis,
    SingleClipSuggestion,
    analyze_single_clip,
)
from glue.models import MidiClip

from .config import (
    EditingStrategy,
    JointObjectiveWeights,
    JointSearchBounds,
    pair_repair_config_for,
)
from .minimal import ALLOWED_MINIMAL_DELTAS, NoteEdit, RepairPreset
from .minimal import _contour_disruption as _shared_contour_disruption
from .minimal import _introduces_pitch_collision as _shared_collision_guard
from .pair import _motif_disruption as _shared_motif_disruption
from .pair import _ordinary_disruption_scale as _shared_disruption_scale

_EPSILON = 1e-9
SuggestionSelection: TypeAlias = Collection[str] | None


@dataclass(frozen=True, slots=True)
class SingleRepairConfig:
    """Immutable one-clip policy derived from the shared preset calibration."""

    preset: RepairPreset
    preservation: int
    maximum_note_changes: int
    search: JointSearchBounds
    objective: JointObjectiveWeights = field(
        default_factory=JointObjectiveWeights
    )

    def __post_init__(self) -> None:
        if not isinstance(self.preset, RepairPreset):
            raise TypeError("preset must be a RepairPreset")
        if isinstance(self.preservation, bool) or not isinstance(
            self.preservation,
            int,
        ):
            raise TypeError("preservation must be an integer between 0 and 100")
        if not 0 <= self.preservation <= 100:
            raise ValueError("preservation must be between 0 and 100")
        if (
            isinstance(self.maximum_note_changes, bool)
            or not isinstance(self.maximum_note_changes, int)
        ):
            raise TypeError("maximum_note_changes must be an integer")
        if self.maximum_note_changes < 0:
            raise ValueError("maximum_note_changes must be non-negative")
        if not isinstance(self.search, JointSearchBounds):
            raise TypeError("search must be JointSearchBounds")
        if not isinstance(self.objective, JointObjectiveWeights):
            raise TypeError("objective must be JointObjectiveWeights")
        if self.preservation == 100 and self.maximum_note_changes:
            raise ValueError("100% preservation requires a zero edit budget")

    @property
    def is_locked(self) -> bool:
        """Return whether preservation prohibits every pitch edit."""

        return self.preservation == 100 or self.maximum_note_changes == 0

    @property
    def preservation_fraction(self) -> float:
        """Return preservation on the shared normalized 0-1 scale."""

        return self.preservation / 100.0

    @property
    def minimum_suggestion_confidence(self) -> float:
        """Return the preset's conservative suggestion admission threshold."""

        return {
            RepairPreset.MINIMAL: 0.65,
            RepairPreset.BALANCED: 0.50,
            RepairPreset.CREATIVE: 0.0,
        }[self.preset]

    @property
    def maximum_bundle_size(self) -> int:
        """Return coordinated-search depth for this preset.

        Minimal stays atomic, Balanced admits pairs, and Creative can use the
        full preservation-calibrated coordinated pool.
        """

        if self.preset is RepairPreset.MINIMAL:
            return 1
        if self.preset is RepairPreset.BALANCED:
            return min(2, self.search.coordinated_options_per_clip)
        return self.search.coordinated_options_per_clip


def _normalize_preset(preset: RepairPreset | str) -> RepairPreset:
    if isinstance(preset, RepairPreset):
        return preset
    if not isinstance(preset, str):
        raise TypeError("preset must be a RepairPreset or string")
    try:
        return RepairPreset(preset.strip().lower())
    except ValueError as exc:
        choices = ", ".join(item.value for item in RepairPreset)
        raise ValueError(f"preset must be one of: {choices}") from exc


def single_repair_config_for(
    preset: RepairPreset | str = RepairPreset.MINIMAL,
    preservation: int = 50,
) -> SingleRepairConfig:
    """Build one-clip bounds from the existing preservation/preset policy."""

    if isinstance(preservation, bool) or not isinstance(preservation, int):
        raise TypeError("preservation must be an integer between 0 and 100")
    if not 0 <= preservation <= 100:
        raise ValueError("preservation must be between 0 and 100")
    resolved_preset = _normalize_preset(preset)
    # Locking the unused A side turns the shared interpolation into a one-side
    # budget without maintaining a second table of preset constants.
    pair_config = pair_repair_config_for(
        EditingStrategy.CUSTOM,
        resolved_preset,
        preservation_a=100,
        preservation_b=preservation,
    )
    return SingleRepairConfig(
        preset=resolved_preset,
        preservation=preservation,
        maximum_note_changes=pair_config.clip_b.max_note_changes,
        search=pair_config.search,
        objective=pair_config.objective,
    )


DEFAULT_SINGLE_REPAIR_CONFIG = single_repair_config_for()


@dataclass(frozen=True, slots=True)
class SingleRepairResult:
    """One complete single-clip search outcome.

    An unchanged result is useful evidence about a bounded search, but
    :attr:`has_improvement` remains false so a UI cannot present it as a
    successful repair.
    """

    original_clip: MidiClip
    repaired_clip: MidiClip
    before_analysis: SingleClipAnalysis
    after_analysis: SingleClipAnalysis
    edits: tuple[NoteEdit, ...]
    repair_config: SingleRepairConfig
    enabled_suggestion_ids: frozenset[str]
    edit_suggestion_ids: tuple[tuple[int, tuple[str, ...]], ...] = ()
    analysis_config: SingleAnalysisConfig = DEFAULT_SINGLE_ANALYSIS_CONFIG
    objective_cost: float = 0.0
    objective_gain: float = 0.0
    states_evaluated: int = 0
    stop_reason: str = ""

    def __post_init__(self) -> None:
        if self.states_evaluated < 0:
            raise ValueError("states_evaluated must be non-negative")
        if not isinstance(self.stop_reason, str) or not self.stop_reason.strip():
            raise ValueError("stop_reason must be a non-empty string")
        original_by_id = {note.id: note for note in self.original_clip.notes}
        repaired_by_id = {note.id: note for note in self.repaired_clip.notes}
        if original_by_id.keys() != repaired_by_id.keys():
            raise ValueError("repaired clip changed note identities")
        edit_by_id = {edit.note_id: edit for edit in self.edits}
        if len(edit_by_id) != len(self.edits):
            raise ValueError("single repair contains duplicate edits")
        for note_id, original in original_by_id.items():
            repaired = repaired_by_id[note_id]
            edit = edit_by_id.get(note_id)
            if edit is None:
                if repaired != original:
                    raise ValueError(
                        f"repaired clip changed note {note_id} without an edit"
                    )
                continue
            if edit.original_pitch != original.pitch:
                raise ValueError(f"edit {note_id} has the wrong source pitch")
            if edit.repaired_pitch != repaired.pitch:
                raise ValueError(f"edit {note_id} has the wrong final pitch")
            if repaired != replace(original, pitch=edit.repaired_pitch):
                raise ValueError(f"repair changed non-pitch fields for note {note_id}")
        provenance_ids = tuple(note_id for note_id, _ in self.edit_suggestion_ids)
        if len(provenance_ids) != len(set(provenance_ids)):
            raise ValueError("edit suggestion provenance contains duplicate note ids")
        if set(provenance_ids) != set(edit_by_id):
            raise ValueError("every edit requires suggestion provenance")
        for _, suggestion_ids in self.edit_suggestion_ids:
            if (
                not suggestion_ids
                or tuple(sorted(set(suggestion_ids))) != suggestion_ids
                or not set(suggestion_ids) <= self.enabled_suggestion_ids
            ):
                raise ValueError(
                    "edit suggestion provenance must be sorted, enabled, and non-empty"
                )

    @property
    def preset(self) -> RepairPreset:
        return self.repair_config.preset

    @property
    def preservation(self) -> int:
        return self.repair_config.preservation

    @property
    def changed_note_count(self) -> int:
        return len(self.edits)

    @property
    def original_score(self) -> float:
        return self.before_analysis.internal_consistency_score

    @property
    def repaired_score(self) -> float:
        return self.after_analysis.internal_consistency_score

    @property
    def score_improvement(self) -> float:
        return self.repaired_score - self.original_score

    @property
    def retention(self) -> float:
        editable = sum(
            not note.is_percussion and note.duration_ticks > 0
            for note in self.original_clip.notes
        )
        return 1.0 if not editable else 1.0 - self.changed_note_count / editable

    @property
    def has_improvement(self) -> bool:
        return self.changed_note_count > 0 and self.score_improvement > _EPSILON

    @property
    def is_improving(self) -> bool:
        return self.has_improvement

    @property
    def no_improvement_reason(self) -> str | None:
        return None if self.has_improvement else self.stop_reason

    @property
    def before(self) -> SingleClipAnalysis:
        return self.before_analysis

    @property
    def after(self) -> SingleClipAnalysis:
        return self.after_analysis

    def suggestion_ids_for_edit(self, note_id: int) -> tuple[str, ...]:
        """Return enabled suggestions authorizing one retained note edit."""

        return next(
            (
                suggestion_ids
                for candidate_id, suggestion_ids in self.edit_suggestion_ids
                if candidate_id == note_id
            ),
            (),
        )


@dataclass(frozen=True, slots=True)
class _NotePlan:
    note_id: int
    alternatives: tuple[int, ...]
    suggestion_ids_by_pitch: tuple[tuple[int, tuple[str, ...]], ...]

    def suggestion_ids(self, pitch: int) -> tuple[str, ...]:
        return next(
            suggestion_ids
            for candidate, suggestion_ids in self.suggestion_ids_by_pitch
            if candidate == pitch
        )


@dataclass(frozen=True, slots=True)
class _AtomicOption:
    note_id: int
    original_pitch: int
    repaired_pitch: int
    suggestion_ids: tuple[str, ...]
    clip: MidiClip
    analysis: SingleClipAnalysis
    score_change: float
    penalty: float

    @property
    def delta(self) -> int:
        return self.repaired_pitch - self.original_pitch


@dataclass(frozen=True, slots=True)
class _SingleState:
    clip: MidiClip
    analysis: SingleClipAnalysis
    edits: tuple[NoteEdit, ...]
    edit_sources: tuple[tuple[int, tuple[str, ...]], ...]
    objective_cost: float

    @property
    def total_edits(self) -> int:
        return len(self.edits)


@dataclass(slots=True)
class _EvaluationBudget:
    maximum: int
    used: int = 1

    @property
    def exhausted(self) -> bool:
        return self.used >= self.maximum


def _replace_pitch(clip: MidiClip, note_id: int, pitch: int) -> MidiClip:
    return clip.with_notes(
        replace(note, pitch=pitch) if note.id == note_id else note
        for note in clip.notes
    )


def _edit_limit(clip: MidiClip, config: SingleRepairConfig) -> int:
    pitched = sum(
        not note.is_percussion and note.duration_ticks > 0 for note in clip.notes
    )
    if not pitched or config.is_locked:
        return 0
    fractional = max(1, int(pitched * config.search.maximum_change_fraction))
    return min(
        config.maximum_note_changes,
        config.search.maximum_total_edits,
        fractional,
    )


def _allowed_delta(delta: int, preset: RepairPreset) -> bool:
    distance = abs(delta)
    if not 1 <= distance <= 12:
        return False
    if preset is RepairPreset.MINIMAL:
        return delta in ALLOWED_MINIMAL_DELTAS
    if preset is RepairPreset.BALANCED:
        return distance <= 4 or distance == 12
    return True


def _suggestion_rank(suggestion: SingleClipSuggestion) -> tuple[object, ...]:
    return (
        -round(suggestion.confidence, 12),
        suggestion.onset_ticks,
        suggestion.track,
        suggestion.channel,
        suggestion.target_note_id,
        suggestion.category.value,
        suggestion.suggestion_id,
    )


def _resolve_enabled_ids(
    analysis: SingleClipAnalysis,
    enabled_suggestion_ids: SuggestionSelection,
) -> frozenset[str]:
    available = frozenset(
        suggestion.suggestion_id for suggestion in analysis.suggestions
    )
    if enabled_suggestion_ids is None:
        return analysis.default_enabled_suggestion_ids
    if isinstance(enabled_suggestion_ids, (str, bytes)):
        raise TypeError("enabled_suggestion_ids must be a collection of strings")
    resolved = frozenset(enabled_suggestion_ids)
    if any(not isinstance(suggestion_id, str) for suggestion_id in resolved):
        raise TypeError("enabled_suggestion_ids must contain only strings")
    unknown = sorted(resolved - available)
    if unknown:
        raise ValueError(f"unknown enabled suggestion id: {unknown[0]}")
    return resolved


def _build_note_plans(
    clip: MidiClip,
    analysis: SingleClipAnalysis,
    enabled_ids: frozenset[str],
    config: SingleRepairConfig,
) -> tuple[_NotePlan, ...]:
    original_by_id = {note.id: note for note in clip.notes}
    grouped: dict[int, list[SingleClipSuggestion]] = {}
    for suggestion in sorted(analysis.suggestions, key=_suggestion_rank):
        if (
            suggestion.suggestion_id not in enabled_ids
            or suggestion.confidence + _EPSILON
            < config.minimum_suggestion_confidence
        ):
            continue
        note = original_by_id.get(suggestion.target_note_id)
        if (
            note is None
            or note.is_percussion
            or note.duration_ticks <= 0
            or note.pitch != suggestion.original_pitch
        ):
            continue
        grouped.setdefault(note.id, []).append(suggestion)

    plans: list[_NotePlan] = []
    for note_id, suggestions in grouped.items():
        note = original_by_id[note_id]
        pitch_sources: dict[int, set[str]] = {}
        ordered_pitches: list[int] = []
        for suggestion in suggestions:
            for pitch in suggestion.alternatives:
                if not _allowed_delta(pitch - note.pitch, config.preset):
                    continue
                if pitch not in pitch_sources:
                    pitch_sources[pitch] = set()
                    ordered_pitches.append(pitch)
                pitch_sources[pitch].add(suggestion.suggestion_id)
        alternatives = tuple(
            ordered_pitches[: config.search.candidate_pitches_per_note]
        )
        if not alternatives:
            continue
        plans.append(
            _NotePlan(
                note_id=note_id,
                alternatives=alternatives,
                suggestion_ids_by_pitch=tuple(
                    (pitch, tuple(sorted(pitch_sources[pitch])))
                    for pitch in alternatives
                ),
            )
        )
    return tuple(plans[: config.search.candidate_notes_per_clip])


def _single_edit_penalty(
    original: MidiClip,
    note_id: int,
    repaired_pitch: int,
    config: SingleRepairConfig,
) -> float:
    index = next(
        index for index, note in enumerate(original.notes) if note.id == note_id
    )
    note = original.notes[index]
    delta = repaired_pitch - note.pitch
    weights = config.objective
    ordinary_scale = _shared_disruption_scale(config.preservation_fraction)
    return (
        ordinary_scale
        * (
            weights.edit_count
            + weights.semitone_distance * abs(delta)
            + (weights.octave if abs(delta) == 12 else 0.0)
            + weights.contour
            * _shared_contour_disruption(original.notes, index, repaired_pitch)
            + weights.motif
            * _shared_motif_disruption(original, frozenset((note_id,)))
        )
        + weights.preservation * config.preservation_fraction**2
    )


def _objective_cost(
    original: MidiClip,
    repaired: MidiClip,
    analysis: SingleClipAnalysis,
    edits: tuple[NoteEdit, ...],
    config: SingleRepairConfig,
) -> float:
    weights = config.objective
    if not edits:
        disruption = 0.0
    else:
        original_index = {
            note.id: index for index, note in enumerate(original.notes)
        }
        repaired_by_id = {note.id: note for note in repaired.notes}
        edit_ids = frozenset(edit.note_id for edit in edits)
        ordinary_scale = _shared_disruption_scale(
            config.preservation_fraction
        )
        contour = sum(
            _shared_contour_disruption(
                original.notes,
                original_index[edit.note_id],
                repaired_by_id[edit.note_id].pitch,
            )
            for edit in edits
        )
        disruption = (
            ordinary_scale
            * (
                len(edits) * weights.edit_count
                + sum(edit.semitone_distance for edit in edits)
                * weights.semitone_distance
                + sum(edit.is_octave_move for edit in edits) * weights.octave
                + contour * weights.contour
                + _shared_motif_disruption(original, edit_ids) * weights.motif
            )
            + len(edits)
            * weights.preservation
            * config.preservation_fraction**2
        )
    return (
        (100.0 - analysis.internal_consistency_score)
        * weights.remaining_conflict
        + disruption
    )


def _state_signature(
    state: _SingleState,
) -> tuple[tuple[int, int], ...]:
    return tuple(
        sorted((edit.note_id, edit.repaired_pitch) for edit in state.edits)
    )


def _state_rank(state: _SingleState) -> tuple[object, ...]:
    return (
        round(state.objective_cost, 12),
        -round(state.analysis.internal_consistency_score, 12),
        state.total_edits,
        sum(edit.semitone_distance for edit in state.edits),
        _state_signature(state),
    )


def _option_rank(option: _AtomicOption) -> tuple[object, ...]:
    return (
        -round(option.score_change, 12),
        round(option.penalty, 12),
        abs(option.delta),
        option.note_id,
        option.repaired_pitch,
        option.suggestion_ids,
    )


def _atomic_options(
    state: _SingleState,
    original: MidiClip,
    plans: tuple[_NotePlan, ...],
    config: SingleRepairConfig,
    analysis_config: SingleAnalysisConfig,
    budget: _EvaluationBudget,
) -> tuple[_AtomicOption, ...]:
    edited_ids = frozenset(edit.note_id for edit in state.edits)
    current_by_id = {note.id: note for note in state.clip.notes}
    original_pitch_by_id: Mapping[int, int] = {
        note.id: note.pitch for note in original.notes
    }
    options: list[_AtomicOption] = []
    for plan in plans:
        if plan.note_id in edited_ids:
            continue
        note = current_by_id[plan.note_id]
        for pitch in plan.alternatives:
            if budget.exhausted:
                return tuple(sorted(options, key=_option_rank))
            if _shared_collision_guard(
                note,
                pitch,
                state.clip.notes,
                original_pitch_by_id,
            ):
                continue
            candidate_clip = _replace_pitch(state.clip, note.id, pitch)
            budget.used += 1
            candidate_analysis = analyze_single_clip(
                candidate_clip,
                config=analysis_config,
            )
            options.append(
                _AtomicOption(
                    note_id=note.id,
                    original_pitch=original_pitch_by_id[note.id],
                    repaired_pitch=pitch,
                    suggestion_ids=plan.suggestion_ids(pitch),
                    clip=candidate_clip,
                    analysis=candidate_analysis,
                    score_change=(
                        candidate_analysis.internal_consistency_score
                        - state.analysis.internal_consistency_score
                    ),
                    penalty=_single_edit_penalty(
                        original,
                        note.id,
                        pitch,
                        config,
                    ),
                )
            )
    return tuple(sorted(options, key=_option_rank))


def _atomic_successor(
    state: _SingleState,
    option: _AtomicOption,
    original: MidiClip,
    config: SingleRepairConfig,
) -> _SingleState | None:
    if (
        option.score_change + _EPSILON
        < config.search.minimum_score_improvement
        or option.score_change <= _EPSILON
    ):
        return None
    edit = NoteEdit(
        note_id=option.note_id,
        original_pitch=option.original_pitch,
        repaired_pitch=option.repaired_pitch,
        score_improvement=option.score_change,
        penalty=option.penalty,
        objective_gain=option.score_change - option.penalty,
        preset=config.preset,
    )
    edits = (*state.edits, edit)
    sources = (*state.edit_sources, (option.note_id, option.suggestion_ids))
    return _SingleState(
        clip=option.clip,
        analysis=option.analysis,
        edits=edits,
        edit_sources=sources,
        objective_cost=_objective_cost(
            original,
            option.clip,
            option.analysis,
            edits,
            config,
        ),
    )


def _bundle_state(
    state: _SingleState,
    bundle: tuple[_AtomicOption, ...],
    original: MidiClip,
    config: SingleRepairConfig,
    analysis_config: SingleAnalysisConfig,
    budget: _EvaluationBudget,
) -> _SingleState | None:
    if budget.exhausted or len(bundle) < 2:
        return None
    if len({option.note_id for option in bundle}) != len(bundle):
        return None
    original_pitch_by_id = {note.id: note.pitch for note in original.notes}
    candidate_clip = state.clip
    for option in bundle:
        note = next(
            note for note in candidate_clip.notes if note.id == option.note_id
        )
        if _shared_collision_guard(
            note,
            option.repaired_pitch,
            candidate_clip.notes,
            original_pitch_by_id,
        ):
            return None
        candidate_clip = _replace_pitch(
            candidate_clip,
            option.note_id,
            option.repaired_pitch,
        )
    budget.used += 1
    candidate_analysis = analyze_single_clip(
        candidate_clip,
        config=analysis_config,
    )
    score_change = (
        candidate_analysis.internal_consistency_score
        - state.analysis.internal_consistency_score
    )
    if (
        score_change + _EPSILON
        < config.search.minimum_score_improvement
        or score_change <= _EPSILON
    ):
        return None
    share = score_change / len(bundle)
    new_edits = tuple(
        NoteEdit(
            note_id=option.note_id,
            original_pitch=option.original_pitch,
            repaired_pitch=option.repaired_pitch,
            score_improvement=share,
            penalty=option.penalty,
            objective_gain=share - option.penalty,
            preset=config.preset,
        )
        for option in bundle
    )
    edits = (*state.edits, *new_edits)
    sources = (
        *state.edit_sources,
        *((option.note_id, option.suggestion_ids) for option in bundle),
    )
    return _SingleState(
        clip=candidate_clip,
        analysis=candidate_analysis,
        edits=edits,
        edit_sources=sources,
        objective_cost=_objective_cost(
            original,
            candidate_clip,
            candidate_analysis,
            edits,
            config,
        ),
    )


def _coordinated_successors(
    state: _SingleState,
    options: tuple[_AtomicOption, ...],
    original: MidiClip,
    edit_limit: int,
    config: SingleRepairConfig,
    analysis_config: SingleAnalysisConfig,
    budget: _EvaluationBudget,
) -> tuple[_SingleState, ...]:
    remaining = min(
        edit_limit - state.total_edits,
        config.maximum_bundle_size,
    )
    if remaining < 2:
        return ()
    by_note: dict[int, list[_AtomicOption]] = {}
    for option in options:
        by_note.setdefault(option.note_id, []).append(option)
    note_ids = tuple(by_note)[:remaining]
    if len(note_ids) < 2:
        return ()

    successors: list[_SingleState] = []
    seen: set[tuple[tuple[int, int], ...]] = set()
    pitches_per_note = max(
        1,
        config.search.coordinated_options_per_clip // 2,
    )
    pair_note_ids = note_ids[:4]
    pair_bundles = (
        (left, right)
        for left_id, right_id in combinations(pair_note_ids, 2)
        for left in by_note[left_id][:pitches_per_note]
        for right in by_note[right_id][:pitches_per_note]
    )
    for bundle in pair_bundles:
        if budget.exhausted:
            break
        signature = tuple(
            sorted(
                (option.note_id, option.repaired_pitch)
                for option in bundle
            )
        )
        if signature in seen:
            continue
        seen.add(signature)
        candidate = _bundle_state(
            state,
            bundle,
            original,
            config,
            analysis_config,
            budget,
        )
        if candidate is not None:
            successors.append(candidate)

    if config.preset is RepairPreset.CREATIVE:
        best_options = tuple(by_note[note_id][0] for note_id in note_ids)
        for size in range(3, len(best_options) + 1):
            if budget.exhausted:
                break
            bundle = best_options[:size]
            signature = tuple(
                sorted(
                    (option.note_id, option.repaired_pitch)
                    for option in bundle
                )
            )
            if signature in seen:
                continue
            seen.add(signature)
            candidate = _bundle_state(
                state,
                bundle,
                original,
                config,
                analysis_config,
                budget,
            )
            if candidate is not None:
                successors.append(candidate)
    return tuple(
        sorted(successors, key=_state_rank)[
            : config.search.successors_per_state
        ]
    )


def _deduplicate_states(
    states: Iterable[_SingleState],
) -> tuple[_SingleState, ...]:
    best_by_signature: dict[tuple[tuple[int, int], ...], _SingleState] = {}
    for state in states:
        signature = _state_signature(state)
        current = best_by_signature.get(signature)
        if current is None or _state_rank(state) < _state_rank(current):
            best_by_signature[signature] = state
    return tuple(sorted(best_by_signature.values(), key=_state_rank))


def _result(
    original: MidiClip,
    before: SingleClipAnalysis,
    state: _SingleState,
    config: SingleRepairConfig,
    enabled_ids: frozenset[str],
    analysis_config: SingleAnalysisConfig,
    budget: _EvaluationBudget,
    stop_reason: str,
    initial_cost: float,
) -> SingleRepairResult:
    return SingleRepairResult(
        original_clip=original,
        repaired_clip=state.clip,
        before_analysis=before,
        after_analysis=state.analysis,
        edits=state.edits,
        repair_config=config,
        enabled_suggestion_ids=enabled_ids,
        edit_suggestion_ids=tuple(
            sorted(state.edit_sources, key=lambda item: item[0])
        ),
        analysis_config=analysis_config,
        objective_cost=state.objective_cost,
        objective_gain=initial_cost - state.objective_cost,
        states_evaluated=budget.used,
        stop_reason=stop_reason,
    )


def generate_single_repair(
    clip: MidiClip,
    *,
    analysis: SingleClipAnalysis | None = None,
    enabled_suggestion_ids: SuggestionSelection = None,
    preset: RepairPreset | str = RepairPreset.MINIMAL,
    preservation: int = 50,
    repair_config: SingleRepairConfig | None = None,
    analysis_config: SingleAnalysisConfig | None = None,
) -> SingleRepairResult:
    """Generate one bounded, deterministic, pitch-only single-clip repair.

    ``None`` selects the analysis API's high-confidence defaults; an empty
    collection explicitly disables every suggestion. Candidate pitches come
    only from enabled suggestions, and each child/bundle is rescored by
    :func:`analyze_single_clip` as a complete modified clip.
    """

    if not isinstance(clip, MidiClip):
        raise TypeError("clip must be a MidiClip")
    if repair_config is not None and not isinstance(
        repair_config,
        SingleRepairConfig,
    ):
        raise TypeError("repair_config must be a SingleRepairConfig")
    config = repair_config or single_repair_config_for(preset, preservation)
    if analysis is not None and not isinstance(analysis, SingleClipAnalysis):
        raise TypeError("analysis must be a SingleClipAnalysis")
    if (
        analysis is not None
        and analysis.analyzed_clip is not None
        and analysis.analyzed_clip != clip
    ):
        raise ValueError("analysis does not match the supplied MIDI clip")
    if analysis_config is None:
        resolved_analysis_config = (
            analysis.analysis_config
            if analysis is not None and analysis.analysis_config is not None
            else DEFAULT_SINGLE_ANALYSIS_CONFIG
        )
    else:
        if not isinstance(analysis_config, SingleAnalysisConfig):
            raise TypeError("analysis_config must be a SingleAnalysisConfig")
        if (
            analysis is not None
            and analysis.analysis_config is not None
            and analysis.analysis_config != analysis_config
        ):
            raise ValueError(
                "analysis was produced with a different analysis configuration"
            )
        resolved_analysis_config = analysis_config
    before = analysis or analyze_single_clip(
        clip,
        config=resolved_analysis_config,
    )
    if not isinstance(before, SingleClipAnalysis):
        raise TypeError("analysis must be a SingleClipAnalysis")
    enabled_ids = _resolve_enabled_ids(before, enabled_suggestion_ids)
    initial_cost = _objective_cost(clip, clip, before, (), config)
    initial = _SingleState(
        clip=clip,
        analysis=before,
        edits=(),
        edit_sources=(),
        objective_cost=initial_cost,
    )
    budget = _EvaluationBudget(maximum=config.search.maximum_evaluations)

    if config.is_locked:
        stop_reason = (
            "Preservation is 100%; no edits are allowed."
            if config.preservation == 100
            else "The configured repair budget is zero; no edits are allowed."
        )
        return _result(
            clip,
            before,
            initial,
            config,
            enabled_ids,
            resolved_analysis_config,
            budget,
            stop_reason,
            initial_cost,
        )
    if not enabled_ids:
        stop_reason = (
            (
                "No repair suggestions were detected. No suggestions are enabled, "
                "so no improving candidate can be generated."
            )
            if not before.suggestions
            else (
                "No suggestions are enabled; select at least one suggestion "
                "to repair."
            )
        )
        return _result(
            clip,
            before,
            initial,
            config,
            enabled_ids,
            resolved_analysis_config,
            budget,
            stop_reason,
            initial_cost,
        )

    plans = _build_note_plans(clip, before, enabled_ids, config)
    edit_limit = _edit_limit(clip, config)
    if not plans or edit_limit == 0:
        return _result(
            clip,
            before,
            initial,
            config,
            enabled_ids,
            resolved_analysis_config,
            budget,
            (
                "No enabled suggestion offered a valid pitch alternative under "
                "the selected preset and preservation settings."
            ),
            initial_cost,
        )

    best = initial
    frontier = (initial,)
    for _ in range(config.search.maximum_iterations):
        successors: list[_SingleState] = []
        for state in frontier:
            if state.total_edits >= edit_limit or budget.exhausted:
                continue
            options = _atomic_options(
                state,
                clip,
                plans,
                config,
                resolved_analysis_config,
                budget,
            )
            for option in options:
                candidate = _atomic_successor(state, option, clip, config)
                if candidate is not None:
                    successors.append(candidate)
            successors.extend(
                _coordinated_successors(
                    state,
                    options,
                    clip,
                    edit_limit,
                    config,
                    resolved_analysis_config,
                    budget,
                )
            )
        if not successors:
            break
        frontier = _deduplicate_states(successors)[: config.search.beam_width]
        if _state_rank(frontier[0]) < _state_rank(best):
            best = frontier[0]

    if best is initial:
        constraint_hint = (
            " Preservation may be too high."
            if config.preservation >= 75
            else ""
        )
        stop_reason = (
            "No improving candidate found. No valid pitch edit from the enabled "
            "suggestions improved estimated internal consistency."
            f"{constraint_hint} The selected preset may be too restrictive."
        )
    else:
        stop_reason = (
            f"Improving {config.preset.label} repair found with "
            f"{best.total_edits} pitch "
            f"change{'s' if best.total_edits != 1 else ''}."
        )
    return _result(
        clip,
        before,
        best,
        config,
        enabled_ids,
        resolved_analysis_config,
        budget,
        stop_reason,
        initial_cost,
    )


__all__ = [
    "DEFAULT_SINGLE_REPAIR_CONFIG",
    "SingleRepairConfig",
    "SingleRepairResult",
    "SuggestionSelection",
    "generate_single_repair",
    "single_repair_config_for",
]
