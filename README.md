# GLUE V0.5 Prototype

GLUE is a deterministic, preservation-first MIDI analysis and repair tool. Its
**Polish One Clip** workflow reviews possible inconsistencies inside one
Standard MIDI File. Its established **Combine Two Clips** workflow explains
where two files may compete and proposes bounded musical changes.

GLUE keeps both workflows separate behind two persistent buttons at the top of
the window. **Combine Two Clips** opens by default. It remains a
standalone desktop prototype with no cloud services, accounts, telemetry, AI
calls, or network features. Scores, chord labels, and repair suggestions are
transparent estimates, not objective musical diagnoses.

## New in V0.5

The desktop Generate buttons now use one shared passage-repair engine for
pitch, optional onset movement, and optional duration changes. **Pitch is on;
Timing and Duration are off** until explicitly enabled, independently for each
clip. Presets never change those permissions. Both pair preservation sliders
still start at 100%; quick balance remains 100:0, 50:50, and 0:100.

Sequence harmony uses duration/accent/bass evidence and Viterbi inference over
triads, sevenths, suspended chords and supported dominant resolutions. Phrase,
contour, motif, metric, ornament, voice-leading and rhythmic evidence feed a
bounded beam search that compares complete passages and full clip pairs.
Intentional chromaticism and syncopation are not automatically mistakes.

Up to three distinct improving alternatives are available in a compact
selector. **Change inspector** exposes exact pitch/onset/duration changes and
qualified reasons. Advanced component scores and calibration JSON remain
collapsed. The new musical-fit estimate includes rhythm and structure and is
not directly comparable to the separate, legacy compatibility estimate.

See [V0.5 design and validation](docs/V05_IMPLEMENTATION.md) and
[musical fixtures](docs/V05_FIXTURES.md). Existing V0.4 public pitch-only repair
APIs and command-line smoke options remain supported for regression testing.

## What works

- Load type-0 and type-1 MIDI while retaining each source event stream for
  preservation-first export.
- Analyze one clip for possible harmonic, melodic, voice-leading, overlap,
  register, bass, and repeated-motif inconsistencies. Suggestions include
  stable locations, confidence, neutral explanations, and pitch alternatives.
- Review, enable, or disable individual single-clip suggestions. Conservative
  high-confidence suggestions are enabled by default, while lower-confidence
  items remain available in a collapsed secondary section.
- Generate preservation-aware Minimal, Balanced, or Creative single-clip
  repairs. Creative evaluates bounded coordinated multi-note and multi-field changes.
- Compare original/repaired piano rolls, exact edits, internal consistency
  estimates, and the search stop reason; export a source-preserving repaired
  MIDI or optional advanced JSON report.
- Estimate duration-weighted major/natural-minor keys, expose ambiguity, and
  infer a time-varying harmonic sequence with confidence and alternatives.
- Score and explain harmonic, bass/root, register, and attack-rhythm
  compatibility using centralized deterministic weights.
- Generate Minimal, Balanced, and Creative pitch-repair candidates from one
  pair of independent A/B preservation values. The repair engine considers
  edits to every permitted clip from one bounded frontier and rescores every
  complete A+B pair.
- Treat 100% preservation as an automatic hard zero-edit constraint. Values
  below 100% permit authorized edits while increasing their cost as preservation
  rises. At 0%, ordinary preservation/displacement penalties disappear, but
  motif, contour, groove and MIDI safety constraints remain active.
- Offer **Keep A**, **Balanced**, and **Keep B** as value shortcuts, not repair
  modes, while leaving both preservation sliders freely adjustable afterward.
- Suggest a preservation balance from cached conflict analysis without running
  several full repairs. The suggestion is previewed with a concise reason and
  changes the sliders only when explicitly applied; uncertain cases say so and
  fall back to 50% / 50%.
- Penalize pitch displacement, local contour disruption, partial exact
  repeated-note changes, new same-voice collisions, unnecessary unison
  convergence, and loss of line independence.
- Retain candidates from requested preservation/preset settings and show
  estimated before/after compatibility, A/B edit counts, retention,
  displacement, and exact edits.
- Show original notes, separate A/B changed-note ghosts, and aligned
  before/after compatibility timelines.
- Export revised A, revised B, a separate-track combined-preview MIDI, and a
  deterministic JSON change report. Source paths and existing outputs are
  protected unless overwrite is explicitly confirmed.
- Report malformed, truncated, empty, and incomplete-note MIDI clearly while
  surfacing nonfatal parser warnings.

## Setup and run

