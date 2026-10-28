"""Central configuration for GLUE's deterministic compatibility heuristics."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose, isfinite
from numbers import Real


@dataclass(frozen=True, slots=True)
class AnalysisConfig:
    """Tunable analysis constants kept outside the scoring implementation.

    A quarter note is the timeline unit.  Time-signature denominators are used
    for bar summaries, but do not change this unit.
    """

    window_beats: float = 1.0
    rhythm_subdivisions: int = 8
    harmonic_weight: float = 0.50
    bass_weight: float = 0.20
    register_weight: float = 0.15
    rhythm_weight: float = 0.15
    harmonic_vertical_weight: float = 0.45
    harmonic_scale_weight: float = 0.14
    harmonic_chord_agreement_weight: float = 0.26
    harmonic_joint_fit_weight: float = 0.15
    chord_coverage_weight: float = 5.0
    chord_completeness_weight: float = 1.5
    chord_root_weight: float = 0.5
    local_harmony_candidate_count: int = 3
    attack_accent: float = 0.25
    downbeat_accent: float = 0.15
    reason_threshold: float = 65.0
    maximum_reasons: int = 5

    def __post_init__(self) -> None:
        if self.window_beats <= 0:
            raise ValueError("window_beats must be positive")
        if self.rhythm_subdivisions <= 0:
            raise ValueError("rhythm_subdivisions must be positive")
        if self.local_harmony_candidate_count <= 0:
            raise ValueError("local_harmony_candidate_count must be positive")
        if not 0 <= self.reason_threshold <= 100:
            raise ValueError("reason_threshold must be between 0 and 100")
        if self.maximum_reasons < 0:
            raise ValueError("maximum_reasons must be non-negative")
        weights = self.component_weights
        if any(weight < 0 for weight in weights):
            raise ValueError("component weights must be non-negative")
        if not isclose(sum(weights), 1.0, abs_tol=1e-9):
            raise ValueError("component weights must sum to 1")
        harmonic_weights = self.harmonic_component_weights
        if any(weight < 0 for weight in harmonic_weights):
            raise ValueError("harmonic component weights must be non-negative")
        if not isclose(sum(harmonic_weights), 1.0, abs_tol=1e-9):
            raise ValueError("harmonic component weights must sum to 1")
        chord_weights = (
            self.chord_coverage_weight,
            self.chord_completeness_weight,
            self.chord_root_weight,
        )
        if any(weight < 0 for weight in chord_weights):
            raise ValueError("chord inference weights must be non-negative")

    @property
    def component_weights(self) -> tuple[float, float, float, float]:
        """Return weights in harmonic, bass, register, rhythm order."""

        return (
            self.harmonic_weight,
            self.bass_weight,
            self.register_weight,
            self.rhythm_weight,
        )

    @property
    def harmonic_component_weights(self) -> tuple[float, float, float, float]:
        """Return vertical, scale, chord-agreement, and joint-fit weights."""

        return (
            self.harmonic_vertical_weight,
            self.harmonic_scale_weight,
            self.harmonic_chord_agreement_weight,
            self.harmonic_joint_fit_weight,
        )


DEFAULT_ANALYSIS_CONFIG = AnalysisConfig()


@dataclass(frozen=True, slots=True)
class SingleAnalysisConfig:
    """Central policy for deterministic, conservative one-clip analysis.

    The thresholds are intentionally cautious.  They identify material worth
    reviewing, not notes that are objectively incorrect.
    """

    window_beats: float = 1.0
    high_confidence_threshold: float = 0.65
    minimum_key_confidence: float = 0.18
    maximum_alternatives: int = 6
    maximum_suggestions: int = 96
    leap_threshold_semitones: int = 12
    step_resolution_semitones: int = 2
    voice_leading_threshold_semitones: int = 8
    crowding_minimum_notes: int = 4
    crowding_span_semitones: int = 12
    motif_minimum_length: int = 3
    motif_maximum_length: int = 4
    motif_maximum_mismatches: int = 2
    harmonic_weight: float = 0.30
    melodic_weight: float = 0.18
    voice_leading_weight: float = 0.14
    overlap_weight: float = 0.12
    register_weight: float = 0.10
    bass_weight: float = 0.10
    motif_weight: float = 0.06

    def __post_init__(self) -> None:
        if (
            isinstance(self.window_beats, bool)
            or not isinstance(self.window_beats, Real)
        ):
            raise TypeError("window_beats must be a finite number")
        if not isfinite(self.window_beats) or self.window_beats <= 0:
            raise ValueError("window_beats must be positive")
        for name in (
            "high_confidence_threshold",
            "minimum_key_confidence",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Real):
                raise TypeError(f"{name} must be a finite number")
            if not isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        for name in (
            "maximum_alternatives",
            "maximum_suggestions",
            "leap_threshold_semitones",
            "step_resolution_semitones",
            "voice_leading_threshold_semitones",
            "crowding_minimum_notes",
            "crowding_span_semitones",
            "motif_minimum_length",
            "motif_maximum_length",
            "motif_maximum_mismatches",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if self.motif_minimum_length > self.motif_maximum_length:
            raise ValueError(
                "motif_minimum_length must not exceed motif_maximum_length"
            )
        weights = self.component_weights
        if any(
            isinstance(weight, bool)
            or not isinstance(weight, Real)
            or not isfinite(weight)
            for weight in weights
        ):
            raise TypeError("single-analysis component weights must be finite numbers")
        if any(weight < 0 for weight in weights):
            raise ValueError("single-analysis component weights must be non-negative")
        if not isclose(sum(weights), 1.0, abs_tol=1e-9):
            raise ValueError("single-analysis component weights must sum to 1")

    @property
    def component_weights(self) -> tuple[float, ...]:
        """Return weights in the same order as single-analysis score fields."""

        return (
            self.harmonic_weight,
            self.melodic_weight,
            self.voice_leading_weight,
            self.overlap_weight,
            self.register_weight,
            self.bass_weight,
            self.motif_weight,
        )


DEFAULT_SINGLE_ANALYSIS_CONFIG = SingleAnalysisConfig()
