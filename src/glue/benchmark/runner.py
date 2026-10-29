"""Blind V0.5 engine invocation followed by ground-truth-only evaluation."""

from __future__ import annotations

import hashlib
import json
import platform
from collections.abc import Callable
from dataclasses import asdict, dataclass
from dataclasses import field as dataclass_field
from pathlib import Path
from time import perf_counter

from glue import __version__
from glue.analysis.musical import analyze_musical, infer_harmony, joint_chord_spans
from glue.fixes import musical as engine
from glue.fixes.musical_config import EditPermissions
from glue.fixes.search_trace import SearchTrace
from glue.models import MidiClip

from .corrupt import KINDS, Corruption, corrupt
from .manifest import digest, load_entry, stable_seed, validate_manifest
from .metrics import measure
from .tracing import targets


@dataclass(frozen=True)
class Experiment:
    presets: tuple[str, ...] = ("minimal", "balanced", "creative")
    preservations: tuple[int, ...] = (0, 50, 90, 100)
    kinds: tuple[str, ...] = KINDS
    seeds: tuple[int, ...] = (0,)
    severity: float = 1.0
    count: int = 1
    permissions: EditPermissions = dataclass_field(
        default_factory=lambda: EditPermissions(True, True, True)
    )
    split: str = "calibration"
    max_notes: int = 256
    pair_preservation: tuple[tuple[int, int], ...] = ()
    trace: bool = False

    def __post_init__(self) -> None:
        if not self.presets or any(p not in {"minimal", "balanced", "creative"} for p in self.presets):
            raise ValueError("Select valid presets")
        values = (*self.preservations, *(p for pair in self.pair_preservation for p in pair))
        if not self.preservations or any(type(p) is not int or not 0 <= p <= 100 for p in values):
            raise ValueError("Preservation must be integer percentages")
        if any(len(pair) != 2 for pair in self.pair_preservation):
            raise ValueError("Pair preservation requires A:B percentages")
        if self.split not in {"calibration", "evaluation"} or self.max_notes < 1:
            raise ValueError("Select a split and positive max_notes")
        if not self.seeds or any(type(s) is not int for s in self.seeds):
            raise ValueError("Provide integer seeds")
        if any(kind not in KINDS for kind in self.kinds):
            raise ValueError("Unknown corruption type")
        # Validate corruption settings even on empty datasets.
        from math import isfinite
        if not isfinite(self.severity) or not 0 < self.severity <= 4 or self.count < 1:
            raise ValueError("Invalid severity or count")


def algorithm_fingerprint() -> str:
    root = Path(engine.__file__).parents[1]
    files = sorted(p for directory in ("analysis", "fixes", "models", "io")
                   for p in (root / directory).glob("*.py"))
    value = "\n".join(f"{p.relative_to(root).as_posix()}:{digest(p)}" for p in files)
    return hashlib.sha256(value.encode()).hexdigest()


def benchmark_fingerprint() -> str:
    files = sorted(Path(__file__).parent.glob("*.py"))
    return hashlib.sha256("\n".join(f"{p.name}:{digest(p)}" for p in files).encode()).hexdigest()


def clear_caches() -> None:
    """Cold top-level analysis/repair caches per run; pure transition memoization remains."""
    for function in (analyze_musical, infer_harmony, joint_chord_spans,
                     engine._suggestions, engine._coincidence):
        function.cache_clear()


