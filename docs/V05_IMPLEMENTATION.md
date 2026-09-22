# GLUE V0.5 implementation and validation

## Outcome and compatibility

V0.5 adds a shared deterministic musical repair engine to both existing desktop
workflows. Combine Two Clips remains the initial tab. Pitch is enabled by
default; Timing and Duration require explicit independent permission per clip.
There are no new dependencies, audio features, network services or AI APIs.

The starting V0.4 baseline had **234 passing tests**, clean Ruff and a passing
GUI launch smoke test. Its public pitch-only APIs and CLI smoke paths remain
available and covered. New desktop Generate buttons return musical candidates;
call `repair_musical()` for this result model. Older `repair_selected()` /
`generate_repair()` calls deliberately retain their V0.4 result/export contracts.
The V0.5 musical-fit estimate is a different metric from optional legacy
compatibility/internal-consistency estimation; the GUI labels them separately.

Two existing GUI tests were adapted to exercise the retained legacy API/panel
explicitly, because the default button and unused-result layout changed.
Their previous assertions were retained; new end-to-end tests cover the new
button route. Version assertions now expect 0.5.0. No tests were deleted.

## Algorithms and architecture

| Layer | Implementation |
|---|---|
| Musical evidence | `analysis/musical.py`: cached phrase, contour, metric, motif/variation, rhythmic repetition, ornament/resolution, overlap, bass and voice-motion evidence |
| Harmony | Duration/accent/bass/key-weighted candidates; eight-state Viterbi sequence, neighboring voice-leading/continuity costs, seventh/suspended chords, inversions and supported dominant resolutions; confidence and alternatives retained |
| Cross-part chord support | A cached event sweep recognizes complete sustained chord shapes across files, preventing legitimate shared seventh/suspended voicings from becoming isolated semitone-clash targets |
| Search | `fixes/musical.py`: one bounded beam for one clip or a pair; full-state rescoring, non-improving intermediates and coordinated measure-local bundles; structural rejection before expensive scoring |
| Objective | Central `musical_config.py` weights for harmony, resolution, melody, voice leading, bass, rhythm, register, motif consistency/retention, contour, groove, collisions/unisons, displacement and preservation |
| Export | `io/edited.py` reschedules bound source events; `musical_exporting.py` stages, reloads and validates MIDI, JSON and combined/bundle artifacts |
| GUI | Shared `musical_controls.py`; existing tabs/loaders/preservation/preset controls retained; compact alternatives and collapsible inspector/calibration details |

Search budgets differ meaningfully: Minimal/Balanced/Creative allow at most
2/4/8 changed notes per editable clip, 6/10/16 candidate notes, ordinary pitch
radii of 2/4/7 semitones, beams of 4/7/10, 2/3/4 rounds and 100/220/420 complete
state evaluations. High-confidence octave-error correction remains possible.
Budgets contract as preservation increases. 100% is a hard lock; at 0%
ordinary preservation costs are zero, but structure is still protected.

New safeguards reject complete contour flattening, major motif destruction,
and new convergence of distinct multi-note parts into one doubled line.
Candidates must improve both musical cost and the retention-aware objective.
Non-dominated alternatives are filtered by note/field diversity; extra edits
without additional benefit do not create an alternative. Unchanged results
are explained and cannot be exported as successful repairs.

## Pitch, timing and duration

- Pitch edits retain source note identity, velocity, release velocity, track
  and channel. Contextually resolving chromatic notes are protected.
- Timing is opt-in. Minimal requires technical collision evidence; Balanced
  permits at most 0.25 quarter-note beats and Creative at most 0.5. Shifts retain
  the original off-grid offset instead of quantizing the performance.
- Duration is opt-in. Maximum absolute changes are 0.125/0.5/1.0 beats and
  relative changes 25%/50%/75%, respectively. Both bounds apply. Technical
  overlaps, cross-part sustain clashes and isolated gaps in otherwise legato
  lines provide evidence; note lengths are never globally normalized.
