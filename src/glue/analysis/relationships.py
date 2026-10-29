"""Conservative performance-relative timing and articulation evidence.

These estimates use only the supplied performance, never a score/reference.
Rubato, pedal tails and intentional variations remain ambiguous.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import pairwise
from statistics import median

from glue.models import MidiClip

from .voices import voice_paths


@dataclass(frozen=True)
class Relationship:
    note_id: int
    field: str
    values: tuple[int, ...]
    confidence: float
    reason: str
    deviation: float


@lru_cache(maxsize=256)
def performance_relations(clip: MidiClip) -> tuple[Relationship, ...]:
    result = []
    ppq = clip.ticks_per_beat
    for line in voice_paths(clip):
        for i in range(1, len(line) - 1):
            previous, note, following = line[i - 1:i + 2]
            nearby = line[max(0, i - 5):i + 6]
            pairs = [(a, b) for a, b in pairwise(nearby)
                     if a.id != note.id and b.id != note.id and b.onset_ticks > a.onset_ticks]
            gaps = [b.onset_ticks - a.onset_ticks for a, b in pairs]
            if len(gaps) < 3:
                continue
            pulse = median(gaps)
            incoming = note.onset_ticks - previous.onset_ticks
            outgoing = following.onset_ticks - note.onset_ticks
            stable = sum(abs(g - pulse) <= pulse * .25 for g in gaps) / len(gaps)
            # A compensating short/long IOI pair amid a stable performed pulse,
            # not an absolute MIDI-grid deviation. Keep small expressive offsets.
            if (pulse >= ppq / 8 and stable >= .75 and incoming > 0 and outgoing > 0
                    and (incoming - pulse) * (outgoing - pulse) < 0
                    and abs(incoming + outgoing - 2 * pulse) < pulse * .25
                    and abs(incoming - outgoing) > max(ppq / 8, pulse * .65)):
                center = (previous.onset_ticks + following.onset_ticks) / 2
                values = {round(center), round(previous.onset_ticks + pulse),
                          round(following.onset_ticks - pulse)}
                # Preserve the performed offset for supported subdivision-sized
                # corrections. Nearby expressive estimates precede these options.
                for fraction in (1 / 8, 1 / 4, 1 / 2):
                    step = ppq * fraction
                    value = note.onset_ticks + round(step) * (1 if center > note.onset_ticks else -1)
                    if step == int(step) and abs(value - center) < pulse * .2:
                        values.add(value)
                ordered = tuple(sorted((v for v in values if previous.onset_ticks < v < following.onset_ticks
                                        and abs(v - note.onset_ticks) > ppq / 16),
                                       key=lambda v: (abs(v - center), v)))[:5]
                if ordered:
                    result.append(Relationship(note.id, "onset_ticks", ordered, stable,
                        "expressive same-voice compensating onset intervals",
                        min(1, abs(incoming - outgoing) / (2 * pulse))))
            ratios = [a.duration_ticks / (b.onset_ticks - a.onset_ticks) for a, b in pairs]
            typical = median(ratios)
            consensus = sum(abs(r - typical) < max(.15, typical * .25) for r in ratios) / len(ratios)
            expected = typical * outgoing
            if (consensus >= .75 and 0 < typical < 1.5 and outgoing > ppq / 8
                    and (note.duration_ticks > expected * 1.8
                         and note.duration_ticks > max(previous.duration_ticks, following.duration_ticks) * 1.6
                         or note.duration_ticks < expected * .4
                         and note.duration_ticks < min(previous.duration_ticks, following.duration_ticks) * .7)):
                values = {round(expected), outgoing, previous.duration_ticks, following.duration_ticks}
                # Related articulation ratios, not blind normalization. Final
                # permission and source-relative movement limits still apply.
                for factor in (.5, 2):
                    value = round(note.duration_ticks * factor)
                    if abs(value - expected) < expected * .25:
                        values.add(value)
                for fraction in (1 / 8, 1 / 4, 1 / 2):
                    step = ppq * fraction
                    value = note.duration_ticks + round(step) * (1 if expected > note.duration_ticks else -1)
                    if step == int(step) and abs(value - expected) < expected * .3:
                        values.add(value)
                ordered = tuple(sorted((v for v in values if v > 0 and abs(v - note.duration_ticks) > ppq / 16),
                                       key=lambda v: (abs(v - expected), v)))[:6]
                if ordered:
                    result.append(Relationship(note.id, "duration_ticks", ordered, consensus,
                        "expressive same-voice articulation ratio",
                        min(1, abs(note.duration_ticks - expected) / max(ppq / 8, expected))))
    return tuple(result)
