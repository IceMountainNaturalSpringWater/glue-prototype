# GLUE V0.5.3: contextual candidates and diagnostic comparison

## Scope and experimental discipline

This iteration changes candidate generation and voice evidence, not the GUI.
There are no new dependencies, network services, audio features or scoring-weight
sweeps. The V0.5.2 measurement snapshot remains intact. Its engine fingerprint is
`04e1428013ad46e2f3c0b2838429d5a841763db64a6ebf5221d7d16bc2c5df96`.

Development uses only the four calibration passages in each existing manifest.
V0.5.2's published held-out aggregate results were already known from the prior
task; individual held-out ground truth was not inspected to design these changes.
Final held-out measurements run only after the V0.5.3 engine is frozen. These are
still eight short passages per corpus, not broad musical validation.

The manifest, corruptions, seeds, note identities, presets and preservation
settings are unchanged: seed 52, 8-beat windows, all three presets, preservation
0/25/50/75/100, and explicit Pitch/Timing/Duration permission. Each corpus has four
calibration and four evaluation works. POP909 uses melody versus accompaniment;
MAESTRO uses expressive single-clip piano. Original references never enter repair.

## Algorithm changes

- Voice paths group near-simultaneous attacks within 1/32 beat, use monotonic
  pitch-order assignment, and consider recent register, pitch proximity, temporal
  gaps, overlap and direction. Voice identities expose approximate bass/inner/upper
  roles, register ranges and adjacent note IDs. They are not definitive hand labels.
- Larger non-octave moves also respect a stable voice's robust register, including
  phrase endpoints; small accidental corrections and isolated register-outlier
  corrections remain possible.
- Pitch proposals use voice neighbors/contour, sequence harmony and alternatives,
  possible extensions, ambiguous key/mode evidence, nearby passing possibilities,
  bass context and repeated/transposed four-note analogues. Existing intentional
  ornament protection remains. Recurring short voice-neighbor figures get additional
  protection, and global-key-only suggestions cannot override local chord support.
  Same-register alternatives precede octave options;
  polyphonic octave changes require stronger repeated-material evidence.
- Timing proposals use inferred subdivision phase, performed onset intervals,
  motif alignment and supported harmony boundaries. Ordinary small microtiming is
  retained. Simultaneous attacks alone do not authorize movement: pair proposals
  need dissonance, competing lines, technical overlap or linked phrase evidence.
- Duration proposals use voice release boundaries and local articulation relative
  to onset spacing, not just neighboring raw lengths. Longer notes preceding longer
  gaps are not automatically mistakes. Cross-part sustained conflicts can propose
  an explicit conflicting-attack boundary. Existing movement limits remain.
  Subdivision-based duration alternatives complement percentage endpoints only
  where sustain-conflict evidence already exists.
- Pitch, timing and duration have separate bounded target pools, preventing a
  timing anomaly from crowding every pitch target out of the shared pool.
- Deduplicated proposals retain provenance and per-field ranks. Developer traces
  include the complete bounded candidate set and inferred voice/register, including
  original unchanged values. Ground-truth presence is joined afterward.
  Here "original" in the engine trace means the supplied repair input (possibly
  corrupted), never the hidden clean benchmark reference.
- Up to eight evidence-linked multi-field bundles complement the existing local
  pairs. Full candidate clips/pairs are still validated and rescored. The existing
  search evaluation ceilings, edit-count limits, beam widths and score weights
  remain unchanged; no brute-force expansion or oracle selection is introduced.

AST comparison against the tracked original confirms that `score_passage` and
`_retention` remain unchanged. `musical_config.py` weights are unchanged. Improved
generation does not imply that the objective can recognize every better candidate.

## Development checks

The incoming snapshot passed 328 tests and Ruff. Early broad pitch proposals
failed existing intentional-chromatic/chord-preservation regressions; the proposal
gates were corrected and the original assertions retained.

