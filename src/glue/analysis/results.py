"""Public immutable result models returned by the analysis API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

KeyMode = Literal["major", "minor"]
ComponentName = Literal["harmonic", "bass", "register", "rhythm"]

PITCH_CLASS_NAMES = (
    "C",
    "C#",
    "D",
    "D#",
    "E",
    "F",
    "F#",
    "G",
    "G#",
    "A",
    "A#",
    "B",
)


@dataclass(frozen=True, slots=True)
class KeyCandidate:
    """One major/minor key-profile match."""

    tonic_pc: int
    mode: KeyMode
    correlation: float

    def __post_init__(self) -> None:
        if not 0 <= self.tonic_pc <= 11:
            raise ValueError("tonic_pc must be between 0 and 11")
        if self.mode not in ("major", "minor"):
            raise ValueError("mode must be 'major' or 'minor'")
        if not -1.000_001 <= self.correlation <= 1.000_001:
            raise ValueError("correlation must be between -1 and 1")

    @property
    def label(self) -> str:
        """Return a deterministic, canonical-sharp key label."""

        return f"{PITCH_CLASS_NAMES[self.tonic_pc]} {self.mode}"

    @property
    def match_score(self) -> float:
        """Map the profile correlation from ``[-1, 1]`` to ``[0, 100]``."""

        return max(0.0, min(100.0, (self.correlation + 1.0) * 50.0))


@dataclass(frozen=True, slots=True)
class KeyEstimate:
    """Ranked key candidates plus a conservative ambiguity confidence."""

    candidates: tuple[KeyCandidate, ...]
    confidence: float

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")

    @classmethod
    def unknown(cls) -> KeyEstimate:
        """Return an estimate for empty or completely uniform pitch material."""

        return cls(candidates=(), confidence=0.0)

    @property
    def top(self) -> KeyCandidate | None:
        """Return the strongest key candidate, if any."""

        return self.candidates[0] if self.candidates else None

    @property
    def tonic_pc(self) -> int | None:
        """Convenience access to the strongest candidate's tonic."""

        return self.top.tonic_pc if self.top else None

    @property
    def mode(self) -> KeyMode | None:
        """Convenience access to the strongest candidate's mode."""

        return self.top.mode if self.top else None

    @property
    def label(self) -> str:
        """Return the strongest key label or ``Unknown``."""

        return self.top.label if self.top else "Unknown"


@dataclass(frozen=True, slots=True)
class ConflictReason:
    """A transparent heuristic warning attached to one analysis window."""

    component: ComponentName
    score: float
    window_index: int
    message: str


@dataclass(frozen=True, slots=True)
class WindowAnalysis:
    """Compatibility component scores for one half-open beat window."""

    index: int
    start_beat: float
    end_beat: float
    harmonic_score: float
    bass_score: float
    register_score: float
    rhythm_score: float
    overall_score: float
    activity_weight: float
    reasons: tuple[ConflictReason, ...] = ()
    bar_index: int = 0

    @property
    def score(self) -> float:
        """Compatibility alias for the combined window score."""

        return self.overall_score


@dataclass(frozen=True, slots=True)
class BarAnalysis:
    """A lightweight aggregate of windows assigned to one notated bar."""

    index: int
    start_beat: float
    end_beat: float
    overall_score: float
    window_indices: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class PairAnalysis:
    """Complete key, component, timeline, and explanation result for two clips."""

    key_a: KeyEstimate
    key_b: KeyEstimate
    combined_key: KeyEstimate
    harmonic_score: float
    bass_score: float
    register_score: float
    rhythm_score: float
    overall_score: float
    windows: tuple[WindowAnalysis, ...]
    reasons: tuple[ConflictReason, ...] = ()
    bars: tuple[BarAnalysis, ...] = ()

    @property
    def score(self) -> float:
        """Compatibility alias for the combined pair score."""

        return self.overall_score

    @property
    def component_scores(self) -> dict[str, float]:
        """Return component scores keyed for UI display."""

        return {
            "harmonic": self.harmonic_score,
            "bass": self.bass_score,
            "register": self.register_score,
            "rhythm": self.rhythm_score,
        }


# A descriptive alias is convenient for callers that do not use "pair" terminology.
CompatibilityAnalysis = PairAnalysis
