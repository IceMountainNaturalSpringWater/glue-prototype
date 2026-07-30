"""Generalized deterministic repair for canonical Clip A + Clip B pairs."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from fractions import Fraction
from itertools import combinations
from math import floor
from typing import Literal

from glue.analysis import (
    DEFAULT_ANALYSIS_CONFIG,
    AnalysisConfig,
    PairAnalysis,
    WindowAnalysis,
    analyze_pair,
)
from glue.models import MidiClip, MidiNote

from .config import (
    DEFAULT_PAIR_REPAIR_CONFIG,
    ClipRepairConstraints,
    EditingStrategy,
    JointObjectiveWeights,
    PairRepairConfig,
    pair_repair_config_for,
)
from .minimal import (
    NoteEdit,
    OctavePolicy,
    RepairConfig,
    RepairPreset,
    _candidate_deltas,
    _contour_disruption,
    _eligible_notes,
    _introduces_pitch_collision,
    _shortlisted_notes,
    generate_repair,
    generate_repair_for_slot,
    repair_config_for,
)

ClipLabel = Literal["A", "B"]
_EPSILON = 1e-9


class RepairConstraintError(ValueError):
    """Raised when the selected constraints leave no legal repair action."""


@dataclass(frozen=True, slots=True)
class PairRepairResult:
    """One immutable, canonically oriented A+B repair candidate.

    A coupled A+B search step has no unique per-note compatibility attribution.
    Its positive full-pair score gain is divided equally between the two
    :class:`NoteEdit` records, preserving the legacy positive-gain contract.
    ``objective_gain`` remains the authoritative complete-candidate value.
    """

    original_clip_a: MidiClip
    original_clip_b: MidiClip
    repaired_clip_a: MidiClip
    repaired_clip_b: MidiClip
    before_analysis: PairAnalysis
    after_analysis: PairAnalysis
    edits_a: tuple[NoteEdit, ...]
    edits_b: tuple[NoteEdit, ...]
    repair_config: PairRepairConfig
    analysis_config: AnalysisConfig = DEFAULT_ANALYSIS_CONFIG
    objective_cost: float = 0.0
    objective_gain: float = 0.0
    states_evaluated: int = 0

    def __post_init__(self) -> None:
        if self.states_evaluated < 0:
            raise ValueError("states_evaluated must be non-negative")
        self._validate_edits(
            self.original_clip_a,
            self.repaired_clip_a,
            self.edits_a,
            "A",
        )
        self._validate_edits(
            self.original_clip_b,
            self.repaired_clip_b,
            self.edits_b,
            "B",
        )

    @staticmethod
    def _validate_edits(
        original: MidiClip,
        repaired: MidiClip,
        edits: tuple[NoteEdit, ...],
        label: ClipLabel,
    ) -> None:
        original_by_id = {note.id: note for note in original.notes}
        repaired_by_id = {note.id: note for note in repaired.notes}
        if original_by_id.keys() != repaired_by_id.keys():
            raise ValueError(f"repaired Clip {label} changed note identities")
        edit_by_id = {edit.note_id: edit for edit in edits}
        if len(edit_by_id) != len(edits):
            raise ValueError(f"Clip {label} contains duplicate edits")
        for note_id, original_note in original_by_id.items():
            repaired_note = repaired_by_id[note_id]
            edit = edit_by_id.get(note_id)
            if edit is None:
                if repaired_note != original_note:
                    raise ValueError(
                        f"repaired Clip {label} changed note {note_id} without an edit"
                    )
                continue
            if edit.original_pitch != original_note.pitch:
                raise ValueError(f"Clip {label} edit {note_id} has the wrong source pitch")
            if edit.repaired_pitch != repaired_note.pitch:
                raise ValueError(f"Clip {label} edit {note_id} has the wrong final pitch")
            if repaired_note != replace(
                original_note,
                pitch=edit.repaired_pitch,
            ):
                raise ValueError(
                    f"repaired Clip {label} changed non-pitch fields for note {note_id}"
                )

    @property
    def strategy(self) -> EditingStrategy:
        return self.repair_config.strategy

    @property
    def preset(self) -> RepairPreset:
        return self.repair_config.preset

    @property
    def constraints_a(self) -> ClipRepairConstraints:
        return self.repair_config.clip_a

    @property
    def constraints_b(self) -> ClipRepairConstraints:
        return self.repair_config.clip_b

    @property
    def original_score(self) -> float:
        return self.before_analysis.overall_score

    @property
    def repaired_score(self) -> float:
        return self.after_analysis.overall_score

    @property
    def score_improvement(self) -> float:
        return self.repaired_score - self.original_score

    @property
    def has_improvement(self) -> bool:
        """Return whether the search produced a changed, better-scoring pair."""

        return self.changed_note_count > 0 and self.score_improvement > _EPSILON

    @property
    def is_improving(self) -> bool:
        """Compatibility alias for :attr:`has_improvement`."""

        return self.has_improvement

    @property
    def no_improvement_reason(self) -> str | None:
        """Return actionable guidance for a valid no-improvement outcome."""

        if self.has_improvement:
            return None
        if self.changed_note_count:
            return "No valid pitch edit improved the estimated result."
        editable_constraints = tuple(
            constraints
            for constraints in (self.constraints_a, self.constraints_b)
            if not constraints.is_locked
        )
        if any(
            constraints.preservation >= 0.75
            for constraints in editable_constraints
        ):
            return (
                "No improving candidate found. Preservation may be too high; "
                "lower it or choose a broader repair preset."
            )
        return (
            "No improving candidate found. The selected preset may be too "
            "restrictive, or no valid pitch edit improved the estimated result."
        )

    @property
    def changed_note_count_a(self) -> int:
        return len(self.edits_a)

    @property
    def changed_note_count_b(self) -> int:
        return len(self.edits_b)

    @property
    def changed_note_count(self) -> int:
        return self.changed_note_count_a + self.changed_note_count_b

    @property
    def total_pitch_displacement(self) -> int:
        return sum(edit.semitone_distance for edit in (*self.edits_a, *self.edits_b))

    @staticmethod
    def _retention(clip: MidiClip, edits: tuple[NoteEdit, ...]) -> float:
        editable_notes = sum(
            not note.is_percussion and note.duration_ticks > 0 for note in clip.notes
        )
        if not editable_notes:
            return 1.0
        return 1.0 - len(edits) / editable_notes

    @property
    def retention_a(self) -> float:
        return self._retention(self.original_clip_a, self.edits_a)

    @property
    def retention_b(self) -> float:
        return self._retention(self.original_clip_b, self.edits_b)

    @property
    def preservation_a(self) -> float:
        return self.constraints_a.preservation

    @property
    def preservation_b(self) -> float:
        return self.constraints_b.preservation

    @property
    def edits(self) -> tuple[NoteEdit, ...]:
        """Return both edit sets; callers needing identity should use A/B fields."""

        return (*self.edits_a, *self.edits_b)

    @property
    def original_clip(self) -> MidiClip:
        """V0.2 alias for the editable clip in a one-sided candidate."""

        if self.strategy is EditingStrategy.PRESERVE_B:
            return self.original_clip_a
        return self.original_clip_b

    @property
    def repaired_clip(self) -> MidiClip:
        """V0.2 alias for the editable clip in a one-sided candidate.

        Pair-aware callers should always use ``repaired_clip_a`` and
        ``repaired_clip_b``. Shared candidates retain B here only so legacy
        presentation code can migrate incrementally without changing V0.2.
        """

        if self.strategy is EditingStrategy.PRESERVE_B:
            return self.repaired_clip_a
        return self.repaired_clip_b

    @property
    def candidate_clip(self) -> MidiClip:
        """V0.2 candidate-list alias; pair-aware callers should use A/B fields."""

        return self.repaired_clip

    @property
    def preservation(self) -> int:
        """V0.2 whole-percent value for the one-sided editable clip."""

        if self.strategy is EditingStrategy.PRESERVE_B:
            return self.constraints_a.preservation_percent
        return self.constraints_b.preservation_percent

    @property
    def before(self) -> PairAnalysis:
        return self.before_analysis

    @property
    def after(self) -> PairAnalysis:
        return self.after_analysis


# Descriptive aliases for callers that use "joint" or "strategy" terminology.
JointRepairResult = PairRepairResult
StrategyRepairResult = PairRepairResult


@dataclass(frozen=True, slots=True)
class _PairState:
    clip_a: MidiClip
    clip_b: MidiClip
    analysis: PairAnalysis
    edits_a: tuple[NoteEdit, ...]
    edits_b: tuple[NoteEdit, ...]
    objective_cost: float

    @property
    def total_edits(self) -> int:
        return len(self.edits_a) + len(self.edits_b)


@dataclass(slots=True)
class _EvaluationBudget:
    maximum: int
    used: int = 1

    @property
    def exhausted(self) -> bool:
        return self.used >= self.maximum


@dataclass(frozen=True, slots=True)
class _AtomicOption:
    """One legal side-local pitch option, including its canonical pair score."""

    side: ClipLabel
    note_id: int
    original_pitch: int
    repaired_pitch: int
    repaired_clip: MidiClip
    analysis: PairAnalysis
    score_change: float
    penalty: float

    @property
    def delta(self) -> int:
        return self.repaired_pitch - self.original_pitch


@dataclass(frozen=True, slots=True)
class _SideExpansion:
    """Bounded single-edit states plus options available to paired expansion."""

    successors: tuple[_PairState, ...] = ()
    options: tuple[_AtomicOption, ...] = ()


def _legacy_config(
    pair_config: PairRepairConfig,
    constraints: ClipRepairConstraints,
) -> RepairConfig:
    config = repair_config_for(
        pair_config.preset,
        constraints.preservation_percent,
    )
    return replace(
        config,
        maximum_changes=min(config.maximum_changes, constraints.max_note_changes),
        octave_policy=(
            config.octave_policy
            if constraints.allow_octave_edits
            else OctavePolicy.NEVER
        ),
    )


def _note_overlap_in_beats(
    note_a: MidiNote,
    clip_a: MidiClip,
    note_b: MidiNote,
    clip_b: MidiClip,
) -> Fraction:
    start = max(
        Fraction(note_a.onset_ticks, clip_a.ticks_per_beat),
        Fraction(note_b.onset_ticks, clip_b.ticks_per_beat),
    )
    end = min(
        Fraction(note_a.end_ticks, clip_a.ticks_per_beat),
        Fraction(note_b.end_ticks, clip_b.ticks_per_beat),
    )
    return max(Fraction(0), end - start)


def _line_independence_metrics(
    original_a: MidiClip,
    original_b: MidiClip,
    repaired_a: MidiClip,
    repaired_b: MidiClip,
    edited_a: frozenset[int],
    edited_b: frozenset[int],
) -> tuple[float, float]:
    """Return introduced-unison duration and close-line convergence loss."""

    original_a_by_id = {note.id: note for note in original_a.notes}
    original_b_by_id = {note.id: note for note in original_b.notes}
    introduced_unison = 0.0
    convergence = 0.0
    for note_a in repaired_a.notes:
        if note_a.is_percussion or note_a.duration_ticks <= 0:
            continue
        for note_b in repaired_b.notes:
            if note_b.is_percussion or note_b.duration_ticks <= 0:
                continue
            overlap = _note_overlap_in_beats(note_a, repaired_a, note_b, repaired_b)
            if overlap <= 0:
                continue
            original_note_a = original_a_by_id[note_a.id]
            original_note_b = original_b_by_id[note_b.id]
            if note_a.id not in edited_a and note_b.id not in edited_b:
                continue
            overlap_weight = min(float(overlap), 1.0)
            original_distance = abs(original_note_a.pitch - original_note_b.pitch)
            repaired_distance = abs(note_a.pitch - note_b.pitch)
            if repaired_distance == 0 and original_distance != 0:
                introduced_unison += overlap_weight
            if repaired_distance < min(original_distance, 5):
                convergence += (
                    (min(original_distance, 12) - repaired_distance) / 12.0
                ) * overlap_weight
    return introduced_unison, convergence


def _motif_disruption(
    clip: MidiClip,
    edit_ids: frozenset[int],
) -> float:
    """Penalize changing only part of an exact repeated-note pattern."""

    if not edit_ids:
        return 0.0
    groups: dict[tuple[int, int, int, int], set[int]] = {}
    for note in clip.notes:
        if note.is_percussion or note.duration_ticks <= 0:
            continue
        key = (note.track, note.channel, note.pitch, note.duration_ticks)
        groups.setdefault(key, set()).add(note.id)
    disruption = 0.0
    for ids in groups.values():
        changed = len(ids & edit_ids)
        if len(ids) > 1 and 0 < changed < len(ids):
            disruption += changed / len(ids)
    return disruption


def _ordinary_disruption_scale(preservation: float) -> float:
    """Remove soft edit costs at zero without changing the legacy midpoint.

    Preservation above 50% is already represented by the separate quadratic
    preservation term. Capping ordinary disruption at its legacy value avoids
    double-counting high preservation while still making the lower half
    progressively more permissive.
    """

    if preservation <= 0.50:
        return preservation / 0.50
    return 1.0


def _clip_disruption(
    original: MidiClip,
    repaired: MidiClip,
    edits: tuple[NoteEdit, ...],
    constraints: ClipRepairConstraints,
    weights: JointObjectiveWeights,
) -> float:
    if not edits:
        return 0.0
    note_index_by_id = {note.id: index for index, note in enumerate(original.notes)}
    repaired_by_id = {note.id: note for note in repaired.notes}
    edit_ids = frozenset(edit.note_id for edit in edits)
    contour = sum(
        _contour_disruption(
            original.notes,
            note_index_by_id[edit.note_id],
            repaired_by_id[edit.note_id].pitch,
        )
        for edit in edits
    )
    octave_count = sum(edit.is_octave_move for edit in edits)
    ordinary_scale = _ordinary_disruption_scale(constraints.preservation)
    return (
        ordinary_scale
        * (
            len(edits) * weights.edit_count
            + sum(edit.semitone_distance for edit in edits)
            * weights.semitone_distance
            + octave_count * weights.octave
            + contour * weights.contour
            + _motif_disruption(original, edit_ids) * weights.motif
        )
        + len(edits) * weights.preservation * constraints.preservation**2
    )


def _objective_cost(
    original_a: MidiClip,
    original_b: MidiClip,
    repaired_a: MidiClip,
    repaired_b: MidiClip,
    analysis: PairAnalysis,
    edits_a: tuple[NoteEdit, ...],
    edits_b: tuple[NoteEdit, ...],
    config: PairRepairConfig,
) -> float:
    weights = config.objective
    edited_a = frozenset(edit.note_id for edit in edits_a)
    edited_b = frozenset(edit.note_id for edit in edits_b)
    introduced_unison, convergence = _line_independence_metrics(
        original_a,
        original_b,
        repaired_a,
        repaired_b,
        edited_a,
        edited_b,
    )
    return (
        (100.0 - analysis.overall_score) * weights.remaining_conflict
        + _clip_disruption(
            original_a,
            repaired_a,
            edits_a,
            config.clip_a,
            weights,
        )
        + _clip_disruption(
            original_b,
            repaired_b,
            edits_b,
            config.clip_b,
            weights,
        )
        + introduced_unison * weights.introduced_unison
        + convergence * weights.convergence
    )


def _single_edit_penalty(
    original: MidiClip,
    repaired_pitch: int,
    note_id: int,
    constraints: ClipRepairConstraints,
    weights: JointObjectiveWeights,
) -> float:
    note_index = next(
        index for index, note in enumerate(original.notes) if note.id == note_id
    )
    note = original.notes[note_index]
    delta = repaired_pitch - note.pitch
    motif = _motif_disruption(original, frozenset((note_id,)))
    ordinary_scale = _ordinary_disruption_scale(constraints.preservation)
    return (
        ordinary_scale
        * (
            weights.edit_count
            + weights.semitone_distance * abs(delta)
            + (weights.octave if abs(delta) == 12 else 0.0)
            + weights.contour
            * _contour_disruption(original.notes, note_index, repaired_pitch)
            + weights.motif * motif
        )
        + weights.preservation * constraints.preservation**2
    )


def _candidate_config(config: PairRepairConfig) -> RepairConfig:
    base = repair_config_for(config.preset, 50)
    return replace(
        base,
        maximum_candidate_notes_per_step=(
            config.search.candidate_notes_per_clip
        ),
        # Generate the preset's complete ordered vocabulary before applying
        # joint-search policy below.  Truncating here used to discard whole
        # categories (positive moves, octaves, and local harmony) merely
        # because they appeared later in a static tuple.
        maximum_candidate_pitches_per_note=max(
            base.maximum_candidate_pitches_per_note,
            config.search.candidate_pitches_per_note,
        ),
    )


def _joint_candidate_deltas(
    note: MidiNote,
    windows: tuple[WindowAnalysis, ...],
    candidate_config: RepairConfig,
    pair_config: PairRepairConfig,
) -> tuple[int, ...]:
    """Return the preset's category-complete bounded pitch vocabulary.

    The search bound, preservation-aware objective, and MIDI safety guards
    decide which options survive. Creative intentionally retains its wider
    local-harmony alternatives instead of silently discarding nine-to-eleven
    semitone candidates.
    """

    deltas = _candidate_deltas(note, windows, candidate_config)
    return deltas[: pair_config.search.candidate_pitches_per_note]


def _side_change_limit(
    clip: MidiClip,
    constraints: ClipRepairConstraints,
    pair_config: PairRepairConfig,
) -> int:
    pitched_notes = sum(
        not note.is_percussion and note.duration_ticks > 0 for note in clip.notes
    )
    if not pitched_notes or pair_config.search.maximum_change_fraction <= 0:
        return 0
    fractional_limit = max(
        1,
        floor(pitched_notes * pair_config.search.maximum_change_fraction),
    )
    return min(constraints.max_note_changes, fractional_limit)


def _creative_windows_for_side(
    windows: tuple[WindowAnalysis, ...],
    side: ClipLabel,
) -> tuple[WindowAnalysis, ...]:
    if side == "B":
        return windows
    return tuple(
        replace(window, local_harmony_a=window.local_harmony_b)
        for window in windows
    )


def _replace_pitch(clip: MidiClip, note_id: int, pitch: int) -> MidiClip:
    return clip.with_notes(
        replace(note, pitch=pitch) if note.id == note_id else note
        for note in clip.notes
    )


def _state_signature(
    state: _PairState,
) -> tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]:
    return (
        tuple(sorted((edit.note_id, edit.repaired_pitch) for edit in state.edits_a)),
        tuple(sorted((edit.note_id, edit.repaired_pitch) for edit in state.edits_b)),
    )


def _state_rank(state: _PairState) -> tuple[object, ...]:
    return (
        round(state.objective_cost, 12),
        -round(state.analysis.overall_score, 12),
        state.total_edits,
        sum(edit.semitone_distance for edit in (*state.edits_a, *state.edits_b)),
        _state_signature(state),
    )


def _atomic_option_rank(option: _AtomicOption) -> tuple[float | int, ...]:
    """Prefer the least harmful atomic options before the bounded cross-product."""

    return (
        -round(option.score_change, 12),
        round(option.penalty, 12),
        abs(option.delta),
        option.note_id,
        option.repaired_pitch,
    )


def _bounded_side_expansion(
    successors: list[_PairState],
    options: list[_AtomicOption],
    pair_config: PairRepairConfig,
) -> _SideExpansion:
    return _SideExpansion(
        successors=tuple(
            sorted(successors, key=_state_rank)[
                : pair_config.search.successors_per_state
            ]
        ),
        options=tuple(sorted(options, key=_atomic_option_rank)),
    )


def _side_successors(
    state: _PairState,
    side: ClipLabel,
    original_a: MidiClip,
    original_b: MidiClip,
    pair_config: PairRepairConfig,
    analysis_config: AnalysisConfig,
    candidate_config: RepairConfig,
    evaluation_budget: _EvaluationBudget,
) -> _SideExpansion:
    is_a = side == "A"
    current = state.clip_a if is_a else state.clip_b
    original = original_a if is_a else original_b
    constraints = pair_config.clip_a if is_a else pair_config.clip_b
    edits = state.edits_a if is_a else state.edits_b
    if constraints.is_locked or len(edits) >= _side_change_limit(
        original,
        constraints,
        pair_config,
    ):
        return _SideExpansion()

    edited_ids = frozenset(edit.note_id for edit in edits)
    original_pitch_by_id: Mapping[int, int] = {
        note.id: note.pitch for note in original.notes
    }
    eligible = _eligible_notes(
        current,
        state.analysis,
        edited_ids,
        candidate_config,
    )
    shortlisted = _shortlisted_notes(eligible, candidate_config)
    successors: list[_PairState] = []
    options: list[_AtomicOption] = []
    for note, weak_windows in shortlisted:
        pitch_windows = _creative_windows_for_side(weak_windows, side)
        deltas = _joint_candidate_deltas(
            note,
            pitch_windows,
            candidate_config,
            pair_config,
        )
        for delta in deltas:
            if evaluation_budget.exhausted:
                return _bounded_side_expansion(
                    successors,
                    options,
                    pair_config,
                )
            if abs(delta) == 12 and not constraints.allow_octave_edits:
                continue
            repaired_pitch = note.pitch + delta
            if _introduces_pitch_collision(
                note,
                repaired_pitch,
                current.notes,
                original_pitch_by_id,
            ):
                continue
            repaired_side = _replace_pitch(current, note.id, repaired_pitch)
            repaired_a = repaired_side if is_a else state.clip_a
            repaired_b = state.clip_b if is_a else repaired_side
            evaluation_budget.used += 1
            analysis = analyze_pair(
                repaired_a,
                repaired_b,
                config=analysis_config,
            )
            score_change = analysis.overall_score - state.analysis.overall_score
            penalty = _single_edit_penalty(
                original,
                repaired_pitch,
                note.id,
                constraints,
                pair_config.objective,
            )
            options.append(
                _AtomicOption(
                    side=side,
                    note_id=note.id,
                    original_pitch=original_pitch_by_id[note.id],
                    repaired_pitch=repaired_pitch,
                    repaired_clip=repaired_side,
                    analysis=analysis,
                    score_change=score_change,
                    penalty=penalty,
                )
            )
            if (
                score_change + _EPSILON
                < pair_config.search.minimum_score_improvement
            ):
                continue
            edit = NoteEdit(
                note_id=note.id,
                original_pitch=original_pitch_by_id[note.id],
                repaired_pitch=repaired_pitch,
                score_improvement=score_change,
                penalty=penalty,
                objective_gain=score_change - penalty,
                preset=pair_config.preset,
            )
            edits_a = (*state.edits_a, edit) if is_a else state.edits_a
            edits_b = state.edits_b if is_a else (*state.edits_b, edit)
            successors.append(
                _PairState(
                    clip_a=repaired_a,
                    clip_b=repaired_b,
                    analysis=analysis,
                    edits_a=edits_a,
                    edits_b=edits_b,
                    objective_cost=_objective_cost(
                        original_a,
                        original_b,
                        repaired_a,
                        repaired_b,
                        analysis,
                        edits_a,
                        edits_b,
                        pair_config,
                    ),
                )
            )
    return _bounded_side_expansion(successors, options, pair_config)


def _paired_successors(
    state: _PairState,
    expansion_a: _SideExpansion,
    expansion_b: _SideExpansion,
    original_a: MidiClip,
    original_b: MidiClip,
    pair_config: PairRepairConfig,
    analysis_config: AnalysisConfig,
    evaluation_budget: _EvaluationBudget,
) -> tuple[_PairState, ...]:
    """Evaluate a small deterministic cross-product as complete A+B edits."""

    if (
        state.total_edits + 2 > pair_config.search.maximum_total_edits
        or not expansion_a.options
        or not expansion_b.options
    ):
        return ()

    option_limit = pair_config.search.paired_options_per_clip
    options_a = expansion_a.options[:option_limit]
    options_b = expansion_b.options[:option_limit]
    successors: list[_PairState] = []
    for option_a in options_a:
        for option_b in options_b:
            if evaluation_budget.exhausted:
                return tuple(
                    sorted(successors, key=_state_rank)[
                        : pair_config.search.successors_per_state
                    ]
                )
            evaluation_budget.used += 1
            analysis = analyze_pair(
                option_a.repaired_clip,
                option_b.repaired_clip,
                config=analysis_config,
            )
            score_change = analysis.overall_score - state.analysis.overall_score
            if (
                score_change + _EPSILON
                < pair_config.search.minimum_score_improvement
            ):
                continue

            # Neither atomic move need improve the pair alone. The indivisible
            # joint step's positive gain is shared only for NoteEdit reporting;
            # complete-pair objective cost controls candidate ranking.
            joint_gain_share = score_change / 2.0
            edit_a = NoteEdit(
                note_id=option_a.note_id,
                original_pitch=option_a.original_pitch,
                repaired_pitch=option_a.repaired_pitch,
                score_improvement=joint_gain_share,
                penalty=option_a.penalty,
                objective_gain=joint_gain_share - option_a.penalty,
                preset=pair_config.preset,
            )
            edit_b = NoteEdit(
                note_id=option_b.note_id,
                original_pitch=option_b.original_pitch,
                repaired_pitch=option_b.repaired_pitch,
                score_improvement=joint_gain_share,
                penalty=option_b.penalty,
                objective_gain=joint_gain_share - option_b.penalty,
                preset=pair_config.preset,
            )
            edits_a = (*state.edits_a, edit_a)
            edits_b = (*state.edits_b, edit_b)
            successors.append(
                _PairState(
                    clip_a=option_a.repaired_clip,
                    clip_b=option_b.repaired_clip,
                    analysis=analysis,
                    edits_a=edits_a,
                    edits_b=edits_b,
                    objective_cost=_objective_cost(
                        original_a,
                        original_b,
                        option_a.repaired_clip,
                        option_b.repaired_clip,
                        analysis,
                        edits_a,
                        edits_b,
                        pair_config,
                    ),
                )
            )
    return tuple(
        sorted(successors, key=_state_rank)[
            : pair_config.search.successors_per_state
        ]
    )


def _coordinated_state(
    state: _PairState,
    side: ClipLabel,
    options: tuple[_AtomicOption, ...],
    original_a: MidiClip,
    original_b: MidiClip,
    pair_config: PairRepairConfig,
    analysis_config: AnalysisConfig,
    evaluation_budget: _EvaluationBudget,
) -> _PairState | None:
    """Fully rescore one same-side multi-note option bundle."""

    if evaluation_budget.exhausted or len(options) < 2:
        return None
    if len({option.note_id for option in options}) != len(options):
        return None

    is_a = side == "A"
    current = state.clip_a if is_a else state.clip_b
    original = original_a if is_a else original_b
    original_pitch_by_id = {note.id: note.pitch for note in original.notes}
    repaired_side = current
    for option in options:
        note = next(
            note
            for note in repaired_side.notes
            if note.id == option.note_id
        )
        if _introduces_pitch_collision(
            note,
            option.repaired_pitch,
            repaired_side.notes,
            original_pitch_by_id,
        ):
            return None
        repaired_side = _replace_pitch(
            repaired_side,
            option.note_id,
            option.repaired_pitch,
        )

    repaired_a = repaired_side if is_a else state.clip_a
    repaired_b = state.clip_b if is_a else repaired_side
    evaluation_budget.used += 1
    analysis = analyze_pair(
        repaired_a,
        repaired_b,
        config=analysis_config,
    )
    score_change = analysis.overall_score - state.analysis.overall_score
    if (
        score_change + _EPSILON
        < pair_config.search.minimum_score_improvement
    ):
        return None

    joint_gain_share = score_change / len(options)
    new_edits = tuple(
        NoteEdit(
            note_id=option.note_id,
            original_pitch=option.original_pitch,
            repaired_pitch=option.repaired_pitch,
            score_improvement=joint_gain_share,
            penalty=option.penalty,
            objective_gain=joint_gain_share - option.penalty,
            preset=pair_config.preset,
        )
        for option in options
    )
    edits_a = (*state.edits_a, *new_edits) if is_a else state.edits_a
    edits_b = state.edits_b if is_a else (*state.edits_b, *new_edits)
    return _PairState(
        clip_a=repaired_a,
        clip_b=repaired_b,
        analysis=analysis,
        edits_a=edits_a,
        edits_b=edits_b,
        objective_cost=_objective_cost(
            original_a,
            original_b,
            repaired_a,
            repaired_b,
            analysis,
            edits_a,
            edits_b,
            pair_config,
        ),
    )


def _coordinated_side_successors(
    state: _PairState,
    side: ClipLabel,
    expansion: _SideExpansion,
    original_a: MidiClip,
    original_b: MidiClip,
    pair_config: PairRepairConfig,
    analysis_config: AnalysisConfig,
    evaluation_budget: _EvaluationBudget,
) -> tuple[_PairState, ...]:
    """Evaluate bounded same-side combinations, including non-greedy pairs.

    Atomic options are retained even when they do not improve compatibility.
    Creative can therefore test a fully rescored two-note combination whose
    individual moves would both be rejected by the ordinary greedy frontier.
    A best-option prefix additionally lets low-preservation searches jump
    directly to coordinated edits across several independent conflict notes.
    """

    if not expansion.options:
        return ()
    is_a = side == "A"
    original = original_a if is_a else original_b
    constraints = pair_config.clip_a if is_a else pair_config.clip_b
    existing_edits = state.edits_a if is_a else state.edits_b
    remaining_side = (
        _side_change_limit(original, constraints, pair_config)
        - len(existing_edits)
    )
    remaining_total = (
        pair_config.search.maximum_total_edits - state.total_edits
    )
    maximum_new = min(
        remaining_side,
        remaining_total,
        pair_config.search.coordinated_options_per_clip,
    )
    if maximum_new < 2:
        return ()

    options_by_note: dict[int, list[_AtomicOption]] = {}
    for option in expansion.options:
        options_by_note.setdefault(option.note_id, []).append(option)
    note_ids = tuple(options_by_note)[:maximum_new]
    if len(note_ids) < 2:
        return ()

    successors: list[_PairState] = []
    evaluated_signatures: set[tuple[tuple[int, int], ...]] = set()

    # Pair alternatives need more than only the best atomic pitch. The option
    # pool is deliberately small and deterministic: Creative's eight-option
    # bound exposes the top four pitches for each of up to four conflict notes.
    pitches_per_note = max(
        1,
        pair_config.search.coordinated_options_per_clip // 2,
    )
    pair_note_ids = note_ids[:4]
    pair_bundles = (
        (left, right)
        for left_id, right_id in combinations(pair_note_ids, 2)
        for left in options_by_note[left_id][:pitches_per_note]
        for right in options_by_note[right_id][:pitches_per_note]
    )
    for bundle in pair_bundles:
        if evaluation_budget.exhausted:
            break
        signature = tuple(
            sorted(
                (option.note_id, option.repaired_pitch)
                for option in bundle
            )
        )
        if signature in evaluated_signatures:
            continue
        evaluated_signatures.add(signature)
        candidate = _coordinated_state(
            state,
            side,
            bundle,
            original_a,
            original_b,
            pair_config,
            analysis_config,
            evaluation_budget,
        )
        if candidate is not None:
            successors.append(candidate)

    # Prefix bundles cheaply expose three-or-more-note coordinated candidates
    # without constructing a combinatorial pitch cross-product.
    best_options = tuple(options_by_note[note_id][0] for note_id in note_ids)
    for bundle_size in range(2, len(best_options) + 1):
        if evaluation_budget.exhausted:
            break
        bundle = best_options[:bundle_size]
        signature = tuple(
            sorted(
                (option.note_id, option.repaired_pitch)
                for option in bundle
            )
        )
        if signature in evaluated_signatures:
            continue
        evaluated_signatures.add(signature)
        candidate = _coordinated_state(
            state,
            side,
            bundle,
            original_a,
            original_b,
            pair_config,
            analysis_config,
            evaluation_budget,
        )
        if candidate is not None:
            successors.append(candidate)

    return tuple(
        sorted(successors, key=_state_rank)[
            : pair_config.search.successors_per_state
        ]
    )


def _deduplicate_states(states: Iterable[_PairState]) -> tuple[_PairState, ...]:
    best_by_signature: dict[
        tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]],
        _PairState,
    ] = {}
    for state in states:
        signature = _state_signature(state)
        current = best_by_signature.get(signature)
        if current is None or _state_rank(state) < _state_rank(current):
            best_by_signature[signature] = state
    return tuple(sorted(best_by_signature.values(), key=_state_rank))


def _joint_repair(
    clip_a: MidiClip,
    clip_b: MidiClip,
    pair_config: PairRepairConfig,
    analysis_config: AnalysisConfig,
) -> PairRepairResult:
    before = analyze_pair(clip_a, clip_b, config=analysis_config)
    initial_cost = _objective_cost(
        clip_a,
        clip_b,
        clip_a,
        clip_b,
        before,
        (),
        (),
        pair_config,
    )
    initial = _PairState(
        clip_a=clip_a,
        clip_b=clip_b,
        analysis=before,
        edits_a=(),
        edits_b=(),
        objective_cost=initial_cost,
    )
    best = initial
    frontier = (initial,)
    candidate_config = _candidate_config(pair_config)
    evaluation_budget = _EvaluationBudget(
        maximum=pair_config.search.maximum_evaluations,
    )

    for _ in range(pair_config.search.maximum_iterations):
        successors: list[_PairState] = []
        for state in frontier:
            if state.total_edits >= pair_config.search.maximum_total_edits:
                continue
            expansion_a = _side_successors(
                state,
                "A",
                clip_a,
                clip_b,
                pair_config,
                analysis_config,
                candidate_config,
                evaluation_budget,
            )
            expansion_b = _side_successors(
                state,
                "B",
                clip_a,
                clip_b,
                pair_config,
                analysis_config,
                candidate_config,
                evaluation_budget,
            )
            successors.extend(expansion_a.successors)
            successors.extend(expansion_b.successors)
            successors.extend(
                _coordinated_side_successors(
                    state,
                    "A",
                    expansion_a,
                    clip_a,
                    clip_b,
                    pair_config,
                    analysis_config,
                    evaluation_budget,
                )
            )
            successors.extend(
                _coordinated_side_successors(
                    state,
                    "B",
                    expansion_b,
                    clip_a,
                    clip_b,
                    pair_config,
                    analysis_config,
                    evaluation_budget,
                )
            )
            successors.extend(
                _paired_successors(
                    state,
                    expansion_a,
                    expansion_b,
                    clip_a,
                    clip_b,
                    pair_config,
                    analysis_config,
                    evaluation_budget,
                )
            )
        if not successors:
            break
        frontier = _deduplicate_states(successors)[: pair_config.search.beam_width]
        if not frontier:
            break
        if _state_rank(frontier[0]) < _state_rank(best):
            best = frontier[0]

    return PairRepairResult(
        original_clip_a=clip_a,
        original_clip_b=clip_b,
        repaired_clip_a=best.clip_a,
        repaired_clip_b=best.clip_b,
        before_analysis=before,
        after_analysis=best.analysis,
        edits_a=best.edits_a,
        edits_b=best.edits_b,
        repair_config=pair_config,
        analysis_config=analysis_config,
        objective_cost=best.objective_cost,
        objective_gain=initial_cost - best.objective_cost,
        states_evaluated=evaluation_budget.used,
    )


def _one_sided_repair(
    clip_a: MidiClip,
    clip_b: MidiClip,
    pair_config: PairRepairConfig,
    analysis_config: AnalysisConfig,
) -> PairRepairResult:
    if pair_config.strategy is EditingStrategy.PRESERVE_A:
        legacy = generate_repair(
            clip_a,
            clip_b,
            repair_config=_legacy_config(pair_config, pair_config.clip_b),
            analysis_config=analysis_config,
        )
        repaired_a = clip_a
        repaired_b = legacy.repaired_clip
        edits_a: tuple[NoteEdit, ...] = ()
        edits_b = legacy.edits
        before = legacy.before_analysis
        after = legacy.after_analysis
    else:
        legacy = generate_repair_for_slot(
            clip_a,
            clip_b,
            "A",
            repair_config=_legacy_config(pair_config, pair_config.clip_a),
            analysis_config=analysis_config,
        )
        repaired_a = legacy.repaired_clip
        repaired_b = clip_b
        edits_a = legacy.edits
        edits_b = ()
        before = legacy.before_analysis
        after = legacy.after_analysis

    initial_cost = _objective_cost(
        clip_a,
        clip_b,
        clip_a,
        clip_b,
        before,
        (),
        (),
        pair_config,
    )
    final_cost = _objective_cost(
        clip_a,
        clip_b,
        repaired_a,
        repaired_b,
        after,
        edits_a,
        edits_b,
        pair_config,
    )
    return PairRepairResult(
        original_clip_a=clip_a,
        original_clip_b=clip_b,
        repaired_clip_a=repaired_a,
        repaired_clip_b=repaired_b,
        before_analysis=before,
        after_analysis=after,
        edits_a=edits_a,
        edits_b=edits_b,
        repair_config=pair_config,
        analysis_config=analysis_config,
        objective_cost=final_cost,
        objective_gain=initial_cost - final_cost,
        states_evaluated=0,
    )


def generate_pair_repair(
    clip_a: MidiClip,
    clip_b: MidiClip,
    *,
    repair_config: PairRepairConfig | None = None,
    strategy: EditingStrategy | str = EditingStrategy.PRESERVE_A,
    preset: RepairPreset | str = RepairPreset.MINIMAL,
    preservation_a: float | None = None,
    preservation_b: float | None = None,
    constraints_a: ClipRepairConstraints | None = None,
    constraints_b: ClipRepairConstraints | None = None,
    analysis_config: AnalysisConfig = DEFAULT_ANALYSIS_CONFIG,
) -> PairRepairResult:
    """Generate the best bounded candidate for the requested editing strategy.

    Shared and Custom modes expand both sides from a common frontier and rescore
    every resulting A+B pair. They never repair A and then use that result as a
    locked target for a separate B repair.
    """

    if repair_config is None:
        effective_preservation_a = (
            constraints_a.preservation
            if constraints_a is not None
            else preservation_a
        )
        effective_preservation_b = (
            constraints_b.preservation
            if constraints_b is not None
            else preservation_b
        )
        resolved = pair_repair_config_for(
            strategy,
            preset,
            preservation_a=effective_preservation_a,
            preservation_b=effective_preservation_b,
        )
        if constraints_a is not None or constraints_b is not None:
            resolved = replace(
                resolved,
                clip_a=constraints_a or resolved.clip_a,
                clip_b=constraints_b or resolved.clip_b,
            )
        repair_config = resolved
    elif any(
        value is not None
        for value in (
            preservation_a,
            preservation_b,
            constraints_a,
            constraints_b,
        )
    ):
        raise ValueError(
            "repair_config cannot be combined with preservation or constraint overrides"
        )

    if repair_config.clip_a.is_locked and repair_config.clip_b.is_locked:
        raise RepairConstraintError(
            "Both clips are fully preserved; lower preservation for at least one clip"
        )
    if repair_config.strategy in (
        EditingStrategy.PRESERVE_A,
        EditingStrategy.PRESERVE_B,
    ):
        return _one_sided_repair(
            clip_a,
            clip_b,
            repair_config,
            analysis_config,
        )
    return _joint_repair(clip_a, clip_b, repair_config, analysis_config)


def generate_shared_repair(
    clip_a: MidiClip,
    clip_b: MidiClip,
    *,
    preset: RepairPreset | str = RepairPreset.MINIMAL,
    preservation_a: float = 0.85,
    preservation_b: float = 0.85,
    analysis_config: AnalysisConfig = DEFAULT_ANALYSIS_CONFIG,
) -> PairRepairResult:
    """Convenience wrapper for the cautious Shared Compromise strategy."""

    return generate_pair_repair(
        clip_a,
        clip_b,
        strategy=EditingStrategy.SHARED,
        preset=preset,
        preservation_a=preservation_a,
        preservation_b=preservation_b,
        analysis_config=analysis_config,
    )


generate_joint_repair = generate_shared_repair
generate_strategy_repair = generate_pair_repair


__all__ = [
    "DEFAULT_PAIR_REPAIR_CONFIG",
    "JointRepairResult",
    "PairRepairResult",
    "RepairConstraintError",
    "StrategyRepairResult",
    "generate_joint_repair",
    "generate_pair_repair",
    "generate_shared_repair",
    "generate_strategy_repair",
]