Calibration trial 1 increased POP909 editable timing recall from 1.67% to 24.58%,
but pitch recall fell because rhythmic evidence displaced pitch targets. MAESTRO
clean octave changes disappeared, but new duration proposals increased false
positives. This motivated separate field pools and duration/IOI articulation
checks rather than weight tuning or benchmark-specific note corrections.

Intermediate development matrices remain in `.test-tmp/v053-calibration-1/` and
`.test-tmp/v053-calibration-2/` and `.test-tmp/v053-calibration-3/`; they are not the frozen final results. Intermediate
runtime may overlap regression tests; final measured matrices run sequentially.

Trial 2 increased POP909 editable pitch recall to 70.83% and timing recall to
24.58%, but MAESTRO clean false positives were still worse than the incoming
baseline. Traces showed locally supported chord tones changed because of global
key disagreement, recurring short neighbor figures flattened, and analogy-based
duration changes on small expressive differences. Candidate-side chord support,
voice ornament, contour and micro-articulation safeguards address those observed
patterns; no corpus names, file IDs or known reference pitches enter the engine.

Trial 3 still had one more clean MAESTRO edited-note observation than baseline
(30 versus 29). The stable-register endpoint safeguard was added before any
held-out measurement. Independent calibration clean controls then recorded 54
versus 85 POP909 edited-note observations and 28 versus 29 MAESTRO; zero clean
octave changes in both. Trial 3 reports were moved to the archive above, not erased.

## Final measurement and validation

An additional synthetic cross-process test found nondeterministic ordering of
otherwise tied candidate provenance labels. A final reason-string tie-breaker
fixes this without changing weights or musical rules. The first frozen matrix
was archived in `.test-tmp/v053-pre-tiebreak/` before inspecting its held-out
results, and the entire matrix was rerun on the corrected engine.

The frozen engine fingerprint is
`66e7374af98dc90556c96d64875d42803b7cea58f6b0a21149468cc7a9b98c53`.
The [freeze record](../benchmarks/baselines/v053-real/freeze.json) was written
before the corrected held-out evaluation, after calibration clean controls and all 342 tests
passed. No algorithm changes follow held-out inspection.

The final [separate corpus/split comparison](../benchmarks/baselines/v053-real/comparison-all.md)
and [machine-readable details](../benchmarks/baselines/v053-real/comparison-all.json)
include all settings, unlocked settings, each preservation level and each preset.
JSON additionally includes per-corruption recovery, scoring-gate examples and
usable-reference-field coverage. Generated recall is not the same as a valid
scored state: safety/movement constraints and search budgets may reject a proposal.

### Outcome: coverage improved, repair-quality acceptance not met

The implementation and frozen measurement are complete, but this is **not a
validated overall repair-quality improvement**. Held-out exact recovery fell to
zero in both corpora, and MAESTRO held-out clean false positives increased. Do
not promote the iteration as meeting the no-false-positive-regression requirement.
No musical-rule or scoring change was made after seeing these results.

The same 909 canonical POP909 files and 1,264 split-eligible MAESTRO performances
from the V0.5.2 inventories remain available. The measured subset is only eight
works per corpus (four calibration/four evaluation), one 8-beat passage each.
POP909: 540 runs per split, including 60 clean controls; MAESTRO: 600 per split,
including 60 clean controls. All 2,280 runs completed with zero errors, skipped
cases or truncated traces. These are repeated settings, not 2,280 independent
musical examples.

### Candidate recall

Percentages below exclude hard-locked targets; arrows are V0.5.2 -> V0.5.3.
The linked comparison also shows all targets, each preservation independently,
and each preset. Minimal still deliberately lacks ordinary timing/duration options.

| Corpus / split | Pitch | Timing | Duration |
|---|---:|---:|---:|
| POP909 calibration | 57.50 -> 71.25% | 1.67 -> 24.58% | 0 -> 25.00% |
| POP909 held-out | 23.75 -> 50.83% | 10.00 -> 26.25% | 4.17 -> 10.42% |
| MAESTRO calibration | 18.75 -> 27.08% | 0 -> 3.82% | 0 -> 1.67% |
| MAESTRO held-out | 24.48 -> 30.73% | 0 -> 0% | 0 -> 0% |