def _diagnose(corruption: Corruption, repair: engine.MusicalRepair, metrics: dict) -> list[dict]:
    """Post-hoc hypotheses, never inputs to search; no rerunning repair with an oracle.

    Private option introspection is isolated here so a future trace API can
    replace it without changing production behavior. Absence of the original
    value proves a candidate coverage gap, not its upstream musical cause.
    """
    findings = []

    def add(stage: str, evidence: str, certainty: str = "hypothesis") -> None:
        findings.append({"stage": stage, "certainty": certainty, "evidence": evidence})

    if metrics["unnecessary_field_edits"]:
        add("scoring", "Selected edits changed untouched fields; fit objective differs from recovery.")
    if not corruption.changes:
        if metrics["edited_notes"]:
            add("analysis", "A designated clean reference received edits; requires musical review.")
        return findings
    if metrics["exact_note_recovery"] == 1 and not metrics["unnecessary_field_edits"]:
        return findings
    options = engine._options(corruption.clips, repair.permissions, repair.preservation,
                              repair.config, None, frozenset(), {})
    available = {(o.slot, o.note_id, o.field, o.value) for o in options}
    missing = []
    for change in corruption.changes:
        if repair.preservation[change.slot] == 100:
            add("preservation penalties", f"Clip {change.slot} is hard-locked at 100%.", "observed")
            continue
        for field in change.fields:
            permission = {"pitch": "pitch", "onset_ticks": "timing", "duration_ticks": "duration"}[field]
            if not getattr(repair.permissions[change.slot], permission):
                add(f"{permission} logic" if permission != "pitch" else "candidate generation",
                    f"{permission} permission is off; recovery of this field is prohibited.", "observed")
            elif (change.slot, change.note_id, field, getattr(change.before, field)) not in available:
                missing.append((change.slot, change.note_id, field))
    if missing:
        add("candidate generation", f"Exact reference values absent from initial options: {missing}.",
            "observed")
        if any(f == "onset_ticks" for _, _, f in missing):
            add("timing logic", "Onset options are gated/grid-bounded; inspect missing targets.")
        if any(f == "duration_ticks" for _, _, f in missing):
            add("duration logic", "Duration options are gated/bounded; inspect missing targets.")
        models = [analyze_musical(c) for c in corruption.clips]
        if any(frame.confidence < 0.5 for model in models for frame in model.frames):
            add("harmony inference", "Low-confidence harmonic frames exist; causal link unproven.")
        add("analysis", "Coverage gaps can reflect evidence ranking or protected ornament labels.")
    if "budget reached" in repair.stop_reason.lower():
        add("search", "Evaluation budget was exhausted; missed combinations are possible.", "observed")
    if any(0 < p < 100 for p in repair.preservation):
        add("preservation penalties", "Nonzero edit penalties may suppress recovery; compare 0% runs.")
    if not findings:
        add("search", "Available targets did not recover truth; pruning, safety or scoring unresolved.")
    return findings


def run_case(reference: tuple[MidiClip, ...], corruption: Corruption, *, preset: str,
             preservation: tuple[int, ...], permissions: EditPermissions,
             tracing: bool = False) -> dict:
    clear_caches()
    started = perf_counter()
    observer = SearchTrace() if tracing else None
    # The sole repair call: no reference, ledger, note-selection mask, chord
    # annotations, or truth-derived pitch targets can cross this boundary.
    repair = engine.generate_musical_repairs(
        *corruption.clips, preset=preset, preservation=preservation,
        permissions=(permissions,) * len(corruption.clips),
        **({"trace": observer} if observer is not None else {}),
    )
    elapsed = perf_counter() - started
    revised = repair.candidates[0].clips if repair.candidates else corruption.clips
    metrics = measure(reference, corruption, revised)
    diagnostics_started = perf_counter()
    diagnosis = _diagnose(corruption, repair, metrics)
    alternatives = [measure(reference, corruption, c.clips)["edit_distance_after"]
                    for c in repair.candidates]
    if alternatives and min(alternatives) < metrics["edit_distance_after"] - 1e-9:
        diagnosis.append({"stage": "scoring", "certainty": "observed",
                          "evidence": "A retained lower-ranked alternative is closer to truth."})
    return {**({"search_trace": targets(corruption, observer, repair)} if observer else {}),
            "preset": preset, "preservation": preservation,
            "permissions": asdict(permissions), "metrics": metrics,
            "runtime_seconds": elapsed, "diagnostic_seconds": perf_counter() - diagnostics_started,
            "evaluations": repair.evaluations, "stop_reason": repair.stop_reason,
            "search_config": asdict(repair.config), "failure_hypotheses": diagnosis,
            "glue_estimate_before": repair.before.estimate,
            "glue_estimate_after": repair.candidates[0].score.estimate
            if repair.candidates else repair.before.estimate,
            "retained_candidate_reference_distances": alternatives,
            "selected_candidate": 0 if repair.candidates else None,
            "edits": [asdict(e) for e in repair.candidates[0].edits] if repair.candidates else []}


