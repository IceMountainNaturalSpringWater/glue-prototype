"""Pure, deterministic MIDI compatibility analysis."""

from .compatibility import (
    INTERVAL_COMPATIBILITY,
    MAJOR_SCALE_INTERVALS,
    MINOR_SCALE_INTERVALS,
    infer_local_harmony_candidates,
    scale_pitch_classes,
    score_bass_compatibility,
    score_harmonic_compatibility,
    score_register_compatibility,
    score_rhythm_compatibility,
)
from .config import DEFAULT_ANALYSIS_CONFIG, AnalysisConfig
from .key import (
    MAJOR_PROFILE,
    MINOR_PROFILE,
    duration_weighted_histogram,
    estimate_combined_key,
    estimate_key,
    estimate_key_from_histogram,
)
from .pair import analyze_compatibility, analyze_pair, analyze_window
from .results import (
    BarAnalysis,
    ChordQuality,
    CompatibilityAnalysis,
    ConflictReason,
    KeyCandidate,
    KeyEstimate,
    LocalHarmonyCandidate,
    PairAnalysis,
    WindowAnalysis,
)

__all__ = [
    "DEFAULT_ANALYSIS_CONFIG",
    "INTERVAL_COMPATIBILITY",
    "MAJOR_PROFILE",
    "MAJOR_SCALE_INTERVALS",
    "MINOR_PROFILE",
    "MINOR_SCALE_INTERVALS",
    "AnalysisConfig",
    "BarAnalysis",
    "ChordQuality",
    "CompatibilityAnalysis",
    "ConflictReason",
    "KeyCandidate",
    "KeyEstimate",
    "LocalHarmonyCandidate",
    "PairAnalysis",
    "WindowAnalysis",
    "analyze_compatibility",
    "analyze_pair",
    "analyze_window",
    "duration_weighted_histogram",
    "estimate_combined_key",
    "estimate_key",
    "estimate_key_from_histogram",
    "infer_local_harmony_candidates",
    "scale_pitch_classes",
    "score_bass_compatibility",
    "score_harmonic_compatibility",
    "score_register_compatibility",
    "score_rhythm_compatibility",
]