Generated does not mean usable or selected. For example, POP909 calibration
generated 48/192 eligible duration reference values, but only 30 were scored and
13 appeared in a surviving beam state. MAESTRO held-out pitch generation rose
from 47 to 59 of 192 eligible targets, while scored reference-value coverage
fell from 47 to 41. Constraint/budget rejection increased. Broadening proposals
alone therefore cannot establish successful recovery.

### Recovery and preservation

All settings including 100% locks; percentages are repeated note/field observations.
Partial recovery means exact recovery of an individual corrupted field, not a
subjective improvement rating. Whole-note recovery requires all fields to match.

| Corpus / split | Exact notes | Partial fields | Clean false positives | Untouched-note preservation |
|---|---:|---:|---:|---:|
| POP909 calibration | 0 -> 0.185% | 1.31 -> 2.86% | 2.65 -> 1.68% | 97.30 -> 98.35% |
| POP909 held-out | 0.185 -> 0% | 1.67 -> 1.43% | 1.94 -> 1.90% | 97.91 -> 98.04% |
| MAESTRO calibration | 1.00 -> 0% | 0.78 -> 0.44% | 1.73 -> 1.67% | 98.29 -> 98.29% |
| MAESTRO held-out | 0.333 -> 0% | 1.00 -> 0.67% | 1.58 -> 1.75% | 98.34 -> 98.22% |

Clean edited-note counts: POP909 calibration 85 -> 54 / 3,210 observations,
held-out 51 -> 50 / 2,625; MAESTRO calibration 29 -> 28 / 1,680, held-out
27 -> 30 / 1,710. POP909's aggregate held-out improvement hides a **0%-preservation
regression**: clean FP 6.48 -> 7.43%; MAESTRO at 0% worsened 7.89 -> 8.77%.
All four matrices retain zero edits at 100% preservation. Settings are not pooled
to hide these differences; see the complete per-setting table.

Only the following corruption/split cells have nonzero exact recovery in either
version. All other sampled cells are 0 -> 0%; full per-kind data remains in JSON.

| Corpus / split / corruption | Exact recovered notes | Rate |
|---|---:|---:|
| POP909 calibration / excessive sustain | 0 -> 1 of 60 | 0 -> 1.67% |
| POP909 held-out / accidental | 1 -> 0 of 60 | 1.67 -> 0% |
| MAESTRO calibration / octave | 6 -> 0 of 60 | 10.00 -> 0% |
| MAESTRO held-out / accidental | 2 -> 0 of 60 | 3.33 -> 0% |

The octave safeguard has a real tradeoff: eliminating inappropriate clean octave
movement also removes genuine injected-octave recoveries in calibration.

### Unnecessary changes and octave revoicing

Unnecessary field edits count changes to fields not listed in the corruption
ledger, including untouched fields on a corrupted note and all clean-input edits.
Different fields on one note can count separately. Octave revoicing is measured
on clean inputs so legitimate injected-octave recovery is not counted as harm.

| Corpus / split | Unnecessary pitch | Unnecessary timing | Unnecessary duration | Clean octave edits / rate |
|---|---:|---:|---:|---:|
| POP909 calibration | 169 -> 233 | 613 -> 192 | 44 -> 89 | 0 -> 0 / 0% |
| POP909 held-out | 176 -> 279 | 304 -> 162 | 38 -> 65 | 0 -> 0 / 0% |
| MAESTRO calibration | 287 -> 282 | 0 -> 0 | 0 -> 0 | 4 -> 0 / 0.238 -> 0% |
| MAESTRO held-out | 272 -> 285 | 0 -> 0 | 0 -> 20 | 20 -> 0 / 1.170 -> 0% |

