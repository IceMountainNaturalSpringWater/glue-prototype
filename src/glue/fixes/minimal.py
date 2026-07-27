"""Deterministic preservation-first pitch repair."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from math import floor

from glue.analysis import (
    DEFAULT_ANALYSIS_CONFIG,
    AnalysisConfig,
    PairAnalysis,
    WindowAnalysis,
    analyze_pair,
)
from glue.models import MidiClip, MidiNote

ALLOWED_MINIMAL_DELTAS = (-2, -1, 1, 2, -12, 12)
_NEARBY_DELTAS = (-2, -1, 1, 2)
_OCTAVE_DELTAS = (-12, 12)
_EPSILON = 1e-9


@dataclass(frozen=True, slots=True)
class MinimalRepairConfig:
    """Transparent search limits and edit penalties for Minimal mode."""

    weak_window_threshold: float = 65.0
    maximum_changes: int = 4
    maximum_change_fraction: float = 0.25
    maximum_candidate_notes_per_step: int = 32
    minimum_score_improvement: float = 0.10
    minimum_objective_gain: float = 0.0
    edit_penalty: float = 0.75
    semitone_distance_penalty: float = 0.20
    contour_penalty: float = 0.50
    octave_penalty: float = 1.25

    def __post_init__(self) -> None:
        if not 0 <= self.weak_window_threshold <= 100:
            raise ValueError("weak_window_threshold must be between 0 and 100")
        if self.maximum_changes < 0:
            raise ValueError("maximum_changes must be non-negative")
        if not 0 <= self.maximum_change_fraction <= 1:
            raise ValueError("maximum_change_fraction must be between 0 and 1")
        if self.maximum_candidate_notes_per_step <= 0:
            raise ValueError("maximum_candidate_notes_per_step must be positive")
        if self.minimum_score_improvement < 0:
            raise ValueError("minimum_score_improvement must be non-negative")
        for name in (
            "edit_penalty",
            "semitone_distance_penalty",
            "contour_penalty",
            "octave_penalty",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")


DEFAULT_MINIMAL_REPAIR_CONFIG = MinimalRepairConfig()


@dataclass(frozen=True, slots=True)
class NoteEdit:
    """One accepted pitch-only edit and its local-window objective evidence.

    ``score_improvement`` is measured over the weak windows intersected by this
    note.  The result object separately exposes the transparent global
    before/after compatibility scores.
    """

    note_id: int
    original_pitch: int
    repaired_pitch: int
    score_improvement: float
    penalty: float
    objective_gain: float

    def __post_init__(self) -> None:
        if self.note_id < 0:
            raise ValueError("note_id must be non-negative")
        if not 0 <= self.original_pitch <= 127:
            raise ValueError("original_pitch must be between 0 and 127")
        if not 0 <= self.repaired_pitch <= 127:
            raise ValueError("repaired_pitch must be between 0 and 127")
        if self.repaired_pitch == self.original_pitch:
            raise ValueError("an edit must change pitch")
        if self.delta not in ALLOWED_MINIMAL_DELTAS:
            raise ValueError(f"unsupported Minimal-mode pitch delta: {self.delta}")
        if self.score_improvement <= 0:
            raise ValueError("score_improvement must be positive")
        if self.penalty < 0:
            raise ValueError("penalty must be non-negative")

    @property
    def delta(self) -> int:
        """Return the signed semitone change."""

        return self.repaired_pitch - self.original_pitch

    @property
    def semitone_distance(self) -> int:
        """Return the absolute edit distance."""

        return abs(self.delta)

    @property
    def is_octave_move(self) -> bool:
        """Whether this edit preserves pitch class by moving one octave."""

        return self.semitone_distance == 12


@dataclass(frozen=True, slots=True)
class MinimalRepairResult:
    """A repaired clip plus complete before/after analysis and edit details.

    ``objective_gain`` is the sum of per-edit local-window objective gains.
    Global compatibility remains available through ``original_score``,
    ``repaired_score``, and ``score_improvement``.
    """

    original_clip: MidiClip
    repaired_clip: MidiClip
    before_analysis: PairAnalysis
    after_analysis: PairAnalysis
    edits: tuple[NoteEdit, ...]
    objective_gain: float

    @property
    def changed_note_count(self) -> int:
        """Return the number of notes whose pitch changed."""

        return len(self.edits)

    @property
    def original_score(self) -> float:
        """Return the compatibility score before repair."""

        return self.before_analysis.overall_score

    @property
    def repaired_score(self) -> float:
        """Return the compatibility score after repair."""

        return self.after_analysis.overall_score

    @property
    def score_improvement(self) -> float:
        """Return the unpenalized global compatibility improvement."""

        return self.repaired_score - self.original_score

    @property
    def candidate_clip(self) -> MidiClip:
        """Compatibility alias used by candidate-list UIs."""

        return self.repaired_clip

    @property
    def before(self) -> PairAnalysis:
        """Compatibility alias for ``before_analysis``."""

        return self.before_analysis

    @property
    def after(self) -> PairAnalysis:
        """Compatibility alias for ``after_analysis``."""

        return self.after_analysis


RepairResult = MinimalRepairResult
RepairEdit = NoteEdit


@dataclass(frozen=True, slots=True)
class _ScoredCandidate:
    note_id: int
    original_pitch: int
    repaired_pitch: int
    clip: MidiClip
    analysis: PairAnalysis
    score_improvement: float
    global_score_change: float
    penalty: float
    objective_gain: float

    @property
    def delta(self) -> int:
        return self.repaired_pitch - self.original_pitch


def _is_pitch_weak(
    window: WindowAnalysis,
    config: MinimalRepairConfig,
) -> bool:
    """Return whether a window has a conflict pitch edits can address."""

    return (
        window.activity_weight > _EPSILON
        and min(
            window.harmonic_score,
            window.bass_score,
            window.register_score,
        )
        < config.weak_window_threshold
    )


def _note_intersects_window(
    note: MidiNote,
    clip: MidiClip,
    window: WindowAnalysis,
) -> bool:
    onset = note.onset_ticks / clip.ticks_per_beat
    end = note.end_ticks / clip.ticks_per_beat
    return onset < window.end_beat - _EPSILON and end > window.start_beat + _EPSILON


def _eligible_notes(
    clip: MidiClip,
    analysis: PairAnalysis,
    edited_ids: frozenset[int],
    config: MinimalRepairConfig,
) -> tuple[tuple[MidiNote, tuple[WindowAnalysis, ...]], ...]:
    weak_windows = tuple(
        window for window in analysis.windows if _is_pitch_weak(window, config)
    )
    eligible: list[tuple[MidiNote, tuple[WindowAnalysis, ...]]] = []
    for note in clip.notes:
        if (
            note.id in edited_ids
            or note.is_percussion
            or note.duration_ticks <= 0
        ):
            continue
        intersections = tuple(
            window
            for window in weak_windows
            if _note_intersects_window(note, clip, window)
        )
        if intersections:
            eligible.append((note, intersections))
    return tuple(eligible)


def _direction(interval: int) -> int:
    return (interval > 0) - (interval < 0)


def _contour_disruption(
    notes: tuple[MidiNote, ...],
    note_index: int,
    repaired_pitch: int,
) -> float:
    """Measure local melodic-direction and interval-size disruption.

    Simultaneous notes are skipped because their vertical spacing is not a
    melodic contour.  This remains a deliberately modest V0.1 heuristic.
    """

    note = notes[note_index]
    previous = next(
        (
            candidate
            for candidate in reversed(notes[:note_index])
            if (
                candidate.track == note.track
                and candidate.channel == note.channel
                and candidate.onset_ticks < note.onset_ticks
            )
        ),
        None,
    )
    following = next(
        (
            candidate
            for candidate in notes[note_index + 1 :]
            if (
                candidate.track == note.track
                and candidate.channel == note.channel
                and candidate.onset_ticks > note.onset_ticks
            )
        ),
        None,
    )

    disruption = 0.0
    intervals: list[tuple[int, int]] = []
    if previous is not None:
        intervals.append(
            (
                note.pitch - previous.pitch,
                repaired_pitch - previous.pitch,
            )
        )
    if following is not None:
        intervals.append(
            (
                following.pitch - note.pitch,
                following.pitch - repaired_pitch,
            )
        )
    for original_interval, repaired_interval in intervals:
        if _direction(original_interval) != _direction(repaired_interval):
            disruption += 1.0
        disruption += abs(repaired_interval - original_interval) / 12.0
    return disruption


def _candidate_penalty(
    notes: tuple[MidiNote, ...],
    note_index: int,
    repaired_pitch: int,
    config: MinimalRepairConfig,
) -> float:
    delta = repaired_pitch - notes[note_index].pitch
    return (
        config.edit_penalty
        + config.semitone_distance_penalty * abs(delta)
        + config.contour_penalty
        * _contour_disruption(notes, note_index, repaired_pitch)
        + (config.octave_penalty if abs(delta) == 12 else 0.0)
    )


def _candidate_rank(candidate: _ScoredCandidate) -> tuple[float, ...]:
    """Higher tuple wins; final fields provide a documented stable tie-break."""

    return (
        round(candidate.objective_gain, 12),
        round(candidate.score_improvement, 12),
        round(candidate.global_score_change, 12),
        -round(candidate.penalty, 12),
        -abs(candidate.delta),
        -candidate.note_id,
        -candidate.repaired_pitch,
    )


def _candidate_note_rank(
    item: tuple[MidiNote, tuple[WindowAnalysis, ...]],
) -> tuple[float, ...]:
    """Prioritize notes in the weakest addressable windows deterministically."""

    note, windows = item
    weakest_component = min(
        min(window.harmonic_score, window.bass_score, window.register_score)
        for window in windows
    )
    weakest_overall = min(window.overall_score for window in windows)
    return (
        weakest_component,
        weakest_overall,
        note.onset_ticks,
        note.track,
        note.channel,
        note.id,
    )


def _shortlisted_notes(
    eligible: tuple[tuple[MidiNote, tuple[WindowAnalysis, ...]], ...],
    config: MinimalRepairConfig,
) -> tuple[tuple[MidiNote, tuple[WindowAnalysis, ...]], ...]:
    ranked = sorted(eligible, key=_candidate_note_rank)
    return tuple(ranked[: config.maximum_candidate_notes_per_step])


def _notes_overlap(left: MidiNote, right: MidiNote) -> bool:
    return (
        left.onset_ticks < right.end_ticks
        and right.onset_ticks < left.end_ticks
    )


def _introduces_pitch_collision(
    note: MidiNote,
    repaired_pitch: int,
    current_notes: tuple[MidiNote, ...],
    original_pitch_by_id: Mapping[int, int],
) -> bool:
    """Reject newly ambiguous equal-pitch overlaps in one MIDI voice.

    Existing equal-pitch overlaps are not newly introduced.  The guard applies
    only when the two notes had different pitches in the imported source,
    matching preservation-first template-writer safety.
    """

    original_pitch = original_pitch_by_id[note.id]
    return any(
        other.id != note.id
        and other.track == note.track
        and other.channel == note.channel
        and other.pitch == repaired_pitch
        and original_pitch_by_id[other.id] != original_pitch
        and _notes_overlap(note, other)
        for other in current_notes
    )


def _local_window_improvement(
    current_analysis: PairAnalysis,
    candidate_analysis: PairAnalysis,
    affected_windows: tuple[WindowAnalysis, ...],
) -> float:
    """Return weighted improvement over only this note's weak windows."""

    candidate_by_index = {
        window.index: window for window in candidate_analysis.windows
    }
    total_weight = sum(window.activity_weight for window in affected_windows)
    if total_weight <= _EPSILON:
        return 0.0
    current_by_index = {
        window.index: window for window in current_analysis.windows
    }
    return sum(
        (
            candidate_by_index[window.index].overall_score
            - current_by_index[window.index].overall_score
        )
        * window.activity_weight
        for window in affected_windows
    ) / total_weight


