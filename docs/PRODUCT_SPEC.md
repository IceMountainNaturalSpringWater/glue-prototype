# GLUE V0.3 Product Specification

## Problem

Producers often have two MIDI ideas that work separately yet compete when
layered. GLUE diagnoses the relationship between existing material and should
preserve both ideas rather than generate replacements. Its scores are
interpretable estimates with reasons and ambiguity, never claims of objective
musical correctness.

## V0.3 scope

GLUE V0.3 is a deterministic, standalone, two-clip MIDI analyzer and
pitch-repair prototype. It has no audio processing, live MIDI, DAW integration,
plugins, cloud services, LLM calls, accounts, telemetry, or network features.
Single-file Polish mode is deferred.

## Primary workflow

1. Import MIDI A and MIDI B without changing either source.
2. Set independent A/B preservation values. The desktop defaults to
   100% / 100%; 100% automatically hard-locks that clip and displays a small
   **Locked** indicator.
3. Optionally use **Keep A** (100% / 0%), **Balanced** (50% / 50%), or **Keep
   B** (0% / 100%) to set the values. These are shortcuts only, and either
   slider remains freely adjustable afterward.
4. Optionally request **Suggest balance**. It uses cached analysis evidence to
   preview preservation values and a concise reason without running several
   complete repairs. The user must explicitly apply the preview. When evidence
   is weak, it reports that no strong recommendation exists and previews the
   Balanced values rather than asserting false confidence.
5. Select Minimal, Balanced, or Creative and generate only the repair requested
   by the current A/B preservation values. Analysis runs automatically if the
   repair needs it.
6. Inspect the compact estimated before/after improvement and exact edits for
   both clips. Detailed keys, component scores, timeline, and qualified reasons
   remain available in the collapsed-by-default analysis section.
7. Export revised A, revised B, a separate-track combined preview, and a JSON
   change report.

The desktop has no editing-strategy selector or separate Lock A/Lock B state.
The two preservation controls are the single source of truth. Values below
100% permit pitch edits under the selected preset and preservation penalty. If
both values are 100%, repair is disabled with a clear explanation.

## Architecture boundaries

```text
models    immutable domain data
io        MIDI parsing, source-preserving writing, combined preview creation
analysis  deterministic scoring and explanations
fixes     constraints, candidate generation, objective, bounded optimization
ui        orchestration and visualization only
```

Theory, scoring, and optimization do not belong in drawing or GUI code.

## Analysis model

Analysis uses transparent, independently testable heuristics.

### Key estimation

- Build duration-weighted pitch-class histograms.
- Compare standard major and natural-minor profiles.
- Return ranked candidates and confidence so ambiguity remains visible.

### Timeline

- Convert MIDI ticks to exact quarter-note positions.
- Analyze true simultaneous activity in one-beat windows.
- Aggregate window results into meter-aware bar summaries.

### Local harmonic compatibility

- Collect active and attacked pitch classes from A and B.
- Weight long/accented notes.
- Infer bounded diatonic triad/seventh candidates under the estimated key.
- Compare clip-local interpretations and report strong semitone/tritone
  relationships where supported.

### Bass/root, register, and rhythm

- Estimate the lowest active support without treating every inversion as a
  conflict.
- Penalize dense simultaneous register overlap as an arrangement signal.
- Compare attack density and competition; rhythmic similarity is not
  inherently good or bad.

### Overall estimated compatibility

The centralized default weighting remains:

- 50% harmonic
- 20% bass/root
- 15% register
- 15% rhythm

All component and total scores are clamped to 0–100 and exposed in the UI.

## Repair contract

Each clip has immutable independent constraints containing preservation,
pitch/octave permissions, the disabled rhythm-edit permission, and a maximum
note-change budget. Repairs may change paired note pitch only. They must retain
note identity, onset, duration, velocity, release velocity, track, channel,
tempo, meter, controllers, and unrelated source events.

Values outside valid preservation ranges are rejected. At 100% preservation a
clip receives zero edits. If both clips are hard-locked, the engine/UI returns
a clear validation message rather than crashing.