POP909 clean timing changes decrease 68 -> 23 in calibration and 33 -> 18 held-out,
but clean duration changes increase 4 -> 9 and 4 -> 8. MAESTRO has no selected
timing edits, but two new clean duration edits held-out. The safeguards suppress
specific failure modes, not all unnecessary edits.

### Failure migration and coordinated coverage

Counts below are corrupted field outcomes, not independent notes or passages.
Locks remain separate (168 per POP909 split, 180 per MAESTRO split). Analysis
failure attribution is **undetermined**, not zero: missing reference candidates
can reflect inference, eligibility gates or target selection.

| Corpus / split | Missing | Pruned | Scoring preferred another result | Required combination not scored | Constraint/budget rejection |
|---|---:|---:|---:|---:|---:|
| POP909 calibration | 530 -> 394 | 19 -> 36 | 39 -> 66 | 42 -> 87 | 31 -> 59 |
| POP909 held-out | 583 -> 467 | 0 -> 15 | 23 -> 74 | 47 -> 68 | 4 -> 27 |
| MAESTRO calibration | 684 -> 653 | 4 -> 4 | 16 -> 15 | 9 -> 32 | 0 -> 12 |
| MAESTRO held-out | 673 -> 661 | 0 -> 0 | 18 -> 21 | 20 -> 14 | 0 -> 18 |

Full before-category -> after-category migrations are in the linked Markdown/JSON.
For example, 144 previously missing POP909 calibration fields now reach another
outcome: seven recover, 35 lose on scoring, 45 lack the coordinated state, 18 are
pruned, 34 encounter constraint/budget rejection, and five never enter search.
Conversely, some previously recovered fields now lose coverage; these are retained
in the migration rather than hidden behind the net recall improvement.

Each split has 120 multi-field cases including locked controls. POP909 calibration
all-reference-fields-generated rises 0 -> 15, joint states entered 0 -> 8, scored
0 -> 7, surviving joint states remain zero. Held-out generation rises 0 -> 6 and
entered states 0 -> 2, but none are scored. Both MAESTRO splits still have zero
complete reference combinations generated. Bounded linked bundles are implemented,
but successful real-corpus coordinated recovery is **not demonstrated**.

Pruning is observed history, not proof that a larger beam would fix recovery:
improving states can be retained outside the beam. Constraints and unavailable
joint states must not be relabeled as pure scoring errors.

### Scoring decision gate: identified, not tuned

The JSON contains explicit targets that were generated, appeared in a surviving
state, and still lost. Their component scores, ranks and rejection outcomes are
retained. Examples suitable for a later calibration-only investigation:

- POP909 calibration `085/085.mid@152:160`, pitch+timing corruption, Balanced,
  preservation 50/50: Clip B note 615 has reference pitch 63 at field rank 1;
  it is scored in seven states and appears in a surviving state, but is not selected.
  A combined state records `not_improving_objective`; edit/retention costs matter.
- MAESTRO calibration `2015/MIDI-Unprocessed_R2_D2-12-13-15_mid--AUDIO-from_mp3_12_R2_2015_wav--1.midi@256:264`,
  accidental, Minimal, preservation 50: note 1591's reference pitch 67 ranks first,
  is scored and survives, but loses with `not_improving_objective` and edit cost 2.165.
  This is direct evidence of a preservation-cost gate, not proof that its weight
  should automatically be reduced.
- Held-out audit only: MAESTRO `2004/MIDI-Unprocessed_XP_08_R1_2004_04-06_ORIG_MID--AUDIO_08_R1_2004_05_Track05_wav--1.midi@444:452`,
  accidental, Minimal, preservation 0: reference pitch 54 for note 2381 is an
  improving scored/surviving candidate at rank 3, yet another result wins.
  This case was inspected after freezing and did not drive an implementation change.

These traces justify further study of ranking and preservation interactions, but
not broad weight sweeps. No scoring change is included in V0.5.3.

### Runtime