def _best_next_edit(
    locked_clip: MidiClip,
    current_clip: MidiClip,
    current_analysis: PairAnalysis,
    edited_ids: frozenset[int],
    original_pitch_by_id: Mapping[int, int],
    repair_config: MinimalRepairConfig,
    analysis_config: AnalysisConfig,
) -> _ScoredCandidate | None:
    note_index_by_id = {note.id: index for index, note in enumerate(current_clip.notes)}
    best: _ScoredCandidate | None = None

    eligible = _eligible_notes(
        current_clip,
        current_analysis,
        edited_ids,
        repair_config,
    )
    for note, weak_windows in _shortlisted_notes(
        eligible,
        repair_config,
    ):
        deltas = _NEARBY_DELTAS
        if any(
            window.register_score < repair_config.weak_window_threshold
            for window in weak_windows
        ):
            deltas += _OCTAVE_DELTAS

        note_index = note_index_by_id[note.id]
        for delta in deltas:
            repaired_pitch = note.pitch + delta
            if not 0 <= repaired_pitch <= 127:
                continue
            if _introduces_pitch_collision(
                note,
                repaired_pitch,
                current_clip.notes,
                original_pitch_by_id,
            ):
                continue
            repaired_note = replace(note, pitch=repaired_pitch)
            candidate_notes = list(current_clip.notes)
            candidate_notes[note_index] = repaired_note
            candidate_clip = current_clip.with_notes(candidate_notes)
            candidate_analysis = analyze_pair(
                locked_clip,
                candidate_clip,
                config=analysis_config,
            )
            global_score_change = (
                candidate_analysis.overall_score - current_analysis.overall_score
            )
            if global_score_change < -_EPSILON:
                continue
            improvement = _local_window_improvement(
                current_analysis,
                candidate_analysis,
                weak_windows,
            )
            if improvement + _EPSILON < repair_config.minimum_score_improvement:
                continue
            penalty = _candidate_penalty(
                current_clip.notes,
                note_index,
                repaired_pitch,
                repair_config,
            )
            objective_gain = improvement - penalty
            if objective_gain <= repair_config.minimum_objective_gain + _EPSILON:
                continue

            candidate = _ScoredCandidate(
                note_id=note.id,
                original_pitch=note.pitch,
                repaired_pitch=repaired_pitch,
                clip=candidate_clip,
                analysis=candidate_analysis,
                score_improvement=improvement,
                global_score_change=global_score_change,
                penalty=penalty,
                objective_gain=objective_gain,
            )
            if best is None or _candidate_rank(candidate) > _candidate_rank(best):
                best = candidate

    return best