- Changed durations stay positive; timing is bounded relative to the original
  note and cannot move beyond the original track end. Imported unchanged
  zero-length notes keep their on/off order.
- New ambiguous equal-pitch overlaps are rejected. MIDI exports preserve
  unrelated absolute event positions, including tempo, meter, controllers,
  programs, markers, pitch wheel, aftertouch and SysEx.

## Demonstrated examples

These are heuristic musical-fit estimates, not listening judgments. Examples
use 0% preservation on the editable clip and the stated explicit permissions.

| Example | Actual retained change | Before → after |
|---|---|---:|
| Pitch only | F#5 → G5; all non-pitch data unchanged | 93.2 → 100.0 |
| Timing only | Three B attacks move later by 0.5 beat; pitches/durations retained | 66.3 → 100.0 |
| Duration only | B's C#4 sustain: 1.0 → 0.25 beats | 92.9 → 98.1 |
| Coordinated pitch + timing | B F#4 → E4 plus two 0.5-beat onset shifts | 70.8 → 100.0 |
| Coordinated pitch + duration | B C#4 → D#4 and sustain 1.0 → 0.25 beats | 92.9 → 100.0 |
| Intentional material | Passing chromaticism, resolving suspension and syncopated repetition retained | Zero edits |

Additional tests repair the isolated repeated-motif alteration, close one
0.125-beat legato gap, retain a seventh chord split across two files, and prove
that Minimal edits fewer notes than Balanced and Balanced fewer than Creative
on the broader-edit fixture. A deliberate score barrier tests that the search
does not require every intermediate edit to improve the score.

## UI behavior

The permissions header and checkboxes fit the single-clip pane without
truncation; the repair result precedes the suggestion list. The piano roll
highlights pitch, timing and duration changes and preserves its existing pitch
labels/contrast/scrolling behavior. Actual font-rendered screenshots were
inspected for both workflows.

Alternative selection updates the preview, field counts and rationale.
Per-note reasons are available in the expandable tree, with full tooltips for
long text. Advanced component evidence and exports are collapsed. Individual
MIDI, combined preview, JSON and four-artifact bundle export remain available.
The compatibility button, overall score and analysis-details toggle remain
together; optional estimation does not discard a selected musical candidate.
Permission/preset/preservation/source changes invalidate stale candidates.

## Performance

Measurements are local engineering observations, not a latency guarantee:

- Five small GUI-button examples: approximately **0.01–0.06 seconds** each.
- A 28-note Creative pitch-search fixture: **420 states**, about **0.8–1.0 s**.
- A 112-note / 32-beat synthetic case: **420 states**, about **4.9 s**.
- The profiled 28-note case spends most time in complete musical rescoring,
  especially harmonic frame-candidate scoring. Profiling overhead raises its
  elapsed time to roughly 2.9 s. Original-context/key reuse and cached
  chord-to-chord distances remove redundant analysis work.

The old three-strategy recommendation pattern is not reintroduced: one
requested search generates alternatives. Full-state caches prevent duplicate
state evaluation within a run. Harmony sequences cap at 128 frames, the note
pool and movement alternatives are limited, and the beam/evaluation ceiling
terminates expensive searches with an explicit explanation.

## Validation and reproduction

Final validation: **272 tests passed in 28.64 s** (234 baseline cases plus 38
new cases), Ruff passed, and `git diff --check` passed. Git emitted only its
normal LF/CRLF conversion notices, not whitespace errors. `python -m glue
--smoke-test` launched successfully with both pair sliders at 100%. The V0.5
single/pair GUI-button smoke, all five repair demonstrations, export/reload,
combined and bundle export, intentional-material controls, and profiling passed.
The final artifact set is under `.test-tmp/v05-review/`.

No regressions were detected in retained V0.4 API/export coverage. The new
desktop result model and musical-fit objective are intentional behavior changes,
not numerically identical replacements for the legacy compatibility metric.