Requirements are 64-bit Python 3.11 or newer and Windows 10/11. In PowerShell:

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m glue
```

If the Windows `python` alias is unavailable, create the environment with
`py -3.11 -m venv .venv`, then use `.\.venv\Scripts\python.exe` explicitly.
The optional `start_windows.ps1` script performs environment setup and tests.

## Desktop workflows

Top-level **Combine Two Clips** and **Polish One Clip** buttons switch the main
workspace without an intermediate screen. Combine mode is selected initially,
and switching does not discard either workflow's loaded state.

### Polish One Clip

1. Load one MIDI file.
2. Review the detected suggestions and enable only the changes you want the
   search to consider. Low-confidence suggestions are secondary and disabled
   by default.
3. Set preservation from 0–100% and choose Minimal, Balanced, or Creative.
   At 100%, repair is hard-locked to zero edits.
4. Set edit permissions and generate bounded alternatives. Analysis is cached and need not be run
   manually first.
5. Inspect the before/after rolls, exact authorized edits, estimated musical-fit
   improvement, and stop reason.
6. Export the repaired MIDI. JSON is under **Advanced exports / musical evidence**.

An unchanged search outcome is explained and is not offered as a successful
repair. Short stepwise chromatic notes are treated conservatively so an
intentional passing tone is not automatically removed.

### Combine Two Clips

1. Load MIDI A and MIDI B.
2. Set Preserve A and Preserve B directly, optionally starting from **Keep
   A**, **Balanced**, or **Keep B**.
3. Optionally select **Suggest balance** to preview an analysis-based
   recommendation, then explicitly apply it or keep the current values.
4. Choose Minimal, Balanced, or Creative, set edit permissions, and generate
   alternatives for the current preservation values. Manual estimation is optional.
5. Inspect the compact before/after estimate, exact A/B edits, and note ghosts,
   then export an individual artifact or all four artifacts from one base name.
6. Expand **Analysis details** when keys, component scores, timeline, and
   qualified conflict reasons are useful.

The compact compatibility group keeps **Estimate compatibility**, its overall
score, and **Show analysis details** together above the repair workspace.
Detailed analysis is collapsed by default and does not reserve permanent
central space.

The interactive window starts with both clips at 100% preservation. A slider at
100% shows an automatic **Locked** indicator and that clip receives zero edits;
lowering it below 100% makes the clip editable again. If both values are 100%,
repair is disabled with an explanation. There is no separate editing-strategy
selector or manual lock state.

Minimal has the smallest joint budget, candidate pool, pitch neighborhood, and
search depth. Balanced expands all four. Creative expands them again, can use
local-harmony targets, and at low preservation evaluates bounded coordinated
same-side note bundles. Per-clip edit budgets and search breadth grow
progressively as preservation falls. Timing and duration can change only with
explicit permission; velocities, channels, controllers and tempo never change.

The joint optimizer is not “repair A, then repair B.” Every search child is a
complete candidate pair, analyzed canonically as revised A plus revised B. A
small bounded A×B expansion also captures coupled edits that only help when
applied together. Bounded same-side bundles also expose coordinated note
changes whose isolated edits do not improve the estimate. The desktop runs
this optimizer once for the current slider values; it does not solve three
strategy variants to recommend a balance.

## Export artifacts

Polish mode's primary artifact is one repaired MIDI based on the original
source template. Only approved note pitches and bound note-event times change.
An optional deterministic JSON report includes reasons and calibration scores.

Combine mode retains its four artifacts:

| Artifact | Contents |
|---|---|
| Revised A | Original event stream with only authorized note pitch/onset/duration changes |
| Revised B | Original event stream with only authorized note pitch/onset/duration changes |
| Combined preview | Type-1 MIDI retaining both clips' separate original tracks and events |
| JSON report | Version, permissions, preset, component scores, preservation and per-note reasons |

The combined preview accepts differing PPQ values when they can be rescaled
exactly. It rejects incompatible effective tempo or time-signature maps rather
than misrepresenting either clip.

## Generate deterministic fixtures

The generator writes only to the explicit destination and never changes
`sample_data/`:

```powershell
python scripts\generate_fixtures.py --output-dir .generated-fixtures
```

| Purpose | MIDI A | MIDI B |
|---|---|---|
| Same-key compatible control | `demo_same_key_a.mid` | `demo_same_key_clean_b.mid` |
| Same-key local conflict | `demo_same_key_a.mid` | `demo_same_key_conflict_b.mid` |
| Progressive preset repair | `demo_preset_context.mid` | `demo_preset_source.mid` |
| Shared advantage / dual export | `shared_better_a.mid` | `shared_better_b.mid` |
| Preservation allocation | `preservation_bias_a.mid` | `preservation_bias_b.mid` |
| Coordinated same-side repair | `coordinated_same_side_a.mid` | `coordinated_same_side_b.mid` |
| Unison-collapse safeguard | `unison_collapse_a.mid` | `unison_collapse_b.mid` |

Dedicated aliases also exist for the both-locked and dual-export test cases.

## Automated GUI smoke tests

Exercise the V0.5 desktop buttons, five repair types, export/reload, screenshots
and a bounded-search profile (choose a fresh output directory on each run):

```powershell
python -m scripts.validate_v05 --output-dir .test-tmp\v05-smoke --profile
```

The commands below intentionally exercise the retained V0.4 pitch-only APIs.

Run a complete single-file workflow, including repaired-MIDI and advanced JSON
export:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
$env:QT_OPENGL = "software"
python -m glue --smoke-test `
  --single-file .generated-fixtures\single_obvious_accidental.mid `
  --single-preservation 0 `
  --single-preset minimal `
  --single-export .generated-fixtures\single-repaired.mid `
  --single-export-report .generated-fixtures\single-changes.json
