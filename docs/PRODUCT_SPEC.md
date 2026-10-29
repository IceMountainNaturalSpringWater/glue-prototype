# GLUE V0.5 Product Specification

## V0.5.4 recovery and diagnostic update

The GUI, permissions, movement bounds, preset edit/evaluation budgets and MIDI
export contract remain unchanged. Candidate scheduling now shares the fixed
budget across fields/notes, and at most four coherent short-line onset bundles
reuse existing generated options. Beam widths are not increased.

Musical continuity and retention both use inferred register-aware voice paths.
Competing-attack scoring requires interval tension or competing monophonic lines,
not coincidence alone. Compensating performed onset intervals and contextual
articulation ratios supply bounded evidence without global quantization.
Supported onset restoration is distinguished from ordinary groove damage.
Corroborated register/interval or motif evidence can permit octave correction
despite legato overlap; compact chord membership counters inappropriate revoicing.

New centralized objective terms are Performance rhythm (1.0), Contextual
articulation (0.5), and Octave context (1.0). Existing coefficients are unchanged.
Scores remain heuristic, not calibrated probabilities or listening judgments.

Reference-aware oracle/rank/margin diagnostics live only in the benchmark package;
production repair cannot import or receive ground truth. Report actual versus
oracle recovery separately, preserve locks in aggregate reports, and expose
unlocked results, false positives and runtime. See [V0.5.4 evidence](V054_REPAIR_QUALITY.md).

## V0.5.3 candidate-evidence update

The desktop contract below remains unchanged. Candidate evidence now uses
approximate register-aware voice paths, near-simultaneous attack grouping,
repeated four-note phrase analogues, local groove/pulse and relative articulation.
Separate bounded target pools per editable field prevent rhythm evidence from
displacing pitch targets. The maximum target pool per field remains 6/10/16 for
Minimal/Balanced/Creative at zero preservation; evaluation and edit-count ceilings
are unchanged. Per-note proposal caps are pitch 4/8/12, timing 2/4/6 and duration
2/6/8. Timing/duration movement limits and permission defaults are unchanged.

Intentional co-attacks alone do not justify timing movement. Global-key
disagreement alone does not override locally supported chord tones. Repeated
short neighbor figures and coherent voice contours receive additional protection;
polyphonic octave changes require stronger evidence. Scores and objective weights
are not broadly retuned. Up to eight linked multi-field proposals reuse the same
full-state validator and evaluation budget. See [V0.5.3 measurements](V053_CANDIDATES.md).

## V0.5 active contract: Advanced Musical Repair

V0.5 keeps Combine Two Clips as the initial tab and Polish One Clip as the
other persistent top-level tab. Loading, preservation shortcuts (100:0,
50:50, 0:100), optional cached compatibility estimation and explicit export
remain. No audio, live MIDI, DAW/plugin, cloud, telemetry or AI integration.

The desktop Generate buttons call the same deterministic musical repair
engine with one clip or a complete pair. Existing V0.4 public pitch-only APIs
and CLI smoke options retain their contracts. The baseline specification
below documents those older APIs; this section takes precedence for the V0.5
desktop and `generate_musical_repairs`.

### Permissions and preservation

- Each clip has independent Pitch, Timing and Duration permissions.
- Pitch defaults on; Timing and Duration default off for every preset.
- Preset selection never enables either timing permission silently.
- 100% preservation means zero edits to that clip. Both pair sliders start
  at 100%; both locked disables Generate with an explanation.
- Lower preservation increases note/edit/evaluation budgets and lowers
  ordinary edit cost. At 0% ordinary preservation penalties are zero, but
  motif, contour, groove and structural safety remain active.

### Musical evidence and harmony

Immutable cached analyses include meter strength, rest/cadence phrase
boundaries, contour, four-attack motifs/variations, independent rhythmic
repetition, density/syncopation, note overlaps, technical equal-pitch
collisions, bass movement and pitch-rank voice leading/parallel motion.
Stepwise passing/neighbor tones, prepared resolving suspensions, anticipations
and recurring chromatic material receive contextual protection. Non-diatonic
pitch alone is not sufficient evidence for a repair.

Harmony uses duration- and accent-weighted pitch evidence, bass/inversion
evidence and key likelihood. All roots are considered for major, minor,
diminished, dominant/major/minor seventh and suspended-second/fourth chords.
An eight-candidate-per-frame Viterbi sequence rewards continuity and supported
dominant resolution while considering voice-leading distance. Forward/backward
max-marginal confidence is heuristic, not a calibrated probability. Both
neighbors influence the final path. One-beat frames coarsen on long clips to
at most 128 frames; weak evidence retains alternative labels.

### Bounded passage optimization

Every valid searched state is a full modified clip or pair with complete
rescoring. Non-improving intermediate states may remain in the beam, and
coordinated same-measure bundles can cross single-edit objective barriers.
The optimizer includes harmony, resolution, melodic continuity, voice leading,
bass movement, rhythmic complementarity, register, unisons/collisions, weak
motif-consistency evidence, relative motif/contour/groove retention, and weighted
edit/displacement/preservation costs. Weights live in `musical_config.py`.

