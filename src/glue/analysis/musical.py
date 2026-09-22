"""Phrase evidence and sequence harmony for deterministic musical repair.

Voice identity uses track/channel, then pitch order inside chords. These are
heuristics: a dense piano track does not uniquely identify independent voices.
All times are quarter-note beats; no audio or learned models are involved.
"""

from __future__ import annotations

from bisect import bisect_right
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from functools import lru_cache
from itertools import groupby, pairwise
from math import ceil, exp

from glue.models import MidiClip, MidiNote

from .key import estimate_key
from .results import PITCH_CLASS_NAMES, KeyEstimate

CHORDS = (
    ("major", (0, 4, 7)),
    ("minor", (0, 3, 7)),
    ("diminished", (0, 3, 6)),
    ("dominant seventh", (0, 4, 7, 10)),
    ("major seventh", (0, 4, 7, 11)),
    ("minor seventh", (0, 3, 7, 10)),
    ("suspended fourth", (0, 5, 7)),
    ("suspended second", (0, 2, 7)),
)

_COMPLETE_CHORDS = frozenset(
    frozenset((root + interval) % 12 for interval in intervals)
    for root in range(12)
    for _, intervals in CHORDS
)


@lru_cache(maxsize=192)
def joint_chord_spans(clips: tuple[MidiClip, ...]) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Exact sustained chord evidence spanning parts, without global-key veto.

    This conservative sweep complements each part's sequence model. Complete
    seventh/suspended voicings must not become semitone-clash repair targets
    simply because their chord tones arrived from two different MIDI files.
    """
    events = sorted(
        (tick / c.ticks_per_beat, n.pitch % 12, delta)
        for c in clips
        for n in c.notes
        if not n.is_percussion and n.duration_ticks > 0
        for tick, delta in ((n.onset_ticks, 1), (n.end_ticks, -1))
    )
    groups = [(beat, tuple(group)) for beat, group in groupby(events, key=lambda e: e[0])]
    active: Counter[int] = Counter()
    spans = []
    for (start, changes), (end, _) in pairwise(groups):
        for _, pc, delta in changes:
            active[pc] += delta
        pcs = frozenset(pc for pc, count in active.items() if count > 0)
        if end - start >= 0.25 and pcs in _COMPLETE_CHORDS:
            spans.append((start, end))
    return tuple(s for s, _ in spans), tuple(e for _, e in spans)


def supported_joint_overlap(
    a: MidiNote,
    b: MidiNote,
    ppq_a: int,
    ppq_b: int,
    spans: tuple[tuple[float, ...], tuple[float, ...]],
) -> bool:
    start = max(a.onset_ticks / ppq_a, b.onset_ticks / ppq_b)
    end = min(a.end_ticks / ppq_a, b.end_ticks / ppq_b)
    index = bisect_right(spans[0], start) - 1
    return end > start and index >= 0 and spans[1][index] >= end


@dataclass(frozen=True)
class Harmony:
    root: int
    quality: str
    pitches: tuple[int, ...]
    bass: int | None
    fit: float

    @property
    def label(self) -> str:
        inversion = (
            f"/{PITCH_CLASS_NAMES[self.bass]}"
            if self.bass in self.pitches and self.bass != self.root
            else ""
        )
        return f"{PITCH_CLASS_NAMES[self.root]} {self.quality}{inversion}"


@dataclass(frozen=True)
class HarmonyFrame:
    start: float
    end: float
    harmony: Harmony
    confidence: float
    alternatives: tuple[Harmony, ...]
    tonicization: bool = False


@dataclass(frozen=True)
class NoteContext:
    note_id: int
    metric_strength: float
    function: str
    confidence: float
    tension: float
    resolution_note: int | None
    phrase: int

    @property
    def protected(self) -> bool:
        return self.function in {
            "passing tone",
            "neighbor tone",
            "suspension",
            "anticipation",
            "repeated chromatic variation",
        }


@dataclass(frozen=True)
class Motif:
    first: tuple[int, ...]
    repeated: tuple[int, ...]
    pitch_variations: tuple[int, ...]
    rhythmic_match: bool


@dataclass(frozen=True)
class MusicalAnalysis:
    frames: tuple[HarmonyFrame, ...]
    notes: tuple[NoteContext, ...]
    phrase_boundaries: tuple[float, ...]
    motifs: tuple[Motif, ...]
    contour: tuple[tuple[int, ...], ...]
    syncopation: float
    density: float
    voice_leading: float
    parallel_motion: float
    bass_motion: float
    collisions: tuple[tuple[int, int], ...]
    rhythmic_motifs: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...] = ()
    overlaps: tuple[tuple[int, int, float], ...] = ()
    legato_gaps: tuple[tuple[int, int], ...] = ()


def metric_strength(clip: MidiClip, tick: int) -> float:
    """Meter-aware bar/beat/subdivision salience, including meter resets."""
    numerator, denominator = clip.time_signature_at(tick)
    reset = max((s.tick for s in clip.time_signature_changes if s.tick <= tick), default=0)
    beat = (tick - reset) / clip.ticks_per_beat
    unit = 4 / denominator
    bar = numerator * unit
    phase = beat % bar
    if min(phase, bar - phase) < 1e-7:
        return 1.0
    pulse = 3 * unit if numerator > 3 and numerator % 3 == 0 else unit
    if abs(phase / pulse - round(phase / pulse)) < 1e-7:
        return 0.7
    if abs(phase / (unit / 2) - round(phase / (unit / 2))) < 1e-7:
        return 0.35
    return 0.2


def voices(clip: MidiClip) -> tuple[tuple[MidiNote, ...], ...]:
    grouped: dict[tuple[int, int], list[MidiNote]] = defaultdict(list)
    for note in clip.notes:
        if not note.is_percussion and note.duration_ticks > 0:
            grouped[note.track, note.channel].append(note)
    return tuple(
        tuple(sorted(v, key=lambda n: (n.onset_ticks, n.pitch, n.id)))
        for _, v in sorted(grouped.items())
    )


def _frame_candidates(
    clip: MidiClip, start: float, end: float, key: KeyEstimate
) -> tuple[Harmony, ...]:
    notes = [
        n
        for n in clip.notes
        if not n.is_percussion
        and n.onset_ticks / clip.ticks_per_beat < end
        and n.end_ticks / clip.ticks_per_beat > start
    ]
    histogram = [0.0] * 12
    for n in notes:
        overlap = min(end, n.end_ticks / clip.ticks_per_beat) - max(
            start, n.onset_ticks / clip.ticks_per_beat
        )
        histogram[n.pitch % 12] += overlap * (1 + 0.5 * metric_strength(clip, n.onset_ticks))
    total = sum(histogram)
    bass = min((n.pitch for n in notes), default=-1) % 12 if notes else None
    scale = (
        {
            (key.tonic_pc + i) % 12
            for i in ((0, 2, 4, 5, 7, 9, 11) if key.mode == "major" else (0, 2, 3, 5, 7, 8, 10))
        }
        if key.tonic_pc is not None
        else set(range(12))
    )
    ranked = []
    for root in range(12):
        for quality, intervals in CHORDS:
            pcs = tuple((root + interval) % 12 for interval in intervals)
            coverage = sum(histogram[pc] for pc in pcs) / max(total, 1e-9)
            completeness = sum(histogram[pc] > 0 for pc in pcs) / len(pcs)
            fit = (
                (
                    3.5 * coverage
                    + completeness
                    + 0.25 * (bass == root)
                    + 0.15 * (bass in pcs)
                    + 0.15 * key.confidence * sum(pc in scale for pc in pcs) / len(pcs)
                )
                if total
                else 0.0
            )
            ranked.append(Harmony(root, quality, pcs, bass, fit))
    return tuple(sorted(ranked, key=lambda c: (-c.fit, c.root, c.quality))[:8])


@lru_cache(maxsize=4096)
def _voice_distance(left: tuple[int, ...], right: tuple[int, ...]) -> float:
    return sum(min(min((a - b) % 12, (b - a) % 12) for b in right) for a in left) / len(left)


def _transition(left: Harmony, right: Harmony) -> float:
    if left.root == right.root and left.quality == right.quality:
        return 0.16
    distance = _voice_distance(left.pitches, right.pitches)
    dominant_resolution = left.quality == "dominant seventh" and (left.root - right.root) % 12 == 7
    return 0.32 * dominant_resolution - 0.035 * distance


@lru_cache(maxsize=192)
def infer_harmony(clip: MidiClip) -> tuple[HarmonyFrame, ...]:
    """Viterbi path with forward/backward confidence over eight candidates/frame.

    Long clips coarsen the frame size to bound the sequence to 128 frames.
    Secondary dominants need actual seventh-chord evidence plus resolution.
    """
    length = float(clip.duration_quarter_notes)
    if length <= 0:
        return ()
    step = max(1.0, ceil(length / 128))
    spans = [(i * step, min(length, (i + 1) * step)) for i in range(ceil(length / step))]
    key = estimate_key(clip)  # Once per full clip, not once per harmonic frame.
    candidates = [_frame_candidates(clip, *span, key) for span in spans]
    forward = [[c.fit for c in candidates[0]]]
    parents: list[list[int]] = [[0] * len(candidates[0])]
    for previous, current in pairwise(candidates):
        values, pointers = [], []
        for c in current:
            scores = [forward[-1][j] + _transition(p, c) for j, p in enumerate(previous)]
            index = max(range(len(scores)), key=lambda j: scores[j])
            values.append(scores[index] + c.fit)
            pointers.append(index)
        forward.append(values)
        parents.append(pointers)
    backward = [[0.0] * len(frame) for frame in candidates]
    for i in range(len(candidates) - 2, -1, -1):
        for j, c in enumerate(candidates[i]):
            backward[i][j] = max(
                n.fit + _transition(c, n) + backward[i + 1][k]
                for k, n in enumerate(candidates[i + 1])
            )
    index = max(range(len(forward[-1])), key=lambda j: forward[-1][j])
    path = [index]
    for i in range(len(candidates) - 1, 0, -1):
        index = parents[i][index]
        path.append(index)
    path.reverse()
    frames = []
    for i, (start, end) in enumerate(spans):
        chosen = candidates[i][path[i]]
        scores = [forward[i][j] + backward[i][j] for j in range(len(candidates[i]))]
        weights = [exp(3 * (score - max(scores))) for score in scores]
        confidence = weights[path[i]] / sum(weights)
        next_chord = candidates[i + 1][path[i + 1]] if i + 1 < len(path) else chosen
        tonicization = (
            chosen.quality == "dominant seventh"
            and (chosen.root - next_chord.root) % 12 == 7
            and chosen.fit > 4
        )
        frames.append(HarmonyFrame(start, end, chosen, confidence, candidates[i], tonicization))
    return tuple(frames)


def harmony_at(frames: tuple[HarmonyFrame, ...], beat: float) -> HarmonyFrame | None:
    return next((f for f in frames if f.start <= beat < f.end), frames[-1] if frames else None)


def _motifs(clip: MidiClip) -> tuple[Motif, ...]:
    found = []
    for voice in voices(clip):
        # Bounded non-overlapping phrases of four attacks; transposed variants
        # are identified through the median pitch displacement.
        for offset in range(0, min(len(voice), 128) - 7, 4):
            left, right = voice[offset : offset + 4], voice[offset + 4 : offset + 8]
            rhythm = tuple(n.onset_ticks - left[0].onset_ticks for n in left) == tuple(
                n.onset_ticks - right[0].onset_ticks for n in right
            )
            if not rhythm:
                continue
            deltas = sorted(b.pitch - a.pitch for a, b in zip(left, right, strict=True))
            shift = deltas[1]
            variations = tuple(
                b.id for a, b in zip(left, right, strict=True) if b.pitch - a.pitch != shift
            )
            if len(variations) <= 2:
                found.append(
                    Motif(tuple(n.id for n in left), tuple(n.id for n in right), variations, True)
                )
    return tuple(found)


@lru_cache(maxsize=192)
def analyze_musical(clip: MidiClip) -> MusicalAnalysis:
    frames = infer_harmony(clip)
    boundaries = {0.0}
    for previous, following in pairwise(frames):
        if (
            previous.tonicization
            and following.confidence > 0.25
            and metric_strength(clip, round(following.start * clip.ticks_per_beat)) >= 0.7
        ):
            boundaries.add(following.start)
    contexts = []
    contours = []
    motion, parallels, bass_motion = [], [], []
    motifs = _motifs(clip)
    rhythmic_motifs = []
    repeated_ids = {
        i for m in motifs for i in (*m.first, *m.repeated) if i not in m.pitch_variations
    }
    for voice in voices(clip):
        for offset in range(0, min(len(voice), 128) - 7, 4):
            left, right = voice[offset : offset + 4], voice[offset + 4 : offset + 8]
            if tuple(n.onset_ticks - left[0].onset_ticks for n in left) == tuple(
                n.onset_ticks - right[0].onset_ticks for n in right
            ):
                rhythmic_motifs.append((tuple(n.id for n in left), tuple(n.id for n in right)))
        attacks = sorted({n.onset_ticks for n in voice})
        for a, b in pairwise(attacks):
            if b - max(n.end_ticks for n in voice if n.onset_ticks == a) >= clip.ticks_per_beat:
                boundaries.add(b / clip.ticks_per_beat)
        contour = tuple(
            b.pitch - a.pitch for a, b in pairwise(voice) if b.onset_ticks > a.onset_ticks
        )
        contours.append(contour)
        groups = [
            sorted((n for n in voice if n.onset_ticks == tick), key=lambda n: n.pitch)
            for tick in attacks
        ]
        for left, right in pairwise(groups):
            bass_motion.append(abs(left[0].pitch - right[0].pitch))
            if len(left) == len(right) and len(left) > 1:
                ds = [b.pitch - a.pitch for a, b in zip(left, right, strict=True)]
                motion.extend(abs(d) for d in ds)
                parallels.extend(
                    1.0
                    for j in range(len(ds) - 1)
                    if ds[j] * ds[j + 1] > 0
                    and (left[j + 1].pitch - left[j].pitch) % 12 in (0, 7)
                    and (right[j + 1].pitch - right[j].pitch) % 12 in (0, 7)
                )
        for i, n in enumerate(voice):
            previous = voice[i - 1] if i and voice[i - 1].onset_ticks < n.onset_ticks else None
            following = next((v for v in voice[i + 1 :] if v.onset_ticks > n.onset_ticks), None)
            frame = harmony_at(frames, n.onset_ticks / clip.ticks_per_beat)
            pcs = frame.harmony.pitches if frame else ()
            strength = metric_strength(clip, n.onset_ticks)
            function = "chord tone" if n.pitch % 12 in pcs else "unresolved tension"
            confidence = frame.confidence if frame else 0.0
            resolution = None
            if (
                previous
                and following
                and n.onset_ticks - previous.end_ticks <= clip.ticks_per_beat
                and following.onset_ticks - n.end_ticks <= clip.ticks_per_beat
            ):
                before, after = n.pitch - previous.pitch, following.pitch - n.pitch
                short = n.duration_ticks <= clip.ticks_per_beat / 2
                if short and strength < 0.7 and 0 < abs(before) <= 2 and 0 < abs(after) <= 2:
                    if before * after > 0:
                        function = "passing tone"
                    elif following.pitch == previous.pitch:
                        function = "neighbor tone"
                previous_frame = harmony_at(frames, previous.onset_ticks / clip.ticks_per_beat)
                if (
                    function == "unresolved tension"
                    and before == 0
                    and after in (-1, -2)
                    and following.pitch % 12 in pcs
                    and previous_frame
                    and previous.pitch % 12 in previous_frame.harmony.pitches
                ):
                    function = "suspension"
                if strength < 0.7 and after == 0 and n.end_ticks >= following.onset_ticks:
                    function = "anticipation"
                if function in {"passing tone", "neighbor tone", "suspension", "anticipation"}:
                    confidence, resolution = 0.85, following.id
            if function == "unresolved tension" and n.id in repeated_ids:
                function, confidence = "repeated chromatic variation", 0.6
            tension = (
                strength * min(2.0, n.duration_ticks / clip.ticks_per_beat)
                if function == "unresolved tension"
                else 0.0
            )
            contexts.append(
                NoteContext(n.id, strength, function, confidence, tension, resolution, 0)
            )
    ordered = tuple(sorted(boundaries))
    onsets = {n.id: n.onset_ticks / clip.ticks_per_beat for n in clip.notes}
    contexts = [
        replace(n, phrase=sum(b <= onsets[n.note_id] for b in ordered) - 1) for n in contexts
    ]
    collisions = []
    for voice in voices(clip):
        for i, n in enumerate(voice):
            for other in voice[i + 1 :]:
                if other.onset_ticks >= n.end_ticks:
                    break
                if other.pitch == n.pitch:
                    collisions.append((n.id, other.id))
    sync = sum(c.metric_strength < 0.7 for c in contexts) / max(1, len(contexts))
    overlaps = []
    for i, note in enumerate(clip.notes):
        for other in clip.notes[i + 1 :]:
            if other.onset_ticks >= note.end_ticks:
                break
            if not note.is_percussion and not other.is_percussion:
                overlaps.append(
                    (
                        note.id,
                        other.id,
                        (min(note.end_ticks, other.end_ticks) - other.onset_ticks)
                        / clip.ticks_per_beat,
                    )
                )
    legato_gaps = []
    context_by_id = {n.note_id: n for n in contexts}
    for voice in voices(clip):
        if len(voice) < 4 or len({n.onset_ticks for n in voice}) != len(voice):
            continue
        gaps = [b.onset_ticks - a.end_ticks for a, b in pairwise(voice)]
        # Only an isolated short gap in an otherwise joined line: repeated
        # staccato articulation is not evidence of a technical legato mistake.
        if sum(gap == 0 for gap in gaps) < len(gaps) * 0.6:
            continue
        for a, b in pairwise(voice):
            gap = b.onset_ticks - a.end_ticks
            if (
                0 < gap <= clip.ticks_per_beat / 4
                and a.duration_ticks >= clip.ticks_per_beat / 2
                and abs(a.pitch - b.pitch) <= 2
                and context_by_id[a.id].function == "chord tone"
            ):
                legato_gaps.append((a.id, gap))
    return MusicalAnalysis(
        frames,
        tuple(sorted(contexts, key=lambda n: n.note_id)),
        ordered,
        motifs,
        tuple(contours),
        sync,
        len(contexts) / max(1.0, float(clip.duration_quarter_notes)),
        sum(motion) / max(1, len(motion)),
        float(len(parallels)),
        sum(bass_motion) / max(1, len(bass_motion)),
        tuple(collisions),
        tuple(rhythmic_motifs),
        tuple(overlaps),
        tuple(legato_gaps),
    )
