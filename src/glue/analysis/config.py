"""Central configuration for GLUE's deterministic compatibility heuristics."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose


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
    attack_accent: float = 0.25
    downbeat_accent: float = 0.15
    reason_threshold: float = 65.0
    maximum_reasons: int = 5

    def __post_init__(self) -> None:
        if self.window_beats <= 0:
            raise ValueError("window_beats must be positive")
        if self.rhythm_subdivisions <= 0:
            raise ValueError("rhythm_subdivisions must be positive")
        if not 0 <= self.reason_threshold <= 100:
            raise ValueError("reason_threshold must be between 0 and 100")
        if self.maximum_reasons < 0:
            raise ValueError("maximum_reasons must be non-negative")
        weights = self.component_weights
        if any(weight < 0 for weight in weights):
            raise ValueError("component weights must be non-negative")
        if not isclose(sum(weights), 1.0, abs_tol=1e-9):
            raise ValueError("component weights must sum to 1")

    @property
    def component_weights(self) -> tuple[float, float, float, float]:
        """Return weights in harmonic, bass, register, rhythm order."""

        return (
            self.harmonic_weight,
            self.bass_weight,
            self.register_weight,
            self.rhythm_weight,
        )


DEFAULT_ANALYSIS_CONFIG = AnalysisConfig()