| Maximum at 0% preservation | Minimal | Balanced | Creative |
|---|---:|---:|---:|
| Edited notes per editable clip | 2 | 4 | 8 |
| Candidate-note pool per clip | 6 | 10 | 16 |
| Ordinary pitch radius, semitones | 2 | 4 | 7 |
| Beam width / search rounds | 4 / 2 | 7 / 3 | 10 / 4 |
| Complete state evaluations, including baseline | 100 | 220 | 420 |
| Onset displacement, quarter-note beats | 0.125 | 0.25 | 0.5 |
| Duration displacement, quarter-note beats | 0.125 | 0.5 | 1.0 |
| Duration displacement, fraction of original | 25% | 50% | 75% |

High-confidence octave-error candidates can use a 12-semitone correction.
Timing and duration limits always apply relative to the original source,
not cumulatively per search step. Both duration bounds must hold. Shifts use
musical subdivisions while preserving the source's off-grid offset; integer
tick checks avoid rounding drift. Minimal timing/duration edits require
explicit permission and technical collision evidence. Other presets may
separate competing attacks, trim sustained clashes or close an isolated small
gap in an otherwise legato line. They do not freely quantize or normalize it.

Only candidates improving both estimated musical cost and the retention-aware
objective are presented. Unchanged/no-improvement outcomes cannot be exported
as repairs. Up to three non-dominated, differing note/field alternatives are
retained; gratuitous extra edits and near-duplicate signatures are excluded.

### UI, rationale, exports and calibration

Repair stays primary. Permissions and alternatives are compact; the change
inspector and advanced evidence/export panel start collapsed. Single-clip
suggestion opt-outs remain respected for pitch edits. Piano-roll ghosts
represent pitch, onset and duration differences. The optional compatibility
button stays adjacent to its overall score and collapsed analysis details;
running it does not discard an existing musical repair.

Every changed note records source/revised pitch, onset, duration, ownership and
qualified reasons. Musical-fit estimates are labeled separately from legacy
compatibility and must not be compared as the same metric. JSON calibration
reports include component scores, weights, preservation, permissions, reasons,
search budget outcome and a future human-rating field.

Export updates paired source note events and reconstructs delta times while
preserving all unrelated events at their absolute ticks. No note is created
or removed; pitches stay in 0–127, changed durations are positive, and new
same-track/channel/pitch overlaps or motion beyond source track ends are
rejected. Imported unchanged zero-length notes retain their event pairing.
Velocity, release velocity, channels, tempo, controllers, programs, SysEx and
other source events remain unchanged. Outputs are staged and reloaded for
semantic validation, with source-path protection and explicit overwrite.
Combined previews preserve original tracks/events at an exact shared PPQ and
reject incompatible tempo/meter maps. Four-artifact bundles are staged before
publication and roll back ordinary publication failures.

Producer ratings and listening validation remain necessary. See
[implementation and validation](V05_IMPLEMENTATION.md) and
[musical fixtures](V05_FIXTURES.md) for limitations and reproducible checks.

## V0.4 baseline reference

## Problem

Producers may need either to reconcile two MIDI ideas that compete when layered
or to polish possible inconsistencies inside one MIDI idea. GLUE diagnoses
existing material and proposes bounded pitch-only changes rather than
generating replacements. Its scores and suggestions are interpretable
estimates with reasons and ambiguity, never claims of objective musical
correctness.

## V0.4 scope

GLUE V0.4 is a deterministic standalone MIDI analysis and pitch-repair
prototype with two separate workflows:

- **Polish One Clip** reviews and selectively repairs one MIDI file.
- **Combine Two Clips** retains the complete V0.3 compatibility and joint
  repair workflow.

It has no audio processing, live MIDI, DAW integration, plugins, cloud
services, LLM calls, accounts, telemetry, or network features.

## Workflow switcher

Persistent **Combine Two Clips** and **Polish One Clip** buttons sit at the top
of the application. Combine mode is selected initially. Each workflow retains
its loaded state when the user switches between them, without an intermediate
chooser page. The analysis, repair, and MIDI-writing layers remain independent
from this navigation.

## Polish One Clip workflow

1. Load one type-0 or type-1 MIDI file without modifying the source.
2. Review deterministic suggestions. High-confidence suggestions are enabled
   by default; lower-confidence suggestions remain available in a collapsed
   secondary section.
3. Enable or disable individual suggestions, or select/clear the lists.
4. Set preservation from 0–100% and select Minimal, Balanced, or Creative.
   A value of 100% is a hard zero-edit constraint.
5. Generate one bounded repair using only enabled suggestions. Every candidate
   is a complete modified clip and receives a fresh complete single-clip
   analysis.
6. Inspect exact edits, before/after piano rolls, estimated internal
   consistency, improvement, and the search stop reason.
7. Export the repaired MIDI. Deterministic JSON is optional and appears only
   under **Advanced Export**.

Repair is usable immediately after loading because analysis runs automatically
and is cached by immutable clip content. Preservation, preset, selection,
resizing, and workflow navigation do not repeat unchanged analysis.

