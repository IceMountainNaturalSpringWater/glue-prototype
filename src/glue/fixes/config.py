"""Immutable V0.3 repair strategies, constraints, and bounded-search policy."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from math import ceil, isfinite
from numbers import Real

from .minimal import RepairPreset


class EditingStrategy(StrEnum):
    """Describe which side of a two-clip repair may change."""

    PRESERVE_A = "preserve-a"
    PRESERVE_B = "preserve-b"
    SHARED = "shared"
    CUSTOM = "custom"

    # Descriptive aliases keep call sites readable without changing serialized values.
    SHARED_COMPROMISE = "shared"
    CUSTOM_PRESERVATION = "custom"

    @property
    def label(self) -> str:
        """Return the user-facing strategy name."""

        return {
            EditingStrategy.PRESERVE_A: "Preserve A",
            EditingStrategy.PRESERVE_B: "Preserve B",
            EditingStrategy.SHARED: "Shared Compromise",
            EditingStrategy.CUSTOM: "Custom Preservation",
        }[self]


# An alternative name is useful to callers that describe these as repair policies.
RepairStrategy = EditingStrategy


def normalize_editing_strategy(
    strategy: EditingStrategy | str,
) -> EditingStrategy:
    """Normalize enum values and common display/identifier spellings."""

    if isinstance(strategy, EditingStrategy):
        return strategy
    if not isinstance(strategy, str):
        raise TypeError("strategy must be an EditingStrategy or string")
    normalized = strategy.strip().lower().replace("_", "-").replace(" ", "-")
    aliases = {
        "preserve-a": EditingStrategy.PRESERVE_A,
        "preserve-b": EditingStrategy.PRESERVE_B,
        "shared": EditingStrategy.SHARED,
        "shared-compromise": EditingStrategy.SHARED,
        "custom": EditingStrategy.CUSTOM,
        "custom-preservation": EditingStrategy.CUSTOM,
    }
    try:
        return aliases[normalized]
    except KeyError as exc:
        choices = ", ".join(strategy.label for strategy in EditingStrategy)
        raise ValueError(f"strategy must be one of: {choices}") from exc


def normalize_preservation(value: Real) -> float:
    """Return a 0-1 preservation value, accepting either fractions or percents."""

    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError("preservation must be a number between 0 and 1 or 0 and 100")
    numeric = float(value)
    if 0.0 <= numeric <= 1.0:
        return numeric
    if 1.0 < numeric <= 100.0:
        return numeric / 100.0
    raise ValueError("preservation must be between 0 and 1 or 0 and 100")


@dataclass(frozen=True, slots=True)
class ClipRepairConstraints:
    """Independent pitch-repair permissions and budget for one clip.

    ``preservation`` uses a normalized 0-1 scale. A value of ``1.0`` is a hard
    lock, not merely a large soft penalty. Rhythm edits are represented so the
    constraint model can grow later, but are intentionally unsupported in V0.3.
    """

    preservation: float
    allow_pitch_edits: bool = True
    allow_octave_edits: bool = True
    allow_rhythm_edits: bool = False
    max_note_changes: int = 1

    def __post_init__(self) -> None:
        if isinstance(self.preservation, bool) or not isinstance(
            self.preservation,
            Real,
        ):
            raise TypeError("preservation must be a number between 0 and 1")
        normalized = float(self.preservation)
        if not 0.0 <= normalized <= 1.0:
            raise ValueError("preservation must be between 0 and 1")
        object.__setattr__(self, "preservation", normalized)
        for name in (
            "allow_pitch_edits",
            "allow_octave_edits",
            "allow_rhythm_edits",
        ):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be a bool")
        if self.allow_rhythm_edits:
            raise ValueError("rhythm edits are not supported in GLUE V0.3")
        if isinstance(self.max_note_changes, bool) or not isinstance(
            self.max_note_changes,
            int,
        ):
            raise TypeError("max_note_changes must be an integer")
        if self.max_note_changes < 0:
            raise ValueError("max_note_changes must be non-negative")

    @property
    def is_locked(self) -> bool:
        """Return whether this clip is prohibited from receiving pitch edits."""

        return (
            self.preservation >= 1.0
            or not self.allow_pitch_edits
            or self.max_note_changes == 0
        )

    @property
    def preservation_percent(self) -> int:
        """Return the normalized value as a stable whole-number percentage."""

        return round(self.preservation * 100)


@dataclass(frozen=True, slots=True)
class JointObjectiveWeights:
    """Centralized coefficients for ranking complete repaired pairs.

    Pair candidates minimize a cost. ``remaining_conflict`` keeps estimated
    compatibility dominant. The disruption terms prefer fewer, smaller edits;
    preservation makes edits progressively more expensive on the protected
    side. ``introduced_unison`` and ``convergence`` prevent a simplistic score
    gain from collapsing independent lines onto the same pitches.
    """

    remaining_conflict: float = 1.0
    edit_count: float = 0.50
    preservation: float = 8.00
    semitone_distance: float = 0.10
    octave: float = 0.75
    contour: float = 0.40
    motif: float = 0.20
    introduced_unison: float = 12.00
    convergence: float = 0.25

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Real):
                raise TypeError(f"{name} must be a number")
            if not isfinite(value):
                raise ValueError(f"{name} must be finite")
            if value < 0:
                raise ValueError(f"{name} must be non-negative")


@dataclass(frozen=True, slots=True)
class JointSearchBounds:
    """Explicit deterministic bounds that keep full-pair search interactive."""

    candidate_notes_per_clip: int = 6
    # Keep the complete Minimal pitch vocabulary (four nearby moves plus two
    # octave moves) available.  Evaluation and beam limits, rather than a
    # direction-biased prefix of that vocabulary, bound the joint search.
    candidate_pitches_per_note: int = 6
    beam_width: int = 6
    maximum_iterations: int = 2
    maximum_total_edits: int = 2
    maximum_change_fraction: float = 0.25
    successors_per_state: int = 24
    paired_options_per_clip: int = 6
    coordinated_options_per_clip: int = 2
    maximum_evaluations: int = 400
    minimum_score_improvement: float = 0.05

    def __post_init__(self) -> None:
        for name in (
            "candidate_notes_per_clip",
            "candidate_pitches_per_note",
            "beam_width",
            "maximum_iterations",
            "successors_per_state",
            "paired_options_per_clip",
            "coordinated_options_per_clip",
            "maximum_evaluations",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if (
            isinstance(self.maximum_total_edits, bool)
            or not isinstance(self.maximum_total_edits, int)
        ):
            raise TypeError("maximum_total_edits must be an integer")
        if self.maximum_total_edits < 0:
            raise ValueError("maximum_total_edits must be non-negative")
        if self.maximum_iterations < self.maximum_total_edits:
            raise ValueError(
                "maximum_iterations must allow the configured maximum_total_edits"
            )
        for name in (
            "maximum_change_fraction",
            "minimum_score_improvement",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Real):
                raise TypeError(f"{name} must be a number")
            if not isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.minimum_score_improvement < 0:
            raise ValueError("minimum_score_improvement must be non-negative")
        if not 0 <= self.maximum_change_fraction <= 1:
            raise ValueError("maximum_change_fraction must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class PairRepairConfig:
    """Complete immutable policy for a two-clip repair."""

    strategy: EditingStrategy
    preset: RepairPreset
    clip_a: ClipRepairConstraints
    clip_b: ClipRepairConstraints
    search: JointSearchBounds
    objective: JointObjectiveWeights = JointObjectiveWeights()

    def __post_init__(self) -> None:
        if not isinstance(self.strategy, EditingStrategy):
            raise TypeError("strategy must be an EditingStrategy")
        if not isinstance(self.preset, RepairPreset):
            raise TypeError("preset must be a RepairPreset")
        if self.strategy is EditingStrategy.PRESERVE_A and not self.clip_a.is_locked:
            raise ValueError("Preserve A requires Clip A to be fully locked")
        if self.strategy is EditingStrategy.PRESERVE_B and not self.clip_b.is_locked:
            raise ValueError("Preserve B requires Clip B to be fully locked")


@dataclass(frozen=True, slots=True)
class _PresetProfile:
    """Low/high deterministic search bounds for one repair preset."""

    minimum_search: JointSearchBounds
    maximum_search: JointSearchBounds
    maximum_changes_per_clip: int


def _preset_profile(preset: RepairPreset) -> _PresetProfile:
    """Return bounded search endpoints used by preservation interpolation."""

    if preset is RepairPreset.MINIMAL:
        return _PresetProfile(
            minimum_search=JointSearchBounds(
                candidate_notes_per_clip=4,
                # High preservation searches nearby moves only; progressively
                # lower preservation restores both one-octave alternatives.
                candidate_pitches_per_note=4,
                beam_width=4,
                maximum_iterations=2,
                maximum_total_edits=2,
                maximum_change_fraction=0.125,
                successors_per_state=16,
                paired_options_per_clip=2,
                coordinated_options_per_clip=1,
                maximum_evaluations=400,
            ),
            maximum_search=JointSearchBounds(
                candidate_notes_per_clip=8,
                candidate_pitches_per_note=6,
                beam_width=8,
                maximum_iterations=4,
                maximum_total_edits=2,
                maximum_change_fraction=0.25,
                successors_per_state=32,
                paired_options_per_clip=3,
                coordinated_options_per_clip=2,
                maximum_evaluations=800,
            ),
            maximum_changes_per_clip=2,
        )
    if preset is RepairPreset.BALANCED:
        return _PresetProfile(
            minimum_search=JointSearchBounds(
                candidate_notes_per_clip=6,
                candidate_pitches_per_note=8,
                beam_width=6,
                maximum_iterations=2,
                maximum_total_edits=2,
                maximum_change_fraction=0.35,
                successors_per_state=24,
                paired_options_per_clip=3,
                coordinated_options_per_clip=2,
                maximum_evaluations=1_200,
            ),
            maximum_search=JointSearchBounds(
                candidate_notes_per_clip=10,
                # Eight nearby moves plus both octave alternatives.
                candidate_pitches_per_note=10,
                beam_width=10,
                maximum_iterations=8,
                maximum_total_edits=8,
                maximum_change_fraction=0.60,
                successors_per_state=48,
                paired_options_per_clip=5,
                coordinated_options_per_clip=4,
                maximum_evaluations=2_000,
            ),
            maximum_changes_per_clip=4,
        )
    return _PresetProfile(
        minimum_search=JointSearchBounds(
            candidate_notes_per_clip=8,
            # Preserve all fourteen nearby moves and both true octaves even at
            # high preservation; the final two slots admit local harmony.
            candidate_pitches_per_note=18,
            beam_width=8,
            maximum_iterations=4,
            maximum_total_edits=4,
            maximum_change_fraction=0.50,
            successors_per_state=36,
            paired_options_per_clip=4,
            coordinated_options_per_clip=4,
            maximum_evaluations=2_500,
        ),
        maximum_search=JointSearchBounds(
            candidate_notes_per_clip=14,
            # Creative adds room for bounded public local-harmony alternatives.
            candidate_pitches_per_note=20,
            beam_width=14,
            maximum_iterations=16,
            maximum_total_edits=16,
            maximum_change_fraction=1.0,
            successors_per_state=72,
            paired_options_per_clip=8,
            coordinated_options_per_clip=8,
            maximum_evaluations=5_000,
        ),
        maximum_changes_per_clip=8,
    )


def _scaled_integer(minimum: int, maximum: int, openness: float) -> int:
    """Interpolate an integer search bound, preserving exact endpoints."""

    return ceil(minimum + (maximum - minimum) * openness)


def _scaled_edit_budget(preservation: float, maximum: int) -> int:
    """Return a hard lock at 100%, otherwise at least one legal pitch edit."""

    if preservation >= 1.0:
        return 0
    return max(1, ceil(maximum * (1.0 - preservation)))


def _scaled_search(
    profile: _PresetProfile,
    openness: float,
    total_edit_budget: int,
) -> JointSearchBounds:
    """Interpolate search breadth from preservation while keeping it bounded."""

    low = profile.minimum_search
    high = profile.maximum_search

    def scaled(name: str) -> int:
        return _scaled_integer(
            getattr(low, name),
            getattr(high, name),
            openness,
        )

    total_edits = min(total_edit_budget, high.maximum_total_edits)
    iterations = max(
        total_edits,
        scaled("maximum_iterations"),
    )
    return replace(
        low,
        candidate_notes_per_clip=scaled("candidate_notes_per_clip"),
        candidate_pitches_per_note=scaled("candidate_pitches_per_note"),
        beam_width=scaled("beam_width"),
        maximum_iterations=iterations,
        maximum_total_edits=total_edits,
        maximum_change_fraction=(
            low.maximum_change_fraction
            + (
                high.maximum_change_fraction
                - low.maximum_change_fraction
            )
            * openness
        ),
        successors_per_state=scaled("successors_per_state"),
        paired_options_per_clip=scaled("paired_options_per_clip"),
        coordinated_options_per_clip=scaled(
            "coordinated_options_per_clip",
        ),
        maximum_evaluations=scaled("maximum_evaluations"),
    )


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


def _constraints(preservation: float, budget: int) -> ClipRepairConstraints:
    locked = preservation >= 1.0 or budget == 0
    return ClipRepairConstraints(
        preservation=preservation,
        allow_pitch_edits=not locked,
        allow_octave_edits=not locked,
        max_note_changes=0 if locked else budget,
    )


def pair_repair_config_for(
    strategy: EditingStrategy | str,
    preset: RepairPreset | str = RepairPreset.MINIMAL,
    *,
    preservation_a: Real | None = None,
    preservation_b: Real | None = None,
) -> PairRepairConfig:
    """Build calibrated constraints for a strategy and preset.

    Fractional values (``0.85``) and whole percentages (``85``) are both
    accepted. Shared and Custom default to cautious 85% preservation. The
    editable side of a one-sided strategy defaults to V0.2's 50% midpoint.
    """

    resolved_strategy = normalize_editing_strategy(strategy)
    resolved_preset = _normalize_preset(preset)
    profile = _preset_profile(resolved_preset)
    requested_a = (
        normalize_preservation(preservation_a)
        if preservation_a is not None
        else None
    )
    requested_b = (
        normalize_preservation(preservation_b)
        if preservation_b is not None
        else None
    )

    if resolved_strategy is EditingStrategy.PRESERVE_A:
        normalized_a = 1.0
        normalized_b = 0.50 if requested_b is None else requested_b
    elif resolved_strategy is EditingStrategy.PRESERVE_B:
        normalized_a = 0.50 if requested_a is None else requested_a
        normalized_b = 1.0
    else:
        normalized_a = 0.85 if requested_a is None else requested_a
        normalized_b = 0.85 if requested_b is None else requested_b

    budget_a = _scaled_edit_budget(
        normalized_a,
        profile.maximum_changes_per_clip,
    )
    budget_b = _scaled_edit_budget(
        normalized_b,
        profile.maximum_changes_per_clip,
    )
    editable_openness = tuple(
        1.0 - preservation
        for preservation, budget in (
            (normalized_a, budget_a),
            (normalized_b, budget_b),
        )
        if budget > 0
    )
    openness = max(editable_openness, default=0.0)
    search = _scaled_search(
        profile,
        openness,
        budget_a + budget_b,
    )

    return PairRepairConfig(
        strategy=resolved_strategy,
        preset=resolved_preset,
        clip_a=_constraints(normalized_a, budget_a),
        clip_b=_constraints(normalized_b, budget_b),
        search=search,
    )


DEFAULT_PAIR_REPAIR_CONFIG = pair_repair_config_for(EditingStrategy.PRESERVE_A)


__all__ = [
    "DEFAULT_PAIR_REPAIR_CONFIG",
    "ClipRepairConstraints",
    "EditingStrategy",
    "JointObjectiveWeights",
    "JointSearchBounds",
    "PairRepairConfig",
    "RepairStrategy",
    "normalize_editing_strategy",
    "normalize_preservation",
    "pair_repair_config_for",
]