Use the existing environment, or install the unchanged declared requirements:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m glue
```

Validation commands (use a fresh smoke output directory):

```powershell
.\.venv\Scripts\python.exe -m pytest --basetemp .test-tmp\v05-tests
.\.venv\Scripts\python.exe -m ruff check .
git diff --check
.\.venv\Scripts\python.exe -m glue --smoke-test
.\.venv\Scripts\python.exe -m scripts.validate_v05 --output-dir .test-tmp\v05-smoke --profile
```

The complete suite includes V0.4 regressions, context/harmony fixtures,
deterministic/multi-step/preset search, hard preservation and permissions,
MIDI event safety, export/reload, overwrite/source protection, combined-event
preservation, bundle rollback, GUI button/selection/invalidation, no-improvement
messaging, and piano-roll pitch-label tests. Validation artifacts under
`.test-tmp/` include MIDI/JSON files, screenshots and a cProfile report; they
are intentionally untracked.

## Known limitations and remaining calibration

- Musical diagnoses and confidence are deterministic heuristics. No producer
  listening study was performed; audibly beneficial repairs are not proven by
  higher fixture scores. Human ratings/weight calibration remain necessary.
- Voice identity is track/channel plus pitch rank, not general polyphonic
  voice separation. Phrase boundaries and four-attack motifs are modest
  heuristics, and long clips use coarser harmonic frames. Incomplete/extended
  jazz voicings, unusual modes and deliberate counterpoint can be ambiguous.
- Search is bounded and can miss improvements outside the source shortlist,
  coordinated bundle or beam. Single-clip timing is intentionally conservative;
  duration extension currently targets isolated legato gaps, not general
  articulation rewriting. No free quantization or note creation is implemented.
- Search remains synchronous on the GUI thread. A busy state blocks duplicate
  actions, but long searches lack cancellation/progress updates and can pause
  repainting. Larger/dense arrangements can take substantially longer.
- Files remain beat-zero aligned. There is no whole-clip alignment, swing
  inference, audio rendering or audition. Pedal/controller performance effects
  are preserved as MIDI events, not acoustically simulated during analysis.
- Combined files retain channels unchanged; equal channel numbers can share
  instrument/controller state in a downstream player. Conflicting tempo/meter
  maps are refused. Individual revised files are the faithful export choice.
- Bundle rollback handles ordinary publication failures, not process crashes
  or a second OS failure during rollback. Legacy CLI previews keep their older
  two-track, note-only semantics; new desktop previews preserve source tracks.

Highest-value next steps: producer ratings and calibration; cancellable worker
execution; richer polyphonic voice/phrase segmentation; incremental local
harmonic caching for large arrangements; and more style-diverse real-MIDI
regression fixtures with human-reviewed rationale.

## Every materially changed file

Documentation and version:

- `README.md`
- `docs/PRODUCT_SPEC.md`
- `docs/ROADMAP.md`
- `docs/V05_FIXTURES.md`
- `docs/V05_IMPLEMENTATION.md`
- `pyproject.toml`
- `src/glue/__init__.py`

Analysis, repair and export:

- `src/glue/analysis/musical.py`
- `src/glue/fixes/musical.py`
- `src/glue/fixes/musical_config.py`
- `src/glue/io/edited.py`
- `src/glue/musical_exporting.py`

GUI:

- `src/glue/ui/main_window.py`
- `src/glue/ui/musical_controls.py`
- `src/glue/ui/single_workflow.py`
- `src/glue/ui/visualizations.py`

Fixtures and validation tooling:

- `scripts/generate_v05_fixtures.py`
- `scripts/validate_v05.py`

Tests:

- `tests/test_edited_midi.py`
- `tests/test_gui_repair_focus.py`
- `tests/test_gui_v03.py`
- `tests/test_gui_v05.py`
- `tests/test_musical_analysis.py`
- `tests/test_musical_exporting.py`
- `tests/test_musical_repair.py`
- `tests/test_repair_export.py`
- `tests/test_scaffold.py`

No changes were made to `sample_data/`, outside the repository, or to Git
history. All implementation changes remain uncommitted for review.