## Combine Two Clips workflow

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

## Single-clip analysis

The single-clip API deterministically estimates a global major or natural-minor
key and returns a qualified internal-consistency score plus note-addressable
suggestions for possible:

- global-key or local-harmony conflicts,
- awkward melodic leaps or resolutions,
- weak chord voice leading,
- duplicate or overlapping notes,
- chord/register crowding,
- bass conflicts,
- inconsistencies in repeated motifs.

Each suggestion includes a stable ID, affected note and tick/beat location,
category, confidence, neutral explanation, related-note context, and bounded
absolute-pitch alternatives. Explanations use qualified wording such as
“Possible harmonic conflict.” They do not claim that a note is wrong.

Analysis is deliberately conservative around chromaticism. Short stepwise
passing or neighbor notes, suspensions, resolutions, and intentional tension
must not be treated as automatic edits. Low-confidence evidence is secondary
and disabled by default.

The internal-consistency estimate combines independently exposed harmony,
melody, voice-leading, overlap, register, bass, and motif component scores.
These heuristics are review aids, not measurements of objective musical
quality.

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

### Single-clip repair

Single-clip repair reuses the shared preset, pitch-edit, preservation, contour,
motif, collision, and bounded-search vocabulary. It does not simulate a pair
analysis with a duplicate or empty clip. A state contains the complete revised
clip, the accumulated edits, and a fresh single-clip analysis.

Only alternatives belonging to explicitly enabled suggestion IDs are eligible.
Disabling one suggestion cannot authorize the same note through a different
suggestion. New same-track/channel equal-pitch overlaps, percussion edits,
out-of-range pitches, changes larger than one octave, and every non-pitch edit
remain prohibited.

- **Minimal** considers a few high-confidence notes, a narrow pitch vocabulary,
  and the smallest edit/depth budget.
- **Balanced** considers a moderate candidate pool and coordinated changes.
- **Creative** uses the broadest but still bounded pool, pitch vocabulary,
  beam, depth, and multi-note bundles.

At lower preservation, ordinary edit, displacement, contour, and motif costs
fall while search budgets grow. At zero preservation those ordinary
preservation costs are removed, but MIDI safety rules remain. Creative may
accept a coordinated bundle whose complete result improves even when its
isolated edits do not. It does not accept a change merely to exhaust a budget.

An unchanged outcome is never presented as a successful repair. The result
instead explains a hard preservation lock, no enabled suggestions, or that no
valid pitch edit improved the estimate.

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

### Single repaired MIDI

Patch only approved paired note-on/note-off pitches in the loaded source
template. The exported file must reopen with the intended pitches while
retaining source PPQ, track structure, delta timing, note duration and velocity,
channels, tempo, meter, controllers, programs, sustain, markers, SysEx, and
other unrelated events. The loaded source path may never be overwritten.
Existing destinations require explicit overwrite approval.

The optional advanced single-clip JSON report writes version `0.4.0`, source
name, preset, preservation, before/after consistency estimates, stop reason,
enabled suggestion IDs, and traceable note edits. Serialization is
deterministic UTF-8 JSON.

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

Write version `0.4.0`, strategy, preset, before/after scores, per-clip source
name, preservation, retention, edit count, and traceable note records including
note ID, track, channel, pitches, onset, and duration. Serialization is
deterministic UTF-8 JSON with finite numeric values.

All four bundle destinations are preflighted, staged, reopened/validated, and
then promoted. Existing outputs require explicit overwrite approval. Promotion
uses four sequential filesystem replacements, so it is not transactionally
atomic if an operating-system failure occurs during that final step.

## Validation fixtures

The V0.4 single-clip catalog adds:

- obvious accidental
- intentional chromatic passing note
- awkward melodic leap
- poor chord voice leading
- duplicate overlap
- bass conflict
- repeated-motif inconsistency
- register crowding
- coordinated multi-note repair
- no-improvement material

Tests cover deterministic analysis/repair; complete suggestion records;
conservative chromatic handling; enabled-suggestion filtering; the 100% hard
lock; preservation and preset breadth; coordinated search; explicit
no-improvement outcomes; pitch-only invariants; source-preserving MIDI and
deterministic JSON export; overwrite protection; analysis caching; workflow
switching; and offscreen single/pair smoke workflows.

The retained V0.3 catalog includes:

- shared-better-than-one-sided
- preservation-bias
- both-locked
- unison-collapse risk
- coordinated same-side improvement
- dual-export

Pair regression tests cover determinism, complete-pair rescoring, per-preset bounds, 100% hard
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
Single-clip suggestions use bounded heuristics rather than general harmonic,
counterpoint, or motif understanding. Dense single repairs can miss an
improvement outside the configured candidate pool, beam, or coordinated
bundles. Analysis cannot reliably distinguish every intentional chromatic note
from an accidental; confidence, default-disabled secondary suggestions, and
producer selection are the safeguards.

Combined previews flatten source tracks and normalize shared timing metadata as
described above. GLUE is not a DAW plugin or AI music generator.