def reproducible_payload(report: dict) -> dict:
    """Exclude only wall-clock/environment fields, not outcomes, settings or errors."""
    return {key: ([{k: v for k, v in row.items() if k not in {"runtime_seconds", "diagnostic_seconds"}}
                   for row in value] if key == "results" else value)
            for key, value in report.items() if key not in {"environment", "reproducibility_digest"}}


def run_benchmark(manifest: dict, experiment: Experiment, *,
                  progress: Callable[[str], None] | None = None) -> dict:
    validate_manifest(manifest)
    rows, skipped = [], []
    root = Path(manifest["root"])
    for entry in sorted(manifest["entries"], key=lambda item: item["id"]):
        if entry["split"] != experiment.split:
            continue
        try:
            clips, documents = load_entry(root, entry)
        except (ValueError, OSError) as exc:
            skipped.append({"entry": entry["id"], "reason": str(exc)})
            continue
        if sum(len(c.notes) for c in clips) > experiment.max_notes:
            skipped.append({"entry": entry["id"], "reason": "Exceeds explicit max_notes bound"})
            continue
        plans = [("clean", experiment.seeds[0])]
        plans += [(kind, seed) for kind in experiment.kinds for seed in experiment.seeds]
        for kind, seed in plans:
            case_seed = stable_seed(seed, entry["id"], kind)
            corruption = corrupt(clips, kind, seed=case_seed, severity=experiment.severity,
                                 count=experiment.count)
            if corruption.skipped:
                skipped.append({"entry": entry["id"], "kind": kind, "seed": seed,
                                "reason": corruption.skipped})
                continue
            ledger = []
            for change in corruption.changes:
                binding = documents[change.slot].bindings[change.note_id]
                ledger.append({**change.record(), "source_events": asdict(binding)})
            settings = [tuple([p] * len(clips)) for p in experiment.preservations]
            if len(clips) == 2:
                settings += list(experiment.pair_preservation)
            for preset in experiment.presets:
                for preservation in dict.fromkeys(settings):
                    identity = {"entry": entry["id"], "group": entry["group"],
                                "dataset": manifest["dataset"],
                                "workflow": "pair" if len(clips) == 2 else "single",
                                "kind": kind, "seed": seed, "corruption_seed": case_seed,
                                "split": entry["split"], "corruption_ledger": ledger}
                    if progress:
                        progress(f"{entry['id']} / {kind} / {preset} / {preservation}")
                    try:
                        row = run_case(clips, corruption, preset=preset,
                                       preservation=preservation, permissions=experiment.permissions,
                                       tracing=experiment.trace)
                    except (ValueError, RuntimeError, ArithmeticError) as exc:
                        # Keep failed runs in reports, not in a successful-run denominator.
                        row = {"preset": preset, "preservation": preservation,
                               "error": f"{type(exc).__name__}: {exc}"}
                    rows.append({**identity, **row})
    content_manifest = {k: v for k, v in manifest.items() if k != "root"}
    report = {"schema": 1, "glue_version": __version__,
              "algorithm_sha256": algorithm_fingerprint(),
              "benchmark_sha256": benchmark_fingerprint(), "manifest": content_manifest,
              "experiment": asdict(experiment), "results": rows, "skipped": skipped,
              "metric_notes": {
                  "distance": "sum(abs pitch semitones + abs onset beats + abs duration beats)",
                  "penalized_distance": "distance + 10 * unnecessary field edits; ancillary only",
                  "null": "not applicable / no observations, never an automatic perfect score",
                  "selection": "first engine candidate; retained alternatives are diagnostics only",
                  "runtime": "repair invocation only, excluding I/O, corruption and metric calculation",
                  "harmony": "duration-weighted interval proxy, not independent chord-label accuracy",
                  "motif": "exact four-note reference patterns; pitch intervals, onsets and durations",
              },
              "environment": {"python": platform.python_version(), "platform": platform.platform(),
                              "cache_policy": "Cold top-level caches; pure transition cache retained"}}
    report["reproducibility_digest"] = hashlib.sha256(json.dumps(
        reproducible_payload(report), sort_keys=True, allow_nan=False).encode()).hexdigest()
    return report