Repair invocation includes tracing, excludes loading/corruption/report metrics.
Final matrices ran sequentially without concurrent test/search jobs. Historical
V0.5.2 timings are machine-dependent observations, not a controlled microbenchmark.

| Corpus / split | Mean seconds before -> after | V0.5.3 p95 | V0.5.3 repair total |
|---|---:|---:|---:|
| POP909 calibration | 0.397 -> 0.401 | 1.185 s | 216.43 s |
| POP909 held-out | 0.292 -> 0.355 | 1.053 s | 191.63 s |
| MAESTRO calibration | 0.264 -> 0.253 | 1.362 s | 151.77 s |
| MAESTRO held-out | 0.118 -> 0.197 | 0.907 s | 118.45 s |

End-to-end matrix wall time was 419.9 s POP909 and 278.2 s MAESTRO. The largest
observed invocation was 2.442 s. Target pools and alternatives remain bounded;
evaluation ceilings were not raised. These timings do not establish full-length
piece scaling. Per-run note counts, evaluation counts and runtimes are in JSON/CSV.

### Highest-value follow-up work (not implemented)

1. Validate stronger voice/motif evidence on additional **calibration** works so
   genuine octave errors can be distinguished from legitimate polyphonic register
   structure, rather than trading all octave recovery for protection.
2. Audit the POP909 candidate-side sustain and pitch evidence that increases
   unnecessary duration/pitch edits; maintain explicit clean-control acceptance
   tests before enabling broader alternatives.
3. Improve expressive timing/articulation analogues and longer-context voice
   alignment. MAESTRO held-out timing/duration reference coverage is still zero;
   scoring tuning cannot select missing values.
4. Reject structurally impossible proposals before spending the fixed search
   budget, and prioritize evidence-linked joint states. Generation gains currently
   migrate into constraint rejection and missing coordinated states.
5. Use the recorded calibration scoring-gate examples to test narrowly scoped
   ranking/preservation hypotheses, with clean FP and unnecessary fields as hard
   acceptance checks. Reserve new untouched works before another generalization claim.

Fourteen new regressions cover staggered chord voice assignment, justified versus
unjustified octave movement, transposed motif alignment across edit fields,
permission/movement limits, expressive microtiming, intentional rhythmic doubling,
voice/provenance traces, bounded linked bundles, duration/IOI relationships,
subdivision duration proposals, recurring neighbor figures, contour/register
protection, comparison denominators and cross-process candidate ordering.
Existing behavioral assertions were not weakened or removed.

### Final validation

- Full pytest: **342 passed in 36.13 s** (incoming baseline: 328).
- Ruff: passed. `git diff --check`: passed; only CRLF conversion notices.
- Independent-process replay: **45 matched cases per corpus**, all three presets
  and five preservation settings on clean, accidental and coordinated inputs.
  All edits, metrics, candidate provenance, voices and traces match after excluding
  only runtime/diagnostic durations. See `replay-verification.json`.
- `python -m glue --smoke-test`: `GLUE_GUI_SMOKE_OK`, initial preservation 100/100.
- Offscreen single/pair GUI + export/reload: `GLUE_V05_SINGLE_PAIR_EXPORT_SMOKE_OK`.
  Synthetic estimates: pitch-only 93.21 -> 100 (one pitch edit); timing-only
  66.26 -> 100 (three onset edits); duration-only 92.88 -> 98.12 (one duration edit);
  pitch+timing 70.80 -> 100 (one pitch/two onset edits); pitch+duration 92.88 -> 100
  (one pitch/one duration edit). Intentional passing tone, suspension and syncopation
  fixtures produce zero edits. Exported MIDI reloads with matching note semantics.
  These are regression demonstrations, not real-corpus quality evidence.
- Generated pair screenshot visually checked; existing controls, note labels and
  change inspector remain present. No GUI implementation was changed.
- Post-run hashes match **4,545 POP909 source/annotation files** and **1,276 MAESTRO
  MIDI files**, including quarantined entries. All four reports and replay match
  the frozen engine SHA above. Raw corpus material remains ignored by Git.
