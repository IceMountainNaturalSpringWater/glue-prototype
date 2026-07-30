"""Deterministic, lightweight preservation-balance suggestions.

This module deliberately consumes an existing :class:`PairAnalysis`.  It does
not run compatibility analysis or repair search, making it safe for a GUI to
reuse the analysis cache when previewing a suggested A/B balance.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from math import isfinite
from numbers import Real
from typing import Literal

from glue.analysis import (
    KeyEstimate,
    PairAnalysis,
    duration_weighted_histogram,
    scale_pitch_classes,
)
from glue.models import MidiClip, MidiNote

DEFAULT_SUGGESTED_PRESERVATION = 50
HIGH_SUGGESTED_PRESERVATION = 95
LOW_SUGGESTED_PRESERVATION = 65
CONFIDENT_SUGGESTION_THRESHOLD = 0.60

_EPSILON = 1e-9
_DIRECTION_DEADBAND = 0.08
_FULL_DIRECTION_MARGIN = 0.45


@dataclass(frozen=True, slots=True)
class BalanceSuggestion:
    """One bounded, qualified preservation suggestion for Clip A and B."""

    preservation_a: int
    preservation_b: int
    confidence: float
    explanation: str

    def __post_init__(self) -> None:
        for name in ("preservation_a", "preservation_b"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
            if not 0 <= value < 100:
                raise ValueError(
                    f"{name} must be between 0 and 99; suggestions never hard-lock"
                )
        if isinstance(self.confidence, bool) or not isinstance(
            self.confidence,
            Real,
        ):
            raise TypeError("confidence must be a number between 0 and 1")
        normalized_confidence = float(self.confidence)
        if not isfinite(normalized_confidence):
            raise ValueError("confidence must be finite")
        if not 0.0 <= normalized_confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if not isinstance(self.explanation, str):
            raise TypeError("explanation must be a string")
        normalized_explanation = self.explanation.strip()
        if not normalized_explanation:
            raise ValueError("explanation must not be empty")
        object.__setattr__(self, "confidence", normalized_confidence)
        object.__setattr__(self, "explanation", normalized_explanation)

    @property
    def is_confident(self) -> bool:
        """Return whether the evidence supports a directional suggestion."""

        return (
            self.confidence >= CONFIDENT_SUGGESTION_THRESHOLD
            and self.preservation_a != self.preservation_b
        )

    @property
    def confidence_label(self) -> Literal["confident", "low confidence"]:
        """Return a compact signal suitable for GUI preview text."""

        return "confident" if self.is_confident else "low confidence"


@dataclass(frozen=True, slots=True)
class _ClipEvidence:
    key_stability: float
    scale_fit: float
    local_harmony: float
    chordal_role: float
    motif_strength: float
    edit_effort: float

    @property
    def preservation_score(self) -> float:
        """Combine qualified evidence; this is not a musical-quality score."""

        return _clamp_unit(
            0.22 * self.key_stability
            + 0.28 * self.scale_fit
            + 0.25 * self.local_harmony
            + 0.10 * self.chordal_role
            + 0.07 * self.motif_strength
            + 0.08 * self.edit_effort
        )


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, value))


def _pitched_notes(clip: MidiClip) -> tuple[MidiNote, ...]:
    return tuple(
        note
        for note in clip.notes
        if not note.is_percussion and note.duration_ticks > 0
    )


def _key_stability(
    estimate: KeyEstimate,
    combined: KeyEstimate,
) -> float:
    if estimate.top is None or combined.top is None:
        return 0.0
    combined_scale = scale_pitch_classes(combined.top)
    if (
        estimate.top.tonic_pc == combined.top.tonic_pc
        and estimate.top.mode == combined.top.mode
    ):
        agreement = 1.0
    elif estimate.top.tonic_pc == combined.top.tonic_pc:
        agreement = 0.65
    elif estimate.top.tonic_pc in combined_scale:
        agreement = 0.35
    else:
        agreement = 0.0
    return _clamp_unit(0.65 * estimate.confidence + 0.35 * agreement)


def _scale_evidence(
    clip: MidiClip,
    scale: frozenset[int],
) -> tuple[float, float]:
    """Return duration-weighted scale fit and cheap pitch-edit effort."""

    histogram = duration_weighted_histogram((clip,))
    total = sum(histogram)
    if total <= _EPSILON:
        return 0.0, 0.0
    in_scale = sum(histogram[pitch_class] for pitch_class in scale)
    scale_fit = _clamp_unit(in_scale / total)
    outside_weight = total - in_scale
    if outside_weight <= _EPSILON:
        pitch_effort = 1.0
    else:
        displacement = sum(
            weight
            * min(
                min(
                    (pitch_class - target) % 12,
                    (target - pitch_class) % 12,
                )
                for target in scale
            )
            for pitch_class, weight in enumerate(histogram)
            if pitch_class not in scale and weight > _EPSILON
        )
        mean_displacement = displacement / outside_weight
        outside_fraction = outside_weight / total
        # A small number of nearby chromatic pitches is comparatively cheap to
        # adjust; widespread or more distant material increases preservation
        # effort.  Major/natural-minor scale gaps keep this deliberately modest.
        pitch_effort = 1.0 - outside_fraction * (
            1.0 - min(1.0, mean_displacement / 6.0)
        )
    return scale_fit, _clamp_unit(pitch_effort)


def _local_harmony_evidence(
    analysis: PairAnalysis,
    *,
    use_clip_a: bool,
) -> float:
    total_activity = sum(window.activity_weight for window in analysis.windows)
    if total_activity <= _EPSILON:
        return 0.0
    weighted = 0.0
    for window in analysis.windows:
        candidates = (
            window.local_harmony_a
            if use_clip_a
            else window.local_harmony_b
        )
        if not candidates:
            continue
        candidate = candidates[0]
        quality = (
            0.45 * candidate.coverage
            + 0.40 * candidate.completeness
            + 0.15 * min(1.0, candidate.probability * 3.0)
        )
        weighted += window.activity_weight * quality
    return _clamp_unit(weighted / total_activity)


def _structural_evidence(
    clip: MidiClip,
    notes: tuple[MidiNote, ...],
    pitch_effort: float,
) -> tuple[float, float, float]:
    if not notes:
        return 0.0, 0.0, 0.0

    distinct_onsets = len({note.onset_ticks for note in notes})
    chordal_role = _clamp_unit(1.0 - distinct_onsets / len(notes))

    signatures = Counter(
        (
            note.track,
            note.channel,
            note.pitch,
            Fraction(note.duration_ticks, clip.ticks_per_beat),
        )
        for note in notes
    )
    motif_strength = _clamp_unit(
        sum(count - 1 for count in signatures.values()) / len(notes)
    )

    active_start = min(note.onset_ticks for note in notes)
    active_end = max(note.end_ticks for note in notes)
    active_beats = max(
        (active_end - active_start) / clip.ticks_per_beat,
        0.25,
    )
    note_density = _clamp_unit(len(notes) / (active_beats * 4.0))
    edit_effort = _clamp_unit(
        0.40 * note_density
        + 0.35 * motif_strength
        + 0.25 * pitch_effort
    )
    return chordal_role, motif_strength, edit_effort


def _clip_evidence(
    clip: MidiClip,
    estimate: KeyEstimate,
    analysis: PairAnalysis,
    *,
    use_clip_a: bool,
) -> _ClipEvidence:
    combined_top = analysis.combined_key.top
    if combined_top is None:
        raise ValueError("combined key evidence is required")
    notes = _pitched_notes(clip)
    scale_fit, pitch_effort = _scale_evidence(
        clip,
        scale_pitch_classes(combined_top),
    )
    chordal_role, motif_strength, edit_effort = _structural_evidence(
        clip,
        notes,
        pitch_effort,
    )
    return _ClipEvidence(
        key_stability=_key_stability(estimate, analysis.combined_key),
        scale_fit=scale_fit,
        local_harmony=_local_harmony_evidence(
            analysis,
            use_clip_a=use_clip_a,
        ),
        chordal_role=chordal_role,
        motif_strength=motif_strength,
        edit_effort=edit_effort,
    )


def _neutral_suggestion(confidence: float, reason: str) -> BalanceSuggestion:
    return BalanceSuggestion(
        preservation_a=DEFAULT_SUGGESTED_PRESERVATION,
        preservation_b=DEFAULT_SUGGESTED_PRESERVATION,
        confidence=min(confidence, CONFIDENT_SUGGESTION_THRESHOLD - 0.01),
        explanation=(
            f"No strong recommendation: {reason} Preservation remains "
            f"{DEFAULT_SUGGESTED_PRESERVATION}/{DEFAULT_SUGGESTED_PRESERVATION}."
        ),
    )


def _evidence_phrases(
    stronger: _ClipEvidence,
    weaker: _ClipEvidence,
) -> tuple[str, ...]:
    candidates = (
        (
            stronger.key_stability - weaker.key_stability,
            "more stable agreement with the estimated combined key",
        ),
        (
            stronger.scale_fit - weaker.scale_fit,
            "stronger duration-weighted fit to the estimated combined scale",
        ),
        (
            stronger.local_harmony - weaker.local_harmony,
            "clearer local-harmony evidence in overlapping windows",
        ),
        (
            stronger.chordal_role - weaker.chordal_role,
            "a denser chordal/context role",
        ),
        (
            stronger.motif_strength - weaker.motif_strength,
            "more repeated-note preservation evidence",
        ),
        (
            stronger.edit_effort - weaker.edit_effort,
            "higher estimated pitch-edit effort",
        ),
    )
    ranked = sorted(
        (
            (difference, index, phrase)
            for index, (difference, phrase) in enumerate(candidates)
            if difference > 0.05
        ),
        key=lambda item: (-item[0], item[1]),
    )
    return tuple(phrase for _, _, phrase in ranked[:3])


def suggest_preservation_balance(
    clip_a: MidiClip,
    clip_b: MidiClip,
    analysis: PairAnalysis,
) -> BalanceSuggestion:
    """Suggest cautious A/B preservation values from cached analysis evidence.

    The result is a deterministic heuristic about edit allocation, not a claim
    that either musical part is objectively better or at fault.  The function
    performs no compatibility analysis and generates no repair candidates.
    """

    if not isinstance(clip_a, MidiClip) or not isinstance(clip_b, MidiClip):
        raise TypeError("clip_a and clip_b must be MidiClip instances")
    if not isinstance(analysis, PairAnalysis):
        raise TypeError("analysis must be a PairAnalysis")

    overlap = sum(window.activity_weight for window in analysis.windows)
    if overlap <= _EPSILON:
        return _neutral_suggestion(
            0.0,
            "the clips have no comparable overlapping activity.",
        )
    if not _pitched_notes(clip_a) or not _pitched_notes(clip_b):
        return _neutral_suggestion(
            0.0,
            "both clips need pitched note evidence for a pitch-repair balance.",
        )
    if analysis.combined_key.top is None:
        return _neutral_suggestion(
            0.0,
            "the combined tonal evidence is unresolved.",
        )

    evidence_a = _clip_evidence(
        clip_a,
        analysis.key_a,
        analysis,
        use_clip_a=True,
    )
    evidence_b = _clip_evidence(
        clip_b,
        analysis.key_b,
        analysis,
        use_clip_a=False,
    )
    difference = evidence_a.preservation_score - evidence_b.preservation_score
    margin = abs(difference)
    direction_strength = _clamp_unit(
        (margin - _DIRECTION_DEADBAND)
        / (_FULL_DIRECTION_MARGIN - _DIRECTION_DEADBAND)
    )
    evidence_reliability = 0.35 + 0.65 * analysis.combined_key.confidence
    confidence = _clamp_unit(direction_strength * evidence_reliability)
    if confidence < CONFIDENT_SUGGESTION_THRESHOLD:
        return _neutral_suggestion(
            confidence,
            (
                "the key, scale, local-harmony, role, motif, and edit-effort "
                "evidence is too similar or ambiguous."
            ),
        )

    preserve_a_more = difference > 0.0
    stronger = evidence_a if preserve_a_more else evidence_b
    weaker = evidence_b if preserve_a_more else evidence_a
    stronger_label = "Clip A" if preserve_a_more else "Clip B"
    phrases = _evidence_phrases(stronger, weaker)
    evidence_text = (
        ", ".join(phrases)
        if phrases
        else "a stronger aggregate of the qualified preservation evidence"
    )
    preservation_a = (
        HIGH_SUGGESTED_PRESERVATION
        if preserve_a_more
        else LOW_SUGGESTED_PRESERVATION
    )
    preservation_b = (
        LOW_SUGGESTED_PRESERVATION
        if preserve_a_more
        else HIGH_SUGGESTED_PRESERVATION
    )
    return BalanceSuggestion(
        preservation_a=preservation_a,
        preservation_b=preservation_b,
        confidence=confidence,
        explanation=(
            f"Confident heuristic: {stronger_label} receives higher preservation "
            f"(A/B = {preservation_a}/{preservation_b}) because it shows "
            f"{evidence_text}. "
            "This estimates edit allocation and is not objective musical blame."
        ),
    )


__all__ = [
    "CONFIDENT_SUGGESTION_THRESHOLD",
    "DEFAULT_SUGGESTED_PRESERVATION",
    "HIGH_SUGGESTED_PRESERVATION",
    "LOW_SUGGESTED_PRESERVATION",
    "BalanceSuggestion",
    "suggest_preservation_balance",
]
