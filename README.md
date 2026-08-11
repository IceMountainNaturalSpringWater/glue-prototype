# GLUE V0.4 Prototype

GLUE is a deterministic, preservation-first MIDI analysis and repair tool. Its
**Polish One Clip** workflow reviews possible inconsistencies inside one
Standard MIDI File. Its established **Combine Two Clips** workflow explains
where two files may compete and proposes compatible pitch-only changes.

V0.4 keeps both workflows separate behind two persistent buttons at the top of
the window. **Combine Two Clips** opens by default. It remains a
standalone desktop prototype with no cloud services, accounts, telemetry, AI
calls, or network features. Scores, chord labels, and repair suggestions are
transparent estimates, not objective musical diagnoses.

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
  repairs. Creative can evaluate bounded coordinated multi-note changes.
- Compare original/repaired piano rolls, exact edits, internal consistency
  estimates, and the search stop reason; export a source-preserving repaired
  MIDI or optional advanced JSON report.
- Estimate duration-weighted major/natural-minor keys, expose ambiguity, and
  analyze simultaneous one-beat windows.
- Score and explain harmonic, bass/root, register, and attack-rhythm
  compatibility using centralized deterministic weights.
- Generate Minimal, Balanced, and Creative pitch-repair candidates from one
  pair of independent A/B preservation values. The repair engine considers
  edits to every permitted clip from one bounded frontier and rescores every
  complete A+B pair.
- Treat 100% preservation as an automatic hard zero-edit constraint. Values
  below 100% permit pitch edits while increasing their cost as preservation
  rises. At 0%, ordinary edit, displacement, octave, contour, and motif
  penalties are removed while MIDI safety and line-independence guards remain.
  Rhythm editing remains disabled.
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
4. Generate one bounded repair. Analysis is cached and does not need to be run
   manually first.
5. Inspect the before/after rolls, exact pitch edits, estimated consistency
   improvement, and stop reason.
6. Export the repaired MIDI. JSON is available only under **Advanced Export**.

An unchanged search outcome is explained and is not offered as a successful
repair. Short stepwise chromatic notes are treated conservatively so an
intentional passing tone is not automatically removed.

### Combine Two Clips

1. Load MIDI A and MIDI B.
2. Set Preserve A and Preserve B directly, optionally starting from **Keep
   A**, **Balanced**, or **Keep B**.
3. Optionally select **Suggest balance** to preview an analysis-based
   recommendation, then explicitly apply it or keep the current values.
4. Choose Minimal, Balanced, or Creative and generate the one repair requested
   by the current preservation values. Compatibility is estimated
   automatically when needed.
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
progressively as preservation falls. All presets are deterministic; none
changes onsets, durations, velocities, channels, controllers, or tempo.

The joint optimizer is not “repair A, then repair B.” Every search child is a
complete candidate pair, analyzed canonically as revised A plus revised B. A
small bounded A×B expansion also captures coupled edits that only help when
applied together. Bounded same-side bundles also expose coordinated note
changes whose isolated edits do not improve the estimate. The desktop runs
this optimizer once for the current slider values; it does not solve three
strategy variants to recommend a balance.

## Export artifacts

Polish mode's primary artifact is one repaired MIDI based on the original
source template. It changes approved note-on/note-off pitches only. An optional
deterministic JSON change report is available under **Advanced Export**.

Combine mode retains its four artifacts:

| Artifact | Contents |
|---|---|
| Revised A | Clip A's source MIDI structure with only approved paired note pitches changed |
| Revised B | Clip B's source MIDI structure with only approved paired note pitches changed |
| Combined preview | Type-1 MIDI with revised A and B on two clearly named tracks |
| JSON report | Version, strategy, preset, scores, preservation/retention, and traceable per-note edits |

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
src/glue/analysis/   pair compatibility and conservative single-clip suggestions
src/glue/fixes/      bounded single-clip and joint-pair pitch search
src/glue/exporting.py staged pair export and deterministic report serialization
src/glue/single_exporting.py source-preserving single MIDI and JSON export
src/glue/ui/         PySide6 orchestration and visualizations only
scripts/             deterministic, copyright-free fixture generation
tests/               unit, regression, integration, GUI, and end-to-end coverage
```

The analysis, repair, and export layers do not import the GUI.

## Known limitations

- MIDI only: no audio audition, WAV analysis, live MIDI ports, DAW control, or
  VST/AU plugin formats.
- Repair is pitch-only. It never creates notes or changes rhythm, timing,
  velocity, channel, controller, or tempo data.
- Key estimation models one global major or natural-minor center. Local harmony
  is limited to diatonic triad/seventh candidates.
- Clips are compared at beat-zero alignment; there is no offset detection,
  warping, or automatic quantization.
- Joint repair is explicitly bounded and runs on the GUI thread. The window
  shows an indeterminate busy indicator, but there is no detailed progress or
  cancellation and dense clips can take noticeable time. An improvement
  outside the beam/search limits may be missed. Dense searches can exhaust the
  shared evaluation ceiling before every later frontier branch is expanded.
- Coordinated bundles inspect a bounded high-priority subset. Their sequential
  collision guard is safe but can conservatively reject a simultaneous pitch
  swap whose intermediate state would collide.
- Repeated-note consistency and counterpoint preservation use modest
  heuristics, not general motif recognition; producer judgment remains
  necessary.
- Balance suggestion is an analysis-only heuristic. Ambiguous evidence returns
  an honest low-confidence 50% / 50% fallback rather than testing repairs or
  claiming a strong directional recommendation.
- Combined previews flatten each clip's source tracks into one named preview
  track. Ambiguous overlapping equal-pitch/channel notes across source tracks
  are rejected rather than altered. Effective tempo/meter transitions are
  normalized, and source controllers, programs, markers, and SysEx are not
  included. Revised individual files preserve those source events.
- A four-file export is fully staged and validated before promotion, but the
  final four filesystem replacements are sequential rather than a
  transaction. A rare OS failure during promotion can leave a partial bundle.
- Compatibility weights and edit penalties still need validation against real
  producer material.
- Single-clip harmony, voice-leading, and motif detectors are bounded
  heuristics. They can miss context or surface intentional tension; confidence
  tiers and explicit suggestion selection keep producer judgment primary.

V0.4 is deterministic MIDI analysis and pitch repair—not a DAW plugin and not
an AI music generator.
