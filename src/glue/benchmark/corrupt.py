"""Seeded error injection into immutable copies, with exact field/event ledgers.

These are operational error hypotheses, not objective judgments about style.
Inapplicable scenarios are skipped, never silently replaced by another error.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass, replace
from math import isfinite

from glue.models import MidiClip, MidiNote

FIELDS = ("pitch", "onset_ticks", "duration_ticks")
KINDS = (
    "accidental", "wrong_diatonic", "wrong_chord_tone", "octave", "bass_pitch", "motif",
    "early", "late", "attack_collision", "call_response", "groove",
    "sustain", "short", "harmony_overlap", "bass_lead_collision",
    "pitch_timing", "pitch_duration", "timing_duration", "coordinated",
)


@dataclass(frozen=True)
class Change:
    slot: int
    note_id: int
    before: MidiNote
    after: MidiNote

    @property
    def fields(self) -> tuple[str, ...]:
        return tuple(f for f in FIELDS if getattr(self.before, f) != getattr(self.after, f))

    def record(self) -> dict:
        return {**asdict(self), "fields": self.fields}


@dataclass(frozen=True)
class Corruption:
    clips: tuple[MidiClip, ...]
    changes: tuple[Change, ...]
    kind: str
    seed: int
    severity: float
    requested_notes: int
    skipped: str | None = None


def _scale(clip: MidiClip) -> frozenset[int]:
    """Independent reference-only major/minor histogram proxy, not GLUE analysis."""
    scales = [frozenset((root + p) % 12 for p in shape) for root in range(12)
              for shape in ((0, 2, 4, 5, 7, 9, 11), (0, 2, 3, 5, 7, 8, 10))]
    return max(scales, key=lambda pcs: sum(n.duration_ticks for n in clip.notes
                                         if n.pitch % 12 in pcs and not n.is_percussion))


def _motif_ids(clip: MidiClip) -> set[int]:
    result = set()
    for track, channel in sorted({(n.track, n.channel) for n in clip.notes}):
        notes = [n for n in clip.notes if (n.track, n.channel) == (track, channel)]
        for i in range(len(notes) - 3):
            a = notes[i:i + 4]
            signature = [(n.pitch, n.onset_ticks - a[0].onset_ticks, n.duration_ticks) for n in a]
            for j in range(i + 4, len(notes) - 3):
                b = notes[j:j + 4]
                if signature == [(n.pitch, n.onset_ticks - b[0].onset_ticks,
                                  n.duration_ticks) for n in b]:
                    result.update(n.id for n in b)
    return result


def _safe(clip: MidiClip, note: MidiNote) -> bool:
    end = next((t.length_ticks for t in clip.tracks if t.index == note.track), clip.length_ticks)
    if note.end_ticks > end or note.duration_ticks <= 0:
        return False
    # Do not introduce ambiguous same-channel/pitch pairing. Other-pitch overlap
    # and simultaneous attacks are intentional corruption scenarios.
    return not any(n.id != note.id and (n.track, n.channel, n.pitch) ==
                   (note.track, note.channel, note.pitch) and
                   max(n.onset_ticks, note.onset_ticks) < min(n.end_ticks, note.end_ticks)
                   for n in clip.notes)


def _alternative(
    clips: tuple[MidiClip, ...], slot: int, n: MidiNote, kind: str,
    severity: float, rng: random.Random,
) -> MidiNote | None:
    clip = clips[slot]
    beat = clip.ticks_per_beat
    step = max(1, round(beat * 0.125 * severity))
    sign = rng.choice((-1, 1))
    delta = max(1, round(severity))
    pitch = n.pitch
    onset, duration = n.onset_ticks, n.duration_ticks
    if kind in {"accidental", "bass_pitch", "motif", "pitch_timing", "pitch_duration",
                "coordinated"}:
        if kind == "bass_pitch" and n.pitch != min(x.pitch for x in clip.notes
                                                 if not x.is_percussion):
            return None
        if kind == "motif" and n.id not in _motif_ids(clip):
            return None
        pitch += sign  # An accidental remains exactly one semitone at any severity.
    elif kind == "octave":
        pitch += sign * 12 * min(2, delta)
    elif kind in {"wrong_diatonic", "wrong_chord_tone"}:
        pcs = _scale(clip) if kind == "wrong_diatonic" else frozenset(
            x.pitch % 12 for c in clips for x in c.notes
            if x.onset_ticks / c.ticks_per_beat <= onset / beat < x.end_ticks / c.ticks_per_beat
            and not x.is_percussion
        )
        if kind == "wrong_chord_tone" and len(pcs) < 3:
            return None
        targets = sorted((p for p in range(max(0, pitch - 12), min(128, pitch + 13))
                          if p % 12 in pcs and p % 12 != pitch % 12
                          and _safe(clip, replace(n, pitch=p))),
                         key=lambda p: (abs(p - pitch), sign * p))
        if not targets:
            return None
        pitch = targets[min(delta - 1, len(targets) - 1)]
    if kind in {"early", "late", "groove", "pitch_timing", "timing_duration", "coordinated"}:
        onset += step * (-1 if kind == "early" else 1 if kind == "late" else sign)
    if kind in {"attack_collision", "call_response"}:
        others = [(c, x) for index, c in enumerate(clips) for x in c.notes
                  if (index != slot or x.id != n.id) and not x.is_percussion
                  and (kind != "call_response" or index != slot)]
        targets = [(abs(x.onset_ticks / c.ticks_per_beat - onset / beat),
                    round(x.onset_ticks / c.ticks_per_beat * beat)) for c, x in others
                   if x.onset_ticks / c.ticks_per_beat != onset / beat]
        targets = [t for t in targets if t[0] <= severity]
        if not targets:
            return None
        onset = min(targets)[1]
    if kind in {"sustain", "pitch_duration", "timing_duration", "coordinated"}:
        duration += max(1, round(beat * 0.5 * severity))
    elif kind == "short":
        duration = max(1, round(duration / (1 + severity)))
    elif kind in {"harmony_overlap", "bass_lead_collision"}:
        others = [(c, x) for c in clips for x in c.notes if not x.is_percussion
                  and x.onset_ticks / c.ticks_per_beat >= n.end_ticks / beat
                  and x.pitch % 12 != n.pitch % 12
                  and (kind != "bass_lead_collision" or abs(x.pitch - n.pitch) >= 12)]
        if kind == "harmony_overlap":
            def harmony_at(beat_position: float) -> frozenset[int]:
                return frozenset(x.pitch % 12 for c in clips for x in c.notes
                                 if not x.is_percussion and x.onset_ticks / c.ticks_per_beat
                                 <= beat_position < x.end_ticks / c.ticks_per_beat)

            original_harmony = harmony_at(n.onset_ticks / beat)
            # Require an observed three-tone sonority change, not merely the
            # next melody attack. Silent gaps retain the prior reference chord.
            others = [(c, x) for c, x in others
                      if len(original_harmony) >= 3
                      and len(harmony_at(x.onset_ticks / c.ticks_per_beat)) >= 3
                      and harmony_at(x.onset_ticks / c.ticks_per_beat) != original_harmony]
        if not others:
            return None
        target = min(x.onset_ticks / c.ticks_per_beat for c, x in others)
        if target - n.end_ticks / beat > severity:
            return None
        duration = round(target * beat) - onset + step
    if not 0 <= pitch <= 127 or onset < 0:
        return None
    return replace(n, pitch=pitch, onset_ticks=onset, duration_ticks=duration)


def corrupt(
    clips: tuple[MidiClip, ...], kind: str, *, seed: int = 0,
    severity: float = 1, count: int = 1,
) -> Corruption:
    if not clips or len(clips) > 2:
        raise ValueError("Expected a single clip or pair")
    if kind not in (*KINDS, "clean"):
        raise ValueError(f"Unknown corruption: {kind}")
    if not isfinite(severity) or not 0 < severity <= 4 or type(count) is not int or count < 1:
        raise ValueError("Severity must be in (0, 4]; count must be a positive integer")
    if kind == "clean":
        return Corruption(clips, (), kind, seed, severity, 0)
    rng = random.Random(seed)
    pool = [(i, n) for i, clip in enumerate(clips) for n in clip.notes
            if not n.is_percussion and n.duration_ticks > 0]
    rng.shuffle(pool)
    requested = max(2, count) if kind == "coordinated" else count
    revised = list(clips)
    changes = []
    anchor = None
    for slot, note in pool:
        position = note.onset_ticks / clips[slot].ticks_per_beat
        if kind == "coordinated" and anchor is not None and abs(position - anchor) > 4:
            continue
        target = _alternative(clips, slot, note, kind, severity, rng)
        if target is None or target == note or not _safe(revised[slot], target):
            continue
        revised[slot] = revised[slot].with_notes(target if n.id == note.id else n
                                               for n in revised[slot].notes)
        changes.append(Change(slot, note.id, note, target))
        anchor = position if anchor is None else anchor
        if len(changes) == requested:
            return Corruption(tuple(revised), tuple(changes), kind, seed, severity, requested)
    return Corruption(clips, (), kind, seed, severity, requested,
                      f"Not applicable: found {len(changes)} safe eligible notes; need {requested}.")