```

The backward-compatible one-sided pair workflow remains available:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
$env:QT_OPENGL = "software"
python -m glue --smoke-test `
  --file-a .generated-fixtures\demo_preset_context.mid `
  --file-b .generated-fixtures\demo_preset_source.mid `
  --export .generated-fixtures\minimal-repaired.mid
```

A complete pair workflow can export all four artifact types. The command-line
`--strategy` option is retained for backward compatibility even though the
desktop no longer exposes strategy modes:

```powershell
python -m glue --smoke-test `
  --file-a .generated-fixtures\dual_export_a.mid `
  --file-b .generated-fixtures\dual_export_b.mid `
  --strategy shared --preserve-a 85 --preserve-b 85 `
  --export-a .generated-fixtures\shared-a.mid `
  --export-b .generated-fixtures\shared-b.mid `
  --export-combined .generated-fixtures\shared-preview.mid `
  --export-report .generated-fixtures\shared-changes.json
Remove-Item Env:QT_QPA_PLATFORM, Env:QT_OPENGL
```

## Architecture

```text
src/glue/models/     immutable MIDI domain models
src/glue/io/         parsing, template-preserving MIDI I/O, combined previews
src/glue/analysis/   cached sequence harmony, phrase/motif/context evidence; legacy analysis
src/glue/fixes/      shared bounded musical passage search; legacy pitch-only APIs
src/glue/exporting.py staged pair export and deterministic report serialization
src/glue/single_exporting.py source-preserving single MIDI and JSON export
src/glue/musical_exporting.py V0.5 staged exports, rollback-capable bundles, calibration JSON
src/glue/ui/         PySide6 orchestration and visualizations only
scripts/             deterministic, copyright-free fixture generation
tests/               unit, regression, integration, GUI, and end-to-end coverage
```

The analysis, repair, and export layers do not import the GUI.

## Known limitations

- MIDI only: no audio audition, WAV analysis, live MIDI ports, DAW control, or
  VST/AU plugin formats.
- Repair never creates/deletes notes or changes velocity, channels, controllers
  or tempo. Timing and duration are optional, bounded and off by default.
- Key likelihood still uses major/natural-minor profiles. Sequence harmony
  uses eight candidates per frame, at most 128 frames, and heuristic confidence;
  rapid changes, unusual modes and dense polyphony remain difficult.
- Clips are compared at beat-zero alignment; there is no offset detection,
  warping, or automatic quantization.
- Joint repair is explicitly bounded and runs on the GUI thread. The window
  shows an indeterminate busy indicator, but there is no detailed progress or
  cancellation and dense clips can take noticeable time. An improvement
  outside the beam/search limits may be missed. Dense searches can exhaust the
  shared evaluation ceiling before every later frontier branch is expanded.
- Coordinated bundles inspect a bounded subset and validate final states. Some
  coordinated solutions remain outside the shortlist/beam. Movement cannot
  extend beyond the original track end; imported ambiguous overlaps are conservative.
- Voice identity uses track/channel and pitch rank. Motif recognition uses
  bounded four-attack patterns, not general musical understanding.
- Balance suggestion is an analysis-only heuristic. Ambiguous evidence returns
  an honest low-confidence 50% / 50% fallback rather than testing repairs or
  claiming a strong directional recommendation.
- New combined previews retain original tracks and events. Clips using equal
  channel numbers may share instrument/controller state in a downstream player.
  Incompatible tempo/meter maps are rejected. Legacy CLI previews keep their
  original two-track, note-only contract.
- V0.5 bundles stage every artifact and roll back ordinary publication errors.
  A process crash or an OS failure during rollback cannot be made transactional.
- Compatibility weights and edit penalties still need validation against real
  producer material.
- Single-clip harmony, voice-leading, and motif detectors are bounded
  heuristics. They can miss context or surface intentional tension; confidence
  tiers and explicit suggestion selection keep producer judgment primary.

V0.5 is deterministic MIDI analysis and controlled repair—not a DAW plugin and not
an AI music generator.