### Constraint-driven pair repair

The desktop uses one deterministic bounded beam search configured by the two
preservation values. A frontier state stores the complete revised A+B pair,
edits on both sides, a canonical full-pair analysis, and objective cost.
Children from either non-locked clip compete in the same frontier. An
up-to-eight-option-per-side cross-product admits coupled A+B steps when neither
atomic edit helps by itself. Bounded same-side pitch combinations also admit
coordinated two-note and multi-note steps whose isolated edits are
non-improving. Every child and bundle is rescored as:

```text
candidate A + candidate B
          ↓
complete compatibility analysis
          ↓
joint objective
```

The implementation must not finish a repair of A and then lock that result
while independently repairing B.

The public Preserve A, Preserve B, Shared, and Custom strategy identifiers and
the V0.2 `generate_repair(locked, unlocked)` API remain available for backward
compatibility and programmatic callers. They are not independent desktop modes
and the preservation shortcuts do not invoke them as hidden strategies.

### Suggest balance

Suggestion is an analysis heuristic, not a repair comparison. It may consider
which clip contributes more high-severity conflict evidence, conflicting-note
count and severity, note density, repeated-note strength, likely role, obvious
local pitch alternatives, displacement, and whether one side appears easier to
improve. It reuses cached pair analysis when possible and must not run full
Minimal, Balanced, and Creative repairs for either clip. The desktop
recommendation is analysis-only: it does not generate repair candidates.
Recommendations are deterministic and remain a preview until explicitly
applied.

### Objective

Candidate cost combines:

- remaining estimated conflict
- edit counts weighted independently by A/B preservation
- total semitone and octave displacement
- local contour and partial exact repeated-note disruption
- hard rejection of new same-voice equal-pitch collisions
- duration-weighted newly introduced cross-clip unisons
- close-line convergence/loss of contrapuntal independence

Coefficients live in one immutable objective configuration. Search bounds also
live in configuration: candidate notes and pitches, paired and coordinated
options per side, beam width, iterations, total/per-clip edits, successors, and
the analysis-evaluation ceiling.

At zero preservation, the ordinary edit-count, displacement, octave, contour,
and repeated-note costs are multiplied by zero. The unison, convergence,
collision, pitch-range, percussion, and pitch-only MIDI safety rules remain.
Ordinary costs increase linearly to their legacy value at 50% and stay there;
the separate quadratic preservation cost continues increasing above 50%.

The V0.3 defaults, measured in compatibility-score cost units, are:

| Term | Weight | Intended effect |
|---|---:|---|
| Remaining conflict | 1.00 | Keep estimated compatibility dominant |
| Each edit | 0.50 | Prefer fewer changes |
| Preservation × preservation² per edit | 8.00 | Move edits toward the less-protected clip |
| Semitone displacement | 0.10 | Prefer smaller pitch moves |
| Octave move | 0.75 | Avoid gratuitous register shifts |
| Contour disruption | 0.40 | Retain local melodic direction/shape |
| Partial exact repeated-note change | 0.20 | Discourage inconsistent edits within repeated-note groups |
| Newly introduced unison duration | 12.00 | Prevent raw consonance from collapsing lines |
| Close-line convergence | 0.25 | Retain modest contrapuntal separation |

### Presets

Preservation continuously interpolates each preset's edit allowance and search
breadth. A value below 100% retains at least one legal edit for a nonempty clip;
100% sets that clip's budget exactly to zero. The configured ranges are:

| Preset | Per-clip edits | Total edits | Change fraction | Candidate notes / pitches | Beam / depth | Coordinated pool | Full-pair evaluations |
|---|---:|---:|---:|---:|---:|---:|---:|
| Minimal | 0–2 | 0–2 | 12.5–25% | 4–8 / 4–6 | 4–8 / 2–4 | 1–2 | 400–800 |
| Balanced | 0–4 | 0–8 | 35–60% | 6–10 / 8–10 | 6–10 / 2–8 | 2–4 | 1,200–2,000 |
| Creative | 0–8 | 0–16 | 50–100% | 8–14 / 18–20 | 8–14 / 4–16 | 4–8 | 2,500–5,000 |