- No dependencies added, no network services, no commit or push.

Workspace caveat: an early focused pytest invocation used pytest's default OS
temporary directory. Subsequent runs explicitly used repository-local `.test-tmp`
paths. No source edits were made outside the repository.

## Reproduction

```powershell
# Existing manifests point to locally supplied, unchanged corpora.
.venv\Scripts\python.exe -m scripts.run_real_baseline --split calibration --output .test-tmp/v053-reproduction
# Freeze/review calibration before evaluating; do not retune against evaluation.
.venv\Scripts\python.exe -m scripts.run_real_baseline --split evaluation --output .test-tmp/v053-reproduction
.venv\Scripts\python.exe -m scripts.compare_candidate_baselines --after .test-tmp/v053-reproduction --split all
.venv\Scripts\python.exe -m scripts.replay_candidate_baseline --root .test-tmp/v053-reproduction
.venv\Scripts\python.exe -m pytest --basetemp .test-tmp/v053-tests
.venv\Scripts\python.exe -m ruff check .
git diff --check
.venv\Scripts\python.exe -m glue --smoke-test
.venv\Scripts\python.exe -m scripts.validate_v05 --output-dir .test-tmp/v053-export-smoke
```

Use fresh output paths; reports are not silently overwritten. The comparison
contains separate corpus/split groups, all settings, unlocked settings, each
preservation level, each preset and each corruption kind. Missing/pruned/scoring/
coordinated outcomes and their migrations are retained rather than pooled into
one success score. Analysis failure attribution remains uncertain.

## Limitations

Approximate polyphonic voices, short window boundaries and ambiguous harmony
still limit evidence. Conservative octave safeguards can miss genuine octave
errors. Motifs are bounded four-note analogues, not complete phrase understanding.
Duration limits can rule out restoration of severely shortened notes. Exact
reference-value recall is stringent for expressive timing; continuous error and
preservation metrics must be read alongside it. Sustain-pedal interpretation and
producer listening ratings are not implemented. Clean-input and corrupted-input
observations repeat the same small set of passages across settings.

The prior held-out set is now an audit set, not a fresh unlimited tuning resource.
Further tuning should remain on calibration, with additional untouched works
reserved before making broader performance claims.

## Materially changed files in this iteration

- `src/glue/analysis/voices.py`: continuity, roles, register/contour and ornament safeguards.
- `src/glue/fixes/context_candidates.py`: bounded pitch, motif, onset and articulation evidence.
- `src/glue/fixes/musical.py`: field-specific pools, deduplication, safety gates and linked bundles.
- `src/glue/fixes/search_trace.py`: proposal provenance and inferred voice/register records.
- `src/glue/benchmark/tracing.py`: diagnostic candidate-set and voice serialization.
- `scripts/compare_candidate_baselines.py`: matched corruption verification, split/settings metrics,
  candidate usability, failure migration and Markdown/JSON comparisons.
- `scripts/replay_candidate_baseline.py`: bounded independent frozen-engine replay.
- `tests/test_candidate_context_v053.py`: new candidate/voice/provenance/report regressions.
- `pyproject.toml`, `src/glue/__init__.py`: version 0.5.3.
- `tests/test_scaffold.py`, `tests/test_repair_export.py`, `tests/test_gui_v03.py`:
  expected version updated; existing behavioral assertions preserved.
- `README.md`, `docs/PRODUCT_SPEC.md`, `docs/V053_CANDIDATES.md`: behavior and measurements.
- `benchmarks/baselines/v053-real/`: frozen calibration/evaluation JSON/CSV, comparisons and replay evidence.

Earlier uncommitted V0.5.1/V0.5.2 files remain intact. This list identifies the
V0.5.3 iteration; no raw corpus, GUI implementation, objective weight, MIDI parser
or exporter was changed. Nothing was committed or pushed.
