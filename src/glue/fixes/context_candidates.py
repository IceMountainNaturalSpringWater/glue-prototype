"""Bounded context alternatives; no ground truth and no new objective weights."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import pairwise
from statistics import median

from glue.analysis.key import estimate_key
from glue.analysis.musical import analyze_musical, harmony_at
from glue.analysis.relationships import performance_relations
from glue.analysis.voices import (
    octave_confidence,
    octave_supported,
    pitch_supported,
    voice_identities,
    voice_ornaments,
    voice_paths,
)
from glue.models import MidiClip, MidiNote

from .musical_config import EditPermissions, MusicalSearch


@dataclass(frozen=True)
class ContextOption:
    note_id: int
    field: str
    value: int
    reason: str
    strength: int


def _legacy_context_options(clip: MidiClip, allow: EditPermissions, config: MusicalSearch) -> tuple[ContextOption, ...]:
    model = analyze_musical(clip)
    contexts = {n.note_id: n for n in model.notes}
    choices = []
    pitch_cap = {"minimal": 2, "balanced": 4, "creative": 6}[config.preset.value]
    for line in voice_paths(clip):
        for i in range(1, len(line) - 1):
            previous, note, following = line[i - 1:i + 2]
            context = contexts[note.id]
            frame = harmony_at(model.frames, note.onset_ticks / clip.ticks_per_beat)
            # Two-sided local evidence only; do not flatten every melodic turn.
            if (allow.pitch and not context.protected and context.metric_strength >= 0.7
                    and note.duration_ticks >= 0.75 * clip.ticks_per_beat):
                values = []
                center = (previous.pitch + following.pitch) / 2
                if (center == int(center) and abs(previous.pitch - following.pitch) in (0, 2, 4)
                        and abs(note.pitch - center) <= config.pitch_range):
                    values.append(int(center))
                if frame and context.tension > 0:
                    values += [p for p in range(max(0, note.pitch - config.pitch_range),
                                                min(128, note.pitch + config.pitch_range + 1))
                               if p % 12 in frame.harmony.pitches]
                for p in sorted(set(values), key=lambda p: (abs(p - center), abs(p - note.pitch), p))[:pitch_cap]:
                    if p != note.pitch and octave_supported(clip, note, p):
                        choices.append(ContextOption(note.id, "pitch", p,
                            "Two-sided voice continuity and local tonal context suggest this bounded alternative.",
                            1 + int(context.tension > 0)))
            # Isolated rhythmic/articulation discrepancy in a strongly repeated
            # local pattern. This generates options, not a quantization rule.
            if config.preset.value == "minimal" or len(line) < 5:
                continue
            gaps = [b.onset_ticks - a.onset_ticks for a, b in pairwise(line)
                    if a.id != note.id and b.id != note.id]
            if gaps:
                gap, count = Counter(gaps).most_common(1)[0]
                onset = previous.onset_ticks + gap
                if (allow.timing and count >= 2 and count / len(gaps) >= 0.75
                        and following.onset_ticks - onset == gap and onset != note.onset_ticks
                        and abs(onset - note.onset_ticks) <= config.onset_beats * clip.ticks_per_beat):
                    choices.append(ContextOption(note.id, "onset_ticks", onset,
                        "An isolated onset differs from both neighbors in an otherwise repeated rhythmic pattern; preserves its off-grid phase.", 4))
            lengths = Counter(n.duration_ticks for n in line if n.id != note.id)
            duration, count = lengths.most_common(1)[0]
            if (allow.duration and count >= 3 and count / (len(line) - 1) >= 0.75
                    and previous.duration_ticks == following.duration_ticks == duration
                    and duration != note.duration_ticks
                    and duration <= following.onset_ticks - note.onset_ticks
                    and following.onset_ticks - note.onset_ticks <= duration + clip.ticks_per_beat / 8
                    and abs(duration - note.duration_ticks) <= min(
                        config.duration_beats * clip.ticks_per_beat,
                        config.duration_fraction * note.duration_ticks)):
                choices.append(ContextOption(note.id, "duration_ticks", duration,
                    "An isolated duration differs from adjacent notes in a strongly repeated articulation pattern; no global normalization.", 4))
    return tuple(sorted(choices, key=lambda o: (-o.strength, o.note_id, o.field, o.value)))


def _templates(line: tuple[MidiNote, ...], index: int, ppq: int) -> list[ContextOption]:
    """Bounded four-note analogues; three unchanged anchors, no reference access.

    Matching relative pitch permits transposed phrases. Median alignment leaves
    one suspicious onset out of the fit and tolerates small performance jitter.
    Alternatives are evidence, not a command to eliminate musical variation.
    """
    note = line[index]
    result = []
    for start in range(max(0, index - 3), min(index + 1, len(line) - 3)):
        offset = index - start
        first = line[start:start + 4]
        candidates = sorted((s for s in range(max(0, start - 48), min(len(line) - 3, start + 49))
                             if abs(s - start) >= 4),
                            key=lambda s: (abs(s - start), s))[:24]
        for other in candidates:
            second = line[other:other + 4]
            anchors = [(a, b) for j, (a, b) in enumerate(zip(first, second, strict=True))
                       if j != offset]
            transpositions = [a.pitch - b.pitch for a, b in anchors]
            if len(set(transpositions)) != 1:
                continue
            shift = int(median(a.onset_ticks - b.onset_ticks for a, b in anchors))
            if any(abs(a.onset_ticks - b.onset_ticks - shift) > ppq / 32 for a, b in anchors):
                continue
            counterpart = second[offset]
            for field, value, reason in (
                ("pitch", counterpart.pitch + transpositions[0], "motif correspondence"),
                ("onset_ticks", counterpart.onset_ticks + shift, "rhythmic motif"),
                ("duration_ticks", counterpart.duration_ticks, "motif articulation"),
            ):
                if value != getattr(note, field):
                    # Microtiming/duration variation is not an error. Require
                    # an isolated discrepancy beyond surrounding articulation.
                    threshold = ppq / (8 if field == "duration_ticks" else 16)
                    if field != "pitch" and (abs(value - getattr(note, field)) <= threshold
                            or any(abs(a.duration_ticks - b.duration_ticks) > ppq / 16
                                   for a, b in anchors)):
                        continue
                    result.append(ContextOption(note.id, field, value, reason, 5))
    return result


def _rhythm(line: tuple[MidiNote, ...], i: int, ppq: int,
            config: MusicalSearch) -> list[ContextOption]:
    if not 0 < i < len(line) - 1 or len(line) < 4:
        return []
    note, previous, following = line[i], line[i - 1], line[i + 1]
    neighbors = line[max(0, i - 4):i] + line[i + 1:i + 5]
    choices = []
    # Infer a shared local subdivision phase, not a zero-phase quantization.
    for unit in (ppq / 2, ppq / 4, ppq / 8):
        phases = [n.onset_ticks % unit for n in neighbors]
        if len(phases) < 3:
            continue
        phase = min(phases, key=lambda p: sum(min(abs(q - p), unit - abs(q - p)) for q in phases))
        residuals = [min(abs(p - phase), unit - abs(p - phase)) for p in phases]
        if sum(r <= ppq / 32 for r in residuals) < max(3, len(phases) * 0.75):
            continue
        target = round(round((note.onset_ticks - phase) / unit) * unit + phase)
        if abs(target - note.onset_ticks) <= ppq / 16:
            continue  # Keep ordinary expressive microtiming.
        if previous.onset_ticks < target < following.onset_ticks:
            choices.append(ContextOption(note.id, "onset_ticks", target, "nearby subdivision in inferred groove", 3))
        # Preserve the performed offset while correcting a subdivision-scale
        # discontinuity; never sweep every tick around the desired reference.
        for step in (ppq / 8, ppq / 4, ppq / 2):
            if step != int(step):
                continue
            value = note.onset_ticks + int(step) * (1 if target > note.onset_ticks else -1)
            if abs(value - target) <= ppq / 32 and previous.onset_ticks < value < following.onset_ticks:
                choices.append(ContextOption(note.id, "onset_ticks", value, "voice continuity with groove offset", 3))
        break
    # A local performed pulse need not line up with any absolute MIDI grid.
    gaps = [b.onset_ticks - a.onset_ticks for a, b in pairwise(
        line[max(0, i - 4):i + 5]) if a.id != note.id and b.id != note.id]
    if len(gaps) >= 3:
        pulse = median(gaps)
        incoming = note.onset_ticks - previous.onset_ticks
        outgoing = following.onset_ticks - note.onset_ticks
        if (pulse >= ppq / 8 and sum(abs(g - pulse) <= pulse * 0.2 for g in gaps) >= len(gaps) * 0.75
                and (incoming - pulse) * (outgoing - pulse) < 0
                and abs(incoming + outgoing - 2 * pulse) <= pulse * 0.2
                and abs(incoming - outgoing) > ppq / 8):
            center = (previous.onset_ticks + following.onset_ticks) / 2
            values = {round(center), round(previous.onset_ticks + pulse), round(following.onset_ticks - pulse)}
            for step in (ppq / 8, ppq / 4, ppq / 2):
                if step == int(step):
                    value = note.onset_ticks + int(step) * (1 if center > note.onset_ticks else -1)
                    if abs(value - center) <= pulse * 0.1:
                        values.add(value)
            choices.extend(ContextOption(note.id, "onset_ticks", v, "neighbor onset intervals / performed pulse", 3)
                           for v in sorted(values) if abs(v - note.onset_ticks) > ppq / 16)
    # Compare duration to the local IOI, not raw length: an expressive long
    # note preceding a long gap is not a sustain error merely because its
    # neighbors are shorter. Pedal tails remain ambiguous.
    gap = following.onset_ticks - note.onset_ticks
    articulations = [a.duration_ticks / (b.onset_ticks - a.onset_ticks)
                     for a, b in pairwise(line[max(0, i - 4):i + 5])
                     if a.id != note.id and b.id != note.id and b.onset_ticks > a.onset_ticks]
    ratio = median(articulations) if articulations else 1.0
    typical = ratio * gap
    if (len(articulations) >= 3 and sum(abs(r - ratio) <= 0.15 for r in articulations) >= 3
            and (note.duration_ticks > typical * 1.6 and note.duration_ticks - gap >= ppq / 4
                 or note.duration_ticks < typical * 0.5)):
        values = {round(typical), gap, previous.duration_ticks, following.duration_ticks}
        # Direct local release boundaries and bounded articulation increments.
        for step in (ppq / 8, ppq / 4, ppq / 2):
            if step == int(step):
                value = note.duration_ticks + int(step) * (1 if typical > note.duration_ticks else -1)
                if abs(value - typical) < abs(note.duration_ticks - typical):
                    values.add(value)
        for value in sorted(values):
            if value > 0 and value <= gap + ppq / 16 and abs(value - note.duration_ticks) > ppq / 8:
                choices.append(ContextOption(note.id, "duration_ticks", value, "neighbor articulation and voice release", 3))
    return choices


def context_options(clip: MidiClip, allow: EditPermissions, config: MusicalSearch) -> tuple[ContextOption, ...]:
    model = analyze_musical(clip)
    contexts = {n.note_id: n for n in model.notes}
    result = [o for o in _legacy_context_options(clip, allow, config)
              if o.field != "onset_ticks" or abs(o.value - next(
                  n.onset_ticks for n in clip.notes if n.id == o.note_id)) > clip.ticks_per_beat / 16]
    expressive = performance_relations(clip)
    roles = {v.note_id: v.role for v in voice_identities(clip)}
    ornaments = voice_ornaments(clip)
    keys = estimate_key(clip).candidates[:2]
    key_pcs = {(k.tonic_pc + p) % 12 for k in keys for p in
               ((0, 2, 4, 5, 7, 9, 11) if k.mode == "major" else (0, 2, 3, 5, 7, 8, 10))}
    for line in voice_paths(clip):
        for i, note in enumerate(line):
            context = contexts[note.id]
            frame = harmony_at(model.frames, note.onset_ticks / clip.ticks_per_beat)
            proposals = _templates(line, i, clip.ticks_per_beat)
            proposals.extend(ContextOption(note.id, "pitch", p, "corroborated octave register/interval context", 5)
                             for p in (note.pitch - 12, note.pitch + 12)
                             if octave_confidence(clip, note, p) >= .8)
            neighbors = line[max(0, i - 1):i] + line[i + 1:i + 2]
            tonal_evidence = context.tension >= 0.5 or (
                context.tension > 0 and len(neighbors) == 2
                and not any(contexts[n.id].protected for n in neighbors))
            if allow.pitch and not context.protected and tonal_evidence and neighbors:
                values: dict[int, str] = {n.pitch: "melodic neighbor / voice continuity" for n in neighbors}
                if len(neighbors) == 2:
                    center = (neighbors[0].pitch + neighbors[1].pitch) / 2
                    if center == int(center):
                        values[int(center)] = "local melodic contour"
                for p in range(max(0, note.pitch - config.pitch_range),
                               min(128, note.pitch + config.pitch_range + 1)):
                    if frame and p % 12 in frame.harmony.pitches:
                        values.setdefault(p, "local harmony / smooth voice leading")
                    elif any(abs(p - n.pitch) <= 2 for n in neighbors):
                        values.setdefault(p, "chromatic or diatonic passing possibility")
                    elif p % 12 in key_pcs and abs(p - note.pitch) <= 2:
                        values.setdefault(p, "key/mode alternative (ambiguous)")
                    elif frame and any(p % 12 in h.pitches for h in frame.alternatives[:2]):
                        values.setdefault(p, "alternative harmony / plausible extension")
                # Existing key model is evidence, never an out-of-key veto.
                for p, reason in values.items():
                    if roles[note.id] == "bass":
                        reason += " / bass-motion context"
                    proposals.append(ContextOption(note.id, "pitch", p, reason, 1))
            if config.preset.value != "minimal":
                proposals.extend(ContextOption(note.id, relation.field, v, relation.reason, 4)
                                 for relation in expressive if relation.note_id == note.id
                                 for v in relation.values)
                rhythmic = _rhythm(line, i, clip.ticks_per_beat, config)
                proposals.extend(rhythmic)
                if frame and any(o.field == "onset_ticks" for o in rhythmic):
                    proposals.append(ContextOption(note.id, "onset_ticks",
                        round(frame.start * clip.ticks_per_beat), "harmony boundary with rhythmic evidence", 2))
            for option in proposals:
                field, value = option.field, option.value
                if value == getattr(note, field):
                    continue
                if field == "pitch":
                    if (not allow.pitch or context.protected or note.id in ornaments or not 0 <= value <= 127
                            or option.strength == 5 and 2 < abs(value - note.pitch) < 12
                            or not (abs(value - note.pitch) <= config.pitch_range
                                    or abs(value - note.pitch) == 12 and option.strength == 5)
                            or not pitch_supported(clip, note, value)):
                        continue
                elif field == "onset_ticks":
                    if (not allow.timing or config.preset.value == "minimal" or value < 0
                            or abs(value - note.onset_ticks) > config.onset_beats * clip.ticks_per_beat):
                        continue
                elif (not allow.duration or config.preset.value == "minimal" or value <= 0
                      or option.strength == 5 and abs(value - note.duration_ticks) < clip.ticks_per_beat / 4
                      or abs(value - note.duration_ticks) > min(config.duration_beats * clip.ticks_per_beat,
                                                                config.duration_fraction * note.duration_ticks)):
                    continue
                result.append(option)
    return tuple(sorted(set(result), key=lambda o: (-o.strength, o.note_id, o.field, o.value, o.reason)))