The upper endpoints apply at 0% preservation. Creative retains its full nearby,
octave, and bounded local-harmony pitch vocabulary and can evaluate
coordinated same-side pairs plus deterministic larger prefixes. MIDI safety
rules still reject illegal or structurally destructive candidates.

Legacy one-sided preset budgets remain compatible with V0.2. Presets are
deterministic and never imply that the highest score is the only valid musical
choice.

## Candidate presentation

Each retained candidate shows:

- preset and configured A/B preservation
- original/repaired estimated compatibility and improvement
- A/B/total notes changed
- A/B configured preservation and actual retention
- total pitch displacement
- exact A edits and exact B edits

The piano roll distinguishes unchanged notes, revised A/B notes, and aligned
original ghosts. The timeline compares complete before/after pair analyses.
The compact compatibility control keeps the estimate action, overall score,
and analysis-details toggle together. Detailed keys, component scores,
timeline, and reasons are collapsed by default above the main workspace.

## Export contract

### Revised A and revised B

Patch only intended note-on/note-off pitches in each original MIDI template.
Unrelated messages and delta times remain intact. A zero-edit revised file is
semantically identical to its source. Neither loaded source may be overwritten.

### Combined preview

Write a type-1 MIDI with revised A and B on separate named tracks. Rescale
different PPQ values exactly using their least common multiple when within the
SMF limit. Effective tempo and time-signature maps must agree; otherwise fail
clearly. Each clip is flattened to one preview track; an ambiguous overlapping
equal-pitch/channel pair from different source tracks is rejected. The preview
normalizes effective tempo/meter transitions and does not include source
controllers, programs, markers, or SysEx.

### JSON change report

Write version `0.3.0`, strategy, preset, before/after scores, per-clip source
name, preservation, retention, edit count, and traceable note records including
note ID, track, channel, pitches, onset, and duration. Serialization is
deterministic UTF-8 JSON with finite numeric values.

All four bundle destinations are preflighted, staged, reopened/validated, and
then promoted. Existing outputs require explicit overwrite approval. Promotion
uses four sequential filesystem replacements, so it is not transactionally
atomic if an operating-system failure occurs during that final step.

## Validation fixtures

In addition to V0.1/V0.2 regression fixtures, V0.3 includes:

- shared-better-than-one-sided
- preservation-bias
- both-locked
- unison-collapse risk
- coordinated same-side improvement
- dual-export

Tests cover determinism, complete-pair rescoring, per-preset bounds, 100% hard
locks, edit allocation, collision/unison safeguards, pitch-only invariants,
strict Minimal/Balanced/Creative edit ladders, preservation-dependent Creative
aggressiveness, non-greedy coordinated same-side improvements,
source-preserving export, combined-preview tracks, JSON completeness, GUI
preservation shortcuts and automatic lock indicators, single-search repair,
deterministic balance suggestions, and offscreen end-to-end export.

## Current limitations

GLUE remains MIDI-only, pitch-repair-only, deterministic, globally
major/natural-minor focused, and limited in local harmony vocabulary. Its
repeated-note heuristic is not general motif recognition. Search is bounded and
runs on the GUI thread, so it may miss an improvement outside its frontier and
blocks interaction while running. The GUI shows an indeterminate busy indicator
but has no detailed progress or cancellation. Balance suggestion is heuristic
and may return a low-confidence 50% / 50% fallback rather than a directional
recommendation. Dense searches may exhaust the shared evaluation ceiling before
every later frontier branch is expanded. Same-side bundles inspect only a
bounded high-priority subset, and their safe sequential collision check can
conservatively reject an otherwise valid simultaneous pitch swap.
Combined previews flatten source tracks and normalize shared timing metadata as
described above. It is not a DAW plugin or AI music generator.
