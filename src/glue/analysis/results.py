"""Public immutable result models returned by the analysis API."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Literal

from glue.models import MidiClip

from .config import SingleAnalysisConfig

KeyMode = Literal["major", "minor"]
ComponentName = Literal["harmonic", "bass", "register", "rhythm"]
ChordQuality = Literal[
    "major",
    "minor",
    "diminished",
    "augmented",
    "major seventh",
    "dominant seventh",
    "minor seventh",
    "half-diminished seventh",
    "diminished seventh",
    "other",
]

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
class LocalHarmonyCandidate:
    """One transparent local chord interpretation for a clip window."""

    root_pc: int
    quality: ChordQuality
    pitch_classes: tuple[int, ...]
    probability: float
    coverage: float
    completeness: float

    def __post_init__(self) -> None:
        if not 0 <= self.root_pc <= 11:
            raise ValueError("root_pc must be between 0 and 11")
        if (
            not self.pitch_classes
            or tuple(sorted(set(self.pitch_classes))) != self.pitch_classes
            or any(not 0 <= pitch_class <= 11 for pitch_class in self.pitch_classes)
        ):
            raise ValueError(
                "pitch_classes must be a non-empty sorted tuple of unique values "
                "between 0 and 11"
            )
        for name, value in (
            ("probability", self.probability),
            ("coverage", self.coverage),
            ("completeness", self.completeness),
        ):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")

    @property
    def label(self) -> str:
        """Return a deterministic canonical-sharp chord label."""

        return f"{PITCH_CLASS_NAMES[self.root_pc]} {self.quality}"


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
    local_harmony_a: tuple[LocalHarmonyCandidate, ...] = ()
    local_harmony_b: tuple[LocalHarmonyCandidate, ...] = ()

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


class SingleSuggestionCategory(StrEnum):
    """Stable categories exposed by the one-clip suggestion API."""

    HARMONIC_CONFLICT = "harmonic-conflict"
    MELODIC_LEAP = "melodic-leap"
    VOICE_LEADING = "voice-leading"
    DUPLICATE_OVERLAP = "duplicate-overlap"
    REGISTER_CROWDING = "register-crowding"
    BASS_CONFLICT = "bass-conflict"
    MOTIF_INCONSISTENCY = "motif-inconsistency"

    @property
    def label(self) -> str:
        """Return a short display label without making a diagnosis."""

        return {
            SingleSuggestionCategory.HARMONIC_CONFLICT: "Possible harmonic conflict",
            SingleSuggestionCategory.MELODIC_LEAP: "Possible melodic discontinuity",
            SingleSuggestionCategory.VOICE_LEADING: "Possible weak voice leading",
            SingleSuggestionCategory.DUPLICATE_OVERLAP: "Possible duplicate or overlap",
            SingleSuggestionCategory.REGISTER_CROWDING: "Possible register crowding",
            SingleSuggestionCategory.BASS_CONFLICT: "Possible bass conflict",
            SingleSuggestionCategory.MOTIF_INCONSISTENCY: (
                "Possible repeated-motif inconsistency"
            ),
        }[self]


@dataclass(frozen=True, slots=True)
class SingleClipSuggestion:
    """One qualified, note-addressable single-clip review suggestion."""

    suggestion_id: str
    target_note_id: int
    related_note_ids: tuple[int, ...]
    original_pitch: int
    onset_ticks: int
    duration_ticks: int
    track: int
    channel: int
    onset_beats: float
    duration_beats: float
    category: SingleSuggestionCategory
    confidence: float
    explanation: str
    alternatives: tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.suggestion_id, str) or not self.suggestion_id.strip():
            raise ValueError("suggestion_id must be a non-empty string")
        if self.target_note_id < 0:
            raise ValueError("target_note_id must be non-negative")
        if (
            tuple(sorted(set(self.related_note_ids))) != self.related_note_ids
            or any(note_id < 0 for note_id in self.related_note_ids)
            or self.target_note_id in self.related_note_ids
        ):
            raise ValueError(
                "related_note_ids must be sorted, unique, non-negative, "
                "and exclude target_note_id"
            )
        if not 0 <= self.original_pitch <= 127:
            raise ValueError("original_pitch must be between 0 and 127")
        if self.onset_ticks < 0 or self.duration_ticks < 0:
            raise ValueError("suggestion timing ticks must be non-negative")
        if self.track < 0:
            raise ValueError("track must be non-negative")
        if not 0 <= self.channel <= 15:
            raise ValueError("channel must be between 0 and 15")
        if (
            not isfinite(self.onset_beats)
            or not isfinite(self.duration_beats)
            or self.onset_beats < 0
            or self.duration_beats < 0
        ):
            raise ValueError("suggestion beat location must be finite and non-negative")
        if not isinstance(self.category, SingleSuggestionCategory):
            raise TypeError("category must be a SingleSuggestionCategory")
        if not isfinite(self.confidence) or not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if not isinstance(self.explanation, str) or not self.explanation.strip():
            raise ValueError("explanation must be a non-empty string")
        if (
            not self.alternatives
            or len(set(self.alternatives)) != len(self.alternatives)
            or any(
                isinstance(pitch, bool)
                or not isinstance(pitch, int)
                or not 0 <= pitch <= 127
                or pitch == self.original_pitch
                for pitch in self.alternatives
            )
        ):
            raise ValueError(
                "alternatives must contain unique replacement MIDI pitches"
            )

    @property
    def id(self) -> str:
        """Compact compatibility alias for GUI selection models."""

        return self.suggestion_id

    @property
    def note_id(self) -> int:
        """Compatibility alias for the editable target note."""

        return self.target_note_id

    @property
    def affected_note_ids(self) -> tuple[int, ...]:
        """Return the target followed by any notes that provide context."""

        return (self.target_note_id, *self.related_note_ids)

    @property
    def location(self) -> tuple[int, int, int, int]:
        """Return track, channel, onset, and duration ticks."""

        return (
            self.track,
            self.channel,
            self.onset_ticks,
            self.duration_ticks,
        )


@dataclass(frozen=True, slots=True)
class SingleClipAnalysis:
    """Complete deterministic analysis of one MIDI clip.

    Scores are qualified estimates of internal consistency.  A high score is
    not proof that the music should remain unchanged.
    """

    key: KeyEstimate
    harmonic_score: float
    melodic_score: float
    voice_leading_score: float
    overlap_score: float
    register_score: float
    bass_score: float
    motif_score: float
    internal_consistency_score: float
    suggestions: tuple[SingleClipSuggestion, ...]
    high_confidence_threshold: float = 0.65
    analyzed_clip: MidiClip | None = None
    analysis_config: SingleAnalysisConfig | None = None

    def __post_init__(self) -> None:
        for name in (
            "harmonic_score",
            "melodic_score",
            "voice_leading_score",
            "overlap_score",
            "register_score",
            "bass_score",
            "motif_score",
            "internal_consistency_score",
        ):
            value = getattr(self, name)
            if not isfinite(value) or not 0 <= value <= 100:
                raise ValueError(f"{name} must be between 0 and 100")
        if (
            not isfinite(self.high_confidence_threshold)
            or not 0 <= self.high_confidence_threshold <= 1
        ):
            raise ValueError("high_confidence_threshold must be between 0 and 1")
        if self.analyzed_clip is not None and not isinstance(
            self.analyzed_clip,
            MidiClip,
        ):
            raise TypeError("analyzed_clip must be a MidiClip or None")
        if self.analysis_config is not None and not isinstance(
            self.analysis_config,
            SingleAnalysisConfig,
        ):
            raise TypeError(
                "analysis_config must be a SingleAnalysisConfig or None"
            )
        suggestion_ids = tuple(item.suggestion_id for item in self.suggestions)
        if len(suggestion_ids) != len(set(suggestion_ids)):
            raise ValueError("single-clip suggestion ids must be unique")

    @property
    def key_estimate(self) -> KeyEstimate:
        """Descriptive alias for the estimated global key."""

        return self.key

    @property
    def estimated_key(self) -> KeyEstimate:
        """GUI-oriented alias for the estimated global key."""

        return self.key

    @property
    def overall_score(self) -> float:
        """Compatibility alias for internal consistency."""

        return self.internal_consistency_score

    @property
    def score(self) -> float:
        """Short compatibility alias for internal consistency."""

        return self.internal_consistency_score

    @property
    def high_confidence_suggestions(self) -> tuple[SingleClipSuggestion, ...]:
        """Return suggestions shown in the primary review list."""

        return tuple(
            suggestion
            for suggestion in self.suggestions
            if suggestion.confidence >= self.high_confidence_threshold
        )

    @property
    def secondary_suggestions(self) -> tuple[SingleClipSuggestion, ...]:
        """Return cautious suggestions intended for a collapsed section."""

        return tuple(
            suggestion
            for suggestion in self.suggestions
            if suggestion.confidence < self.high_confidence_threshold
        )

    @property
    def default_enabled_suggestion_ids(self) -> frozenset[str]:
        """Return the conservative default selection for repair."""

        return frozenset(
            suggestion.suggestion_id
            for suggestion in self.high_confidence_suggestions
        )

    @property
    def component_scores(self) -> dict[str, float]:
        """Return display-ready component scores in stable category order."""

        return {
            "harmonic": self.harmonic_score,
            "melodic": self.melodic_score,
            "voice_leading": self.voice_leading_score,
            "overlap": self.overlap_score,
            "register": self.register_score,
            "bass": self.bass_score,
            "motif": self.motif_score,
        }
