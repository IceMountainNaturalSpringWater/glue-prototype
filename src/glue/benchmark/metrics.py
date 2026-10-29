"""Reference-relative metrics, independent of the optimizer's objective.

All timing distances use quarter-note beats. Notes are matched by immutable
source identity, never by their repaired pitch/onset or output sort position.
Proxy musical descriptors are explicitly not listening-quality judgments.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations, pairwise
from statistics import mean

from glue.models import MidiClip, MidiNote

from .corrupt import FIELDS, Corruption


def _ratio(numerator: float, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _index(clips: tuple[MidiClip, ...]) -> dict[tuple[int, int], MidiNote]:
    return {(slot, n.id): n for slot, c in enumerate(clips) for n in c.notes}


def _voice_sequences(clips: tuple[MidiClip, ...]) -> list[list[tuple[int, int]]]:
    groups = defaultdict(list)
    for slot, clip in enumerate(clips):
        for n in clip.notes:
            if not n.is_percussion:
                groups[slot, n.track, n.channel].append(n)
    return [[(slot, n.id) for n in sorted(notes, key=lambda n: (n.onset_ticks, n.pitch, n.id))]
            for (slot, _, _), notes in sorted(groups.items())]


def _structure(reference: tuple[MidiClip, ...], revised: tuple[MidiClip, ...]) -> dict:
    truth, actual = _index(reference), _index(revised)
    contour, motif = [], []
    for sequence in _voice_sequences(reference):
        for a, b in pairwise(sequence):
            if truth[a].onset_ticks == truth[b].onset_ticks:
                continue
            old = truth[b].pitch - truth[a].pitch
            new = actual[b].pitch - actual[a].pitch
            contour.append((old > 0) - (old < 0) == (new > 0) - (new < 0))
        # Exact reference four-note motifs, with transposition-invariant pitch
        # intervals and exact inter-onset/duration patterns. No GLUE motif model.
        def signature(ids, notes):
            first = notes[ids[0]]
            return tuple((notes[k].pitch - first.pitch,
                          notes[k].onset_ticks - first.onset_ticks,
                          notes[k].duration_ticks) for k in ids)

        occurrences = defaultdict(list)
        for i in range(len(sequence) - 3):
            ids = sequence[i:i + 4]
            occurrences[signature(ids, truth)].append((i, ids))
        for expected, matches in occurrences.items():
            if len(matches) > 1 and matches[-1][0] - matches[0][0] >= 4:
                motif.extend(signature(ids, actual) == expected for _, ids in matches)
    return {"melodic_contour_similarity": _ratio(sum(contour), len(contour)),
            "contour_comparisons": len(contour),
            "motif_similarity": _ratio(sum(motif), len(motif)), "motif_occurrences": len(motif)}


def descriptors(clips: tuple[MidiClip, ...]) -> dict:
    """Simple transparent proxies; intentional dissonance/unisons remain valid music."""
    notes = [(i, n, c.ticks_per_beat) for i, c in enumerate(clips)
             for n in c.notes if not n.is_percussion]
    overlap_weight = tension = cross_weight = cross_tension = 0.0
    simultaneous = 0
    cross_pairs = 0
    separations = []
    for (i, a, qa), (j, b, qb) in combinations(notes, 2):
        overlap = max(0, min(a.end_ticks / qa, b.end_ticks / qb)
                      - max(a.onset_ticks / qa, b.onset_ticks / qb))
        dissonance = {1: 1, 11: 1, 6: 0.7, 2: 0.15, 10: 0.15}.get((a.pitch - b.pitch) % 12, 0)
        overlap_weight += overlap
        tension += overlap * dissonance
        if i != j:
            cross_pairs += 1
            simultaneous += abs(a.onset_ticks / qa - b.onset_ticks / qb) <= 1 / 64
            cross_weight += overlap
            cross_tension += overlap * dissonance
            if overlap:
                separations.append(abs(a.pitch - b.pitch))
    result = {"harmony_compatibility_proxy": 1 - tension / overlap_weight
              if overlap_weight else None}
    if len(clips) == 2:
        density = _ratio(simultaneous, cross_pairs)
        result.update({"simultaneous_attack_density": density,
                       "rhythmic_complementarity_proxy": 1 - density if density is not None else None,
                       "register_separation_semitones": mean(separations) if separations else None,
                       "cross_clip_harmonic_compatibility_proxy": 1 - cross_tension / cross_weight
                       if cross_weight else None})
    return result


def measure(
    reference: tuple[MidiClip, ...], corruption: Corruption, revised: tuple[MidiClip, ...],
) -> dict:
    truth, damaged, actual = _index(reference), _index(corruption.clips), _index(revised)
    if not truth.keys() == damaged.keys() == actual.keys() or len(reference) != len(revised):
        raise ValueError("Metrics require stable source note identities")
    if any(a.ticks_per_beat != b.ticks_per_beat
           for a, b in zip(reference, revised, strict=True)):
        raise ValueError("Metrics require unchanged tick resolution")
    changed = {(c.slot, c.note_id) for c in corruption.changes}
    corrupted_fields = {(c.slot, c.note_id, f) for c in corruption.changes for f in c.fields}
    for key in truth:
        expected = {f for f in FIELDS if getattr(truth[key], f) != getattr(damaged[key], f)}
        recorded = {f for f in FIELDS if (*key, f) in corrupted_fields}
        if expected != recorded:
            raise ValueError("Corruption ledger does not match reference/input differences")
    pitch_keys = [k for k in truth if (*k, "pitch") in corrupted_fields]
    untouched = [k for k in truth if k not in changed]
    edits = [k for k in truth if actual[k] != damaged[k]]
    unnecessary_fields = sum(getattr(actual[k], f) != getattr(damaged[k], f)
                             and (*k, f) not in corrupted_fields for k in truth for f in FIELDS)
    unnecessary_notes = sum(k in edits for k in untouched)
    before_distance = after_distance = 0.0
    onset_before, onset_after, duration_before, duration_after = [], [], [], []
    pitch_before, pitch_after = [], []
    for k, original in truth.items():
        ppq = reference[k[0]].ticks_per_beat
        pitch_before.append(abs(damaged[k].pitch - original.pitch))
        pitch_after.append(abs(actual[k].pitch - original.pitch))
        onset_before.append(abs(damaged[k].onset_ticks - original.onset_ticks) / ppq)
        onset_after.append(abs(actual[k].onset_ticks - original.onset_ticks) / ppq)
        duration_before.append(abs(damaged[k].duration_ticks - original.duration_ticks) / ppq)
        duration_after.append(abs(actual[k].duration_ticks - original.duration_ticks) / ppq)
        before_distance += pitch_before[-1] + onset_before[-1] + duration_before[-1]
        after_distance += pitch_after[-1] + onset_after[-1] + duration_after[-1]
    result = {
        "pitch_edits": sum(actual[k].pitch != damaged[k].pitch for k in truth),
        "timing_edits": sum(actual[k].onset_ticks != damaged[k].onset_ticks for k in truth),
        "duration_edits": sum(actual[k].duration_ticks != damaged[k].duration_ticks for k in truth),
        "octave_displacements": sum(abs(actual[k].pitch - damaged[k].pitch) >= 12 for k in truth),
        "corrupted_notes_improved": sum(
            sum(abs(getattr(actual[k], f) - getattr(truth[k], f)) /
                (1 if f == "pitch" else reference[k[0]].ticks_per_beat) for f in FIELDS)
            < sum(abs(getattr(damaged[k], f) - getattr(truth[k], f)) /
                  (1 if f == "pitch" else reference[k[0]].ticks_per_beat) for f in FIELDS)
            for k in changed),
        "recovered_corrupted_fields": sum(getattr(actual[s, n], f) == getattr(truth[s, n], f)
                                            for s, n, f in corrupted_fields),
        "corrupted_field_count": len(corrupted_fields),
        "note_count": len(truth), "corrupted_notes": len(changed),
        "pitch_corrupted_notes": len(pitch_keys),
        "pitch_recovered_notes": sum(actual[k].pitch == truth[k].pitch for k in pitch_keys),
        "pitch_recovery_accuracy": _ratio(sum(actual[k].pitch == truth[k].pitch
                                                for k in pitch_keys), len(pitch_keys)),
        "pitch_class_recovery": _ratio(sum(actual[k].pitch % 12 == truth[k].pitch % 12
                                             for k in pitch_keys), len(pitch_keys)),
        "exact_recovered_notes": sum(actual[k] == truth[k] for k in changed),
        "exact_note_recovery": _ratio(sum(actual[k] == truth[k] for k in changed), len(changed)),
        "all_note_exact_accuracy": _ratio(sum(actual[k] == truth[k] for k in truth), len(truth)),
        "untouched_notes": len(untouched), "unnecessary_edit_count": unnecessary_notes,
        "unnecessary_field_edits": unnecessary_fields,
        "untouched_note_preservation": _ratio(len(untouched) - unnecessary_notes, len(untouched)),
        "edited_notes": len(edits),
        "clean_false_positive_rate": _ratio(len(edits), len(truth)) if not changed else None,
        "edit_distance_before": before_distance, "edit_distance_after": after_distance,
        # Explicit ancillary penalty, never a replacement for component metrics.
        "preservation_penalized_distance": after_distance + 10 * unnecessary_fields,
        "made_worse": after_distance > before_distance + 1e-9,
    }
    for name, before, after in (("onset_error_beats", onset_before, onset_after),
                                ("duration_error_beats", duration_before, duration_after),
                                ("pitch_error_semitones", pitch_before, pitch_after)):
        result[name + "_before"] = mean(before) if before else 0.0
        result[name + "_after"] = mean(after) if after else 0.0
        result[name + "_total_before"] = sum(before)
        result[name + "_total_after"] = sum(after)
    for phase, clips in (("before", corruption.clips), ("after", revised)):
        result.update({f"{key}_{phase}": value for key, value in _structure(reference, clips).items()})
        result.update({f"{key}_{phase}": value for key, value in descriptors(clips).items()})
    result["reference_descriptors"] = descriptors(reference)
    return result
