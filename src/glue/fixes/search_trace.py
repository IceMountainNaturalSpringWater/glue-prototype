"""Opt-in, ground-truth-blind developer tracing; never used for search decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import isfinite
from typing import Any

from glue.analysis.voices import voice_identities
from glue.models import MidiClip

Signature = tuple[tuple[int, int, str, int], ...]


def signature(options: tuple[Any, ...]) -> Signature:
    return tuple(sorted((o.slot, o.note_id, o.field, o.value) for o in options))


@dataclass
class SearchTrace:
    """One trace per invocation. Bounded storage; truncation is always explicit.

    No reference notes or desired targets are accepted. Consumers match targets
    post-hoc. State signatures encode changes relative to the corrupted input.
    """

    max_states: int = 20000
    options: list[dict] = field(default_factory=list)
    states: dict[Signature, dict] = field(default_factory=dict)
    winner: Signature = ()
    retained: list[Signature] = field(default_factory=list)
    truncated: bool = False
    round: int = 0
    note_contexts: list[dict] = field(default_factory=list)

    def reset(self, options: tuple[Any, ...], clips: tuple[MidiClip, ...] = ()) -> None:
        if self.max_states < 1:
            raise ValueError("Trace max_states must be positive")
        self.options.clear()
        self.states.clear()
        self.retained.clear()
        self.winner = ()
        self.truncated = False
        self.round = 0
        self.note_contexts = [
            {"slot": slot, **asdict(identity), "original_pitch": note.pitch,
             "original_onset_beats": note.onset_ticks / clip.ticks_per_beat,
             "original_duration_beats": note.duration_ticks / clip.ticks_per_beat}
            for slot, clip in enumerate(clips)
            for identity in voice_identities(clip)
            for note in clip.notes if note.id == identity.note_id]
        ranks: dict[tuple, int] = {}
        for rank, option in enumerate(options, 1):
            key = (option.slot, option.note_id, option.field)
            ranks[key] = ranks.get(key, 0) + 1
            self.options.append({"slot": option.slot, "note_id": option.note_id,
                                 "field": option.field, "value": option.value,
                                 "global_rank": rank, "field_rank": ranks[key],
                                 "reason": option.reason,
                                 "provenance": getattr(option, "provenance", ())})

    def record(self, history: tuple[Any, ...], reason: str, candidate: Any = None) -> None:
        key = signature(history)
        if key not in self.states:
            if len(self.states) >= self.max_states:
                self.truncated = True
                return
            self.states[key] = {"changes": key, "rounds": [], "outcomes": [],
                                "scored": False, "survived_beam": False,
                                "beam_pruned": False, "components": None,
                                "objective": None, "retention_cost": None, "edit_cost": None}
        state = self.states[key]
        if self.round not in state["rounds"]:
            state["rounds"].append(self.round)
        if reason not in state["outcomes"]:
            state["outcomes"].append(reason)
        if candidate is not None:
            state["scored"] = True
            state["components"] = dict(candidate.score.components)
            for name in ("objective", "retention_cost", "edit_cost"):
                value = getattr(candidate, name)
                state[name] = value if isfinite(value) else None

    def beam(self, successors: list, frontier: list) -> None:
        kept = {signature(history) for _, history in frontier}
        for _, history in successors:
            key = signature(history)
            if key in self.states:
                self.states[key]["survived_beam" if key in kept else "beam_pruned"] = True

    def finish(self, candidates: list) -> None:
        self.retained = []
        for candidate in candidates:
            self.retained.append(tuple(sorted(
                (edit.slot, edit.note_id, name, getattr(edit.after, name))
                for edit in candidate.edits for name in ("pitch", "onset_ticks", "duration_ticks")
                if getattr(edit.before, name) != getattr(edit.after, name)
            )))
        self.winner = self.retained[0] if self.retained else ()