def _change_limit(clip: MidiClip, config: MinimalRepairConfig) -> int:
    """Return a floor-based fraction cap with one edit for positive fractions."""

    pitched_note_count = sum(
        not note.is_percussion and note.duration_ticks > 0 for note in clip.notes
    )
    if not pitched_note_count or config.maximum_change_fraction <= 0:
        return 0
    fractional_limit = max(
        1,
        floor(pitched_note_count * config.maximum_change_fraction),
    )
    return min(config.maximum_changes, fractional_limit)


def generate_minimal_repair(
    locked_clip: MidiClip,
    unlocked_clip: MidiClip,
    *,
    repair_config: MinimalRepairConfig = DEFAULT_MINIMAL_REPAIR_CONFIG,
    analysis_config: AnalysisConfig = DEFAULT_ANALYSIS_CONFIG,
) -> MinimalRepairResult:
    """Generate one conservative, deterministic pitch-only repair candidate.

    Each greedy step considers only notes intersecting a weak harmonic, bass,
    or register window, with a deterministic cap on candidate notes.  Candidate
    gain is measured over the affected weak windows, while global compatibility
    may not decrease.  Nearby semitone moves are always available; octave moves
    are considered only for windows with weak register compatibility.  Rhythm,
    onset, duration, velocity, track, channel, note identity, and clip metadata
    are never changed.
    """

    before = analyze_pair(locked_clip, unlocked_clip, config=analysis_config)
    current_clip = unlocked_clip
    current_analysis = before
    edits: list[NoteEdit] = []
    edited_ids: frozenset[int] = frozenset()
    original_pitch_by_id = {
        note.id: note.pitch for note in unlocked_clip.notes
    }

    for _ in range(_change_limit(unlocked_clip, repair_config)):
        candidate = _best_next_edit(
            locked_clip,
            current_clip,
            current_analysis,
            edited_ids,
            original_pitch_by_id,
            repair_config,
            analysis_config,
        )
        if candidate is None:
            break
        edits.append(
            NoteEdit(
                note_id=candidate.note_id,
                original_pitch=candidate.original_pitch,
                repaired_pitch=candidate.repaired_pitch,
                score_improvement=candidate.score_improvement,
                penalty=candidate.penalty,
                objective_gain=candidate.objective_gain,
            )
        )
        edited_ids = frozenset((*edited_ids, candidate.note_id))
        current_clip = candidate.clip
        current_analysis = candidate.analysis

    objective_gain = sum(edit.objective_gain for edit in edits)
    return MinimalRepairResult(
        original_clip=unlocked_clip,
        repaired_clip=current_clip,
        before_analysis=before,
        after_analysis=current_analysis,
        edits=tuple(edits),
        objective_gain=objective_gain,
    )
