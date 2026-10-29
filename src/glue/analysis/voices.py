"""Deterministic, order-preserving note-role continuity for repair evidence.

Track/channel is not a voice when it contains chords. A bounded dynamic program
matches each attack group to preceding lines, with explicit births/deaths. This
is a heuristic, not a claim of unique voice separation in expressive piano.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from statistics import median

from glue.models import MidiClip, MidiNote


def _matching(previous: list[MidiNote], current: list[MidiNote], ppq: int,
              histories: list[list[MidiNote]]) -> tuple[tuple[int, int], ...]:
    """Order-preserving edit alignment; a 24-semitone leap can start a new voice."""
    table: dict[tuple[int, int], tuple[float, tuple]] = {(0, 0): (0.0, ())}
    for i in range(len(previous) + 1):
        for j in range(len(current) + 1):
            if i == j == 0:
                continue
            choices = []
            if i:
                cost, path = table[i - 1, j]
                choices.append((cost + 12, path))
            if j:
                cost, path = table[i, j - 1]
                choices.append((cost + 12, path))
            if i and j:
                cost, path = table[i - 1, j - 1]
                a, b = previous[i - 1], current[j - 1]
                history = histories[i - 1][-4:]
                register = median(n.pitch for n in history)
                direction = a.pitch - history[-2].pitch if len(history) > 1 else 0
                motion = b.pitch - a.pitch
                # Pedal-like tails are ambiguous, so overlap is a soft cue.
                overlap = max(0, a.end_ticks - b.onset_ticks) / ppq
                gap = max(0, b.onset_ticks - a.end_ticks) / ppq
                continuity = (abs(motion) + 0.25 * abs(b.pitch - register)
                              + min(4, overlap * 2) + min(2, gap * 0.5)
                              + (0.5 if direction * motion < 0 and abs(motion) > 4 else 0))
                choices.append((cost + continuity, path + ((i - 1, j - 1),)))
            table[i, j] = min(choices, key=lambda value: (value[0], -len(value[1]), value[1]))
    return table[len(previous), len(current)][1]


@lru_cache(maxsize=192)
def voice_paths(clip: MidiClip) -> tuple[tuple[MidiNote, ...], ...]:
    groups = defaultdict(list)
    for note in clip.notes:
        if not note.is_percussion and note.duration_ticks > 0:
            groups[note.track, note.channel].append(note)
    paths = []
    for _, notes in sorted(groups.items()):
        local: list[list[MidiNote]] = []
        attacks: list[list[MidiNote]] = []
        for note in sorted(notes, key=lambda n: (n.onset_ticks, n.pitch, n.id)):
            if not attacks or note.onset_ticks - attacks[-1][0].onset_ticks > clip.ticks_per_beat / 32:
                attacks.append([])
            attacks[-1].append(note)
        for attack in attacks:
            onset = attack[0].onset_ticks
            current = sorted(attack, key=lambda n: (n.pitch, n.id))
            active = sorted((i for i, line in enumerate(local)
                             if onset - line[-1].onset_ticks <= 4 * clip.ticks_per_beat),
                            key=lambda i: (local[i][-1].pitch, i))
            # Large clusters use pitch-rank matching instead of an unbounded DP.
            matched = (_matching([local[i][-1] for i in active], current,
                                 clip.ticks_per_beat, [local[i] for i in active])
                       if max(len(active), len(current)) <= 32 else
                       tuple(zip(range(len(active)), range(len(current)))))
            used = set()
            for a, b in matched:
                local[active[a]].append(current[b])
                used.add(b)
            local.extend([n] for i, n in enumerate(current) if i not in used)
        paths.extend(tuple(line) for line in local)
    return tuple(paths)


@dataclass(frozen=True)
class VoiceIdentity:
    note_id: int
    voice: int
    role: str
    register_low: int
    register_high: int
    register_center: float
    previous: int | None
    following: int | None
    confidence: str


@lru_cache(maxsize=192)
def voice_identities(clip: MidiClip) -> tuple[VoiceIdentity, ...]:
    lines = voice_paths(clip)
    centers = [median(n.pitch for n in line) for line in lines]
    result = []
    for index, line in enumerate(lines):
        center = centers[index]
        role = ("single" if len(lines) == 1 else "bass" if center == min(centers)
                else "upper" if center == max(centers) else "inner")
        for i, note in enumerate(line):
            result.append(VoiceIdentity(
                note.id, index, role, min(n.pitch for n in line), max(n.pitch for n in line),
                float(center), line[i - 1].id if i else None,
                line[i + 1].id if i + 1 < len(line) else None,
                "approximate" if len(line) >= 3 else "low"))
    return tuple(result)


def pitch_supported(clip: MidiClip, note: MidiNote, target: int) -> bool:
    """Do not change chord order or move a line through a nearby attack voice."""
    peers = [n for n in clip.notes if n.id != note.id and n.track == note.track
             and n.channel == note.channel
             and abs(n.onset_ticks - note.onset_ticks) <= clip.ticks_per_beat / 32]
    if any((note.pitch - n.pitch) * (target - n.pitch) < 0 for n in peers):
        return False
    for line in voice_paths(clip):
        if len(line) >= 5 and abs(target - note.pitch) > 2 and any(n.id == note.id for n in line):
            peers = sorted(n.pitch for n in line if n.id != note.id)
            low, high = peers[(len(peers) - 1) // 4], peers[3 * (len(peers) - 1) // 4]
            if (high - low <= 12 and low - 2 <= note.pitch <= high + 2
                    and not low - 2 <= target <= high + 2):
                return False  # Preserve a stable voice's robust register, including endpoints.
        for i in range(1, len(line) - 1):
            if line[i].id != note.id:
                continue
            a, b = line[i - 1].pitch, line[i + 1].pitch
            if (abs(a - b) <= 7 and min(a, b) < note.pitch < max(a, b)
                    and not min(a, b) <= target <= max(a, b)):
                return False  # Do not turn a coherent line into a register excursion.
    return octave_supported(clip, note, target)


@lru_cache(maxsize=192)
def voice_ornaments(clip: MidiClip) -> frozenset[int]:
    """Protect recurring short neighbor figures missed by flattened polyphony.

    Repetition supplies evidence of intent. A single isolated neighbor-like
    discrepancy stays ambiguous and is not automatically protected here.
    """
    protected = set()
    for line in voice_paths(clip):
        figures = defaultdict(list)
        for a, n, b in zip(line, line[1:], line[2:]):
            if (a.pitch == b.pitch and 0 < abs(n.pitch - a.pitch) <= 2
                    and n.duration_ticks <= clip.ticks_per_beat / 2):
                figures[a.pitch, n.pitch].append(n.id)
        protected.update(ident for ids in figures.values() if len(ids) >= 2 for ident in ids)
    return frozenset(protected)


def octave_supported(clip: MidiClip, note: MidiNote, target: int) -> bool:
    """Octave movement requires an isolated register excursion, not pitch-class fit.

    Crossing another simultaneous chord voice is a conservative rejection even
    at 0% preservation. This can miss a genuine already-crossed octave error;
    that limitation is preferable to silently revoicing coherent chords.
    """
    if abs(target - note.pitch) < 12:
        return True
    peers = [n for n in clip.notes if n.id != note.id and n.track == note.track
             and n.channel == note.channel and n.onset_ticks == note.onset_ticks]
    if any((note.pitch - n.pitch) * (target - n.pitch) <= 0 for n in peers):
        return False
    if octave_confidence(clip, note, target) >= 0.8:
        return True
    for line in voice_paths(clip):
        for index, n in enumerate(line):
            if n.id != note.id:
                continue
            if _motif_octave(line, index, target):
                return True
            # A polyphonic/arpeggiated stream can look like an isolated leap
            # after approximate assignment. Require motif corroboration there.
            neighborhood = line[max(0, index - 1):index + 2]
            if any(a.id != b.id and a.track == b.track and a.channel == b.channel
                   and min(a.end_ticks, b.end_ticks) - max(a.onset_ticks, b.onset_ticks)
                   > clip.ticks_per_beat / 16
                   for a in neighborhood for b in clip.notes):
                return False
            if not 0 < index < len(line) - 1:
                return False
            a, b = line[index - 1].pitch, line[index + 1].pitch
            if abs(a - b) > 7:
                return False
            return ((n.pitch > max(a, b) + 7 or n.pitch < min(a, b) - 7)
                    and abs(target - a) + abs(target - b)
                    <= abs(n.pitch - a) + abs(n.pitch - b) - 12)
    return False


def octave_confidence(clip: MidiClip, note: MidiNote, target: int) -> float:
    """Multiple independent register/interval cues, not a blanket overlap veto.

    Confidence is heuristic, not a calibrated probability. A stable longer voice
    and a large robust-register excursion are required without motif evidence.
    Ordinary high notes within that register retain their octave identity.
    """
    if abs(target - note.pitch) != 12 or not 0 <= target <= 127:
        return 0.0
    for line in voice_paths(clip):
        for i, n in enumerate(line):
            if n.id != note.id:
                continue
            if _motif_octave(line, i, target):
                return 1.0
            chord_neighbors = [x for x in clip.notes if x.id != note.id and x.track == note.track
                               and x.channel == note.channel
                               and abs(x.onset_ticks - note.onset_ticks) <= clip.ticks_per_beat / 32]
            if any(abs(x.pitch - note.pitch) <= 7 and abs(x.pitch - target) > 7
                   for x in chord_neighbors):
                return 0.0  # A compact chord is evidence of an intentional register, even if voice assignment is uncertain.
            peers = sorted(x.pitch for x in line if x.id != note.id)
            if len(peers) < 6:
                return 0.0
            low, high = peers[(len(peers) - 1) // 4], peers[3 * (len(peers) - 1) // 4]
            adjacent = line[max(0, i - 2):i] + line[i + 1:i + 3]
            near = sorted(adjacent, key=lambda x: (abs(x.onset_ticks - note.onset_ticks), x.id))[:2]
            excursion = note.pitch < low - 7 or note.pitch > high + 7
            if (high - low <= 7 and excursion and low - 2 <= target <= high + 2
                    and len(near) == 2 and all(abs(target - x.pitch) <= 5 for x in near)
                    and sum(abs(note.pitch - x.pitch) - abs(target - x.pitch) for x in near) >= 12):
                return .85
            return 0.0
    return 0.0


def _motif_octave(line: tuple[MidiNote, ...], index: int, target: int) -> bool:
    """Three unchanged notes plus matching rhythm support one octave discrepancy."""
    for start in range(max(0, index - 3), min(index + 1, len(line) - 3)):
        first = line[start:start + 4]
        offset = index - start
        for other in range(len(line) - 3):
            if abs(other - start) < 4:
                continue
            second = line[other:other + 4]
            if second[offset].pitch != target:
                continue
            if all(a.duration_ticks == b.duration_ticks
                   and a.onset_ticks - first[0].onset_ticks == b.onset_ticks - second[0].onset_ticks
                   and (i == offset or a.pitch == b.pitch)
                   for i, (a, b) in enumerate(zip(first, second, strict=True))):
                return True
    return False
