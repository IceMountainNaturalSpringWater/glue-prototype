# GLUE V0.5.4: recovery, oracle ceilings and counterfactual diagnostics

## Scope and protocol

No GUI features, dependencies, audio, network services or producer-quality claims
are added. Production search never receives the reference performance, corruption
ledger, benchmark note masks or desired values. The new oracle is strictly an
offline consumer of completed blind-repair reports. V0.5.3 reports, source MIDI,
annotations and manifests remain intact. Changes are uncommitted.

Development uses the existing four calibration passages per corpus. V0.5.3's
published held-out aggregate results were already known from the preceding task;
no held-out examples or new held-out oracle results are used to design fixes.
Baseline held-out counterfactuals were computed and sealed before engine changes,
because their score decomposition requires the unchanged V0.5.3 engine.

The protocol remains seed 52; one 8-beat window per work; 8-64 notes; all three
presets; preservation 0/25/50/75/100 (symmetric for pairs); explicit Pitch/Timing/
Duration permission. POP909 uses melody/accompaniment pairs, MAESTRO single piano.
There are four calibration and four held-out works in each corpus. Each POP909
split has 540 runs including 60 clean controls; each MAESTRO split has 600 including
60 clean controls. Repeated presets/settings are not independent compositions.

## Oracle definitions

- **Any-rank and top-1/3/5 recall:** exact reference field value in the generated
  bounded pool, ranked separately for each note/edit field. These are not GUI
  alternative ranks. Entered/scored/survived/pruned flags retain observed history.
- **Availability upper bound:** count of corrupted notes for which every required
  reference field exists in the generated pool, ignoring joint validity and cost.
  This relaxed Cartesian bound can overestimate achievable recovery.
- **Feasible no-collateral oracle:** exhaustive subsets of complete reference-note
  corrections, with all untouched notes/fields left unchanged. Uses the actual
  permissions, preservation edit limits, MIDI/movement safeguards and structural
  retention checks, but ignores scoring preference. The implementation explicitly
  rejects more than ten corrupted notes instead of silently approximating.
- The feasible oracle is **not** an exhaustive optimum over arbitrary collateral
  changes. Such changes might enable otherwise invalid states. Reporting both
  bounds avoids pretending that value availability proves a feasible repair.
- Actual recovery is always GLUE's first selected candidate, never oracle-selected.
  Partial recovery means an exact corrupted field; exact-note recovery requires
  all fields of that note to match. Unnecessary edits are measured independently.

## V0.5.3 baseline, measured before engine changes

Engine SHA: `66e7374af98dc90556c96d64875d42803b7cea58f6b0a21149468cc7a9b98c53`.
Incoming validation: 342 tests and Ruff passed.

| Calibration corpus, all settings | Actual exact | Feasible oracle | Availability bound |
|---|---:|---:|---:|
| POP909 | 0.185% | 16.85% | 19.63% |
| MAESTRO | 0% | 2.50% | 2.50% |

This shows a large selection gap for POP909, but a low whole-note ceiling for
MAESTRO even before ranking. Reference fields can exist individually while the
other fields needed for the same note are absent. Movement bounds also matter:
doubling a severely shortened note can exceed the permitted 75% source-relative
duration expansion. Those outcomes are not relabeled as scoring losses.

### Score-loss evidence

For every case, developer-only diagnostics compare selected and complete-reference
states, including raw components, weighted contributions, motif/contour/groove
retention, pitch/onset/duration displacement, edit count and preservation costs.
Positive `truth_minus_selected_margin` means the current objective prefers the
selected state. Counterfactuals can be absent from the actual pool or structurally
invalid; explicit validity results accompany their scores.

On calibration POP909 `085/085.mid@152:160`, clean Balanced at 0% favors edits by
4.705 objective units; 4.5 comes from separating close-register co-attacks, versus
about 0.44 from harmony. This is an evidence/feature problem, not justification
for a blind weight sweep. On MAESTRO calibration, feasible onset restoration can
pay 0.125 groove-retention cost while small unrelated harmonic gains win instead.
Several correct pitch candidates lose to preservation costs despite ranking first.

Existing components already use differing musical normalizations (note count,
pair activity and beat duration). They are not calibrated probabilities or equally
scaled quality axes. This iteration conditions the overly broad rhythm feature
on musical evidence rather than globally rescaling all weights. Side-by-side
weighted margins expose dominance instead of hiding it in a combined score.

## Changes and evidence

1. **Pair rhythm evidence:** mere close-register coincidence no longer incurs
   the competing-attack term. It requires substantial interval tension or two
   competing monophonic lines, and respects joint harmonic support. Intentional
   synchronization is not automatically wrong.
2. **Consistent voice use:** melodic continuity and retention now use the same
   register-aware inferred voice paths as candidate generation. The older
   flattened track/channel ordering could miss real contour damage or invent
   leaps between chord voices. This also protects short descending phrase endings.
3. **Expressive relationships:** compensating short/long onset intervals in a
   locally stable performed pulse supply bounded alternatives, retaining nonzero
   phase and allowing rubato. Small deviations are left alone. Articulation uses
   local duration/IOI ratios and immediate neighbors, not a universal note length.
   Existing edit permissions and source-relative movement bounds remain unchanged.
4. **Contextual scoring:** explicit Performance rhythm, Contextual articulation
   and Octave context components make supported anomalies visible to full-passage
   scoring. Their centralized weights are 1.0, 0.5 and 1.0. Existing weights are
   unchanged; no parameter sweep was performed. Supported onset restoration does
   not pay the ordinary local groove-damage term merely for changing a gap.
5. **Contextual octave reasoning:** motif corroboration or a stable longer voice,
   robust-register excursion and supporting neighboring intervals can override
   the former blanket overlap rejection. Compact chord membership counters a
   suspected excursion; ordinary high notes are not automatically octave errors.
   Confidence values are heuristic, not calibrated probabilities. Crossing and
   MIDI safety checks remain conservative.
6. **Fixed-budget search allocation:** round-robin note/field alternatives give
   different edit types access before one note consumes the shallow budget. Up to
   four coherent onset-shift bundles preserve a targeted short line's internal
   intervals. Bundles use generated values only and pass the same full-state
   validator. No global beam-width, depth or evaluation-limit increase.

An existing timing-only regression initially acquired an unnecessary pitch edit.
The coherent onset bundles fixed it without changing the original assertion.

## Calibration development checks

Trial 1 (`.test-tmp/v054-calibration-1`, engine `dbd9e9f35f82cfd8afabc32179b37a21258085d5e3530536fed231490f4280bd`):
POP909 exact recovery 1 -> 3 / 540, clean FP 54 -> 45 / 3,210. MAESTRO exact
recovery 0 -> 12 / 600, but clean FP 28 -> 34 / 1,680 and two clean octave changes.
The trial process loaded version 0.5.3 before the package version was updated;
the engine fingerprint identifies the actual implementation, not that label.

Calibration traces showed a compact low chord note incorrectly assigned to an
upper voice, short articulation consistent with its immediate neighbors flagged
as anomalous, and retention still using the older voice ordering. The three
specific corrections above followed those traces. Clean controls afterward:
POP909 41 / 3,210; MAESTRO 28 / 1,680; zero clean octave changes in both. MAESTRO
has two new clean timing edits despite unchanged total false positives.

Clean-edit causes are evidence-label hypotheses: harmony, explicit motif
correspondence, register/voice, timing, duration, plus an overlapping multi-edit
search-interaction tag. A generic rationale mentioning motif retention is not
counted as motif-generated correction. The final comparison recomputes these
tags from the saved edits; it supersedes the initial oracle's draft cause labels.

## Frozen results and validation

**The overall repair-quality gate is not met.** MAESTRO's calibration recovery
gain did not generalize to held-out works. POP909's held-out gain is one recovered
note across repeated settings, not a material closing of the oracle gap. This is
an overfitting/generalization warning under the requested stop rule: no further
engine tuning followed evaluation. Lower clean false-positive totals do not
cancel the regressions below. These eight works per corpus are not broad musical
or listening validation.

The final engine fingerprint is
`a00c900cfe8da896d851a91a8d16a625da9c8204269e90b962cf66b993ed06c8`.
[The freeze record](../benchmarks/baselines/v054-real/freeze.json) predates the new
held-out run. All four result matrices match it. The final comparison includes
all settings, unlocked settings, each preservation value, each preset and each
corruption type in [Markdown](../benchmarks/baselines/v054-real/quality-comparison-all.md)
and [JSON](../benchmarks/baselines/v054-real/quality-comparison-all.json).
Per-case results, CSV exports and oracle diagnostics remain in the corpus/split
subdirectories. All arrows below are V0.5.3 -> V0.5.4.

### Inventory and sample sizes

POP909: 2,898 MIDI files detected, 909 canonical songs usable, 1,989 variants
excluded; deterministic manifest split 700 calibration / 209 held-out.
MAESTRO: 1,276 listed MIDI files, 1,275 parse-valid; 11 performances in four
cross-split work groups quarantined, leaving 1,264 eligible (1,093 calibration /
171 held-out). Source hashes remain unchanged for all 4,545 POP909 source and
annotation files and all 1,276 MAESTRO MIDI files.

The benchmark subset uses four works per split per corpus, not the full inventory.
Each POP909 split has 540 runs, each MAESTRO split 600, including 60 clean runs
each: 2,280 total. Every work is repeated over three presets and five preservation
values. Results must not be interpreted as thousands of independent examples.

### Actual recovery versus oracle and clean preservation

Rates in this table include 100% preservation; exact recovery denominators are
540 corrupted-note observations per POP909 split and 600 per MAESTRO split.
Clean FP is the fraction of original clean notes edited, not the fraction of runs.

| Corpus / split | Actual exact recovery | Feasible oracle | Availability upper bound | Clean FP notes / denominator (rate) | Untouched-note preservation |
|---|---:|---:|---:|---:|---:|
| POP909 calibration | 1 -> 1 (0.19% -> 0.19%) | 16.85% -> 18.15% | 19.63% -> 19.63% | 54 -> 41 / 3,210 (1.68% -> 1.28%) | 98.35% -> 98.64% |
| POP909 held-out | 0 -> 1 (0% -> 0.19%) | 12.59% -> 12.41% | 13.70% -> 13.52% | 50 -> 44 / 2,625 (1.90% -> 1.68%) | 98.04% -> 98.33% |
| MAESTRO calibration | 0 -> 12 (0% -> 2.00%) | 2.50% -> 7.00% | 2.50% -> 7.00% | 28 -> 28 / 1,680 (1.67% -> 1.67%) | 98.29% -> 98.38% |
| MAESTRO held-out | 0 -> 0 (0% -> 0%) | 3.00% -> 2.83% | 3.00% -> 2.83% | 30 -> 29 / 1,710 (1.75% -> 1.70%) | 98.22% -> 98.27% |

| Unlocked settings only | Actual exact | Feasible oracle | Clean FP |
|---|---:|---:|---:|
| POP909 calibration | 0.23% -> 0.23% | 21.06% -> 22.69% | 2.10% -> 1.60% |
| POP909 held-out | 0% -> 0.23% | 15.74% -> 15.51% | 2.38% -> 2.10% |
| MAESTRO calibration | 0% -> 2.50% | 3.13% -> 8.75% | 2.08% -> 2.08% |
| MAESTRO held-out | 0% -> 0% | 3.75% -> 3.54% | 2.19% -> 2.12% |

Actual recovery as a fraction of the feasible no-collateral ceiling is only
1/98 for final POP909 calibration, 1/67 for POP909 held-out, 12/42 for MAESTRO
calibration and 0/17 for MAESTRO held-out. Candidate coverage is not sufficient.

The only nonzero exact-recovery corruption cells are POP909 calibration sustain
(1/60 before and after), POP909 held-out accidental (0 -> 1/60), and MAESTRO
calibration octave (0 -> 12/60). All other corruption types have zero exact-note
recovery. The 12 MAESTRO recoveries repeat two passages across presets/settings;
they are not 12 independent successful performances.

Partial corrupted-field recovery is POP909 calibration 2.86% -> 2.14%, held-out
1.43% -> 2.14%; MAESTRO calibration 0.44% -> 1.67%, held-out 0.67% -> 0.67%.

### Candidate recall and ranking

Editable targets only (100% locks excluded). Each cell is before -> after.
Rank is within the generated alternatives for the particular note and field.

| Corpus / split / field | Any rank | Top 1 | Top 3 | Top 5 |
|---|---:|---:|---:|---:|
| POP909 calibration pitch | 71.25% -> 71.25% | 28.33% -> 28.33% | 64.58% -> 64.58% | 69.58% -> 69.58% |
| POP909 calibration timing | 24.58% -> 24.58% | 19.58% -> 19.58% | 24.58% -> 24.58% | 24.58% -> 24.58% |
| POP909 calibration duration | 25.00% -> 25.00% | 0% -> 0% | 2.08% -> 0% | 6.25% -> 6.25% |
| POP909 held-out pitch | 50.83% -> 50.00% | 29.17% -> 29.17% | 37.92% -> 37.50% | 45.83% -> 45.00% |
| POP909 held-out timing | 26.25% -> 26.25% | 22.92% -> 19.58% | 26.25% -> 24.58% | 26.25% -> 24.58% |
| POP909 held-out duration | 10.42% -> 10.42% | 0% -> 0% | 2.08% -> 2.08% | 4.17% -> 4.17% |
| MAESTRO calibration pitch | 27.08% -> 38.54% | 23.96% -> 35.42% | 27.08% -> 38.54% | 27.08% -> 38.54% |
| MAESTRO calibration timing | 3.82% -> 6.25% | 0% -> 0% | 2.78% -> 3.82% | 3.82% -> 6.25% |
| MAESTRO calibration duration | 1.67% -> 1.67% | 0% -> 0% | 1.67% -> 1.67% | 1.67% -> 1.67% |
| MAESTRO held-out pitch | 30.73% -> 29.17% | 11.98% -> 11.46% | 25.00% -> 23.96% | 26.56% -> 25.00% |
| MAESTRO held-out timing | 0% -> 0% | 0% -> 0% | 0% -> 0% | 0% -> 0% |
| MAESTRO held-out duration | 0% -> 0% | 0% -> 0% | 0% -> 0% | 0% -> 0% |

Expressive timing proposals helped only calibration. Contextual duration
proposals did not improve measured recall, and neither timing nor duration
produced any exact held-out MAESTRO candidate. This requirement remains an
empirical limitation, not a completed quality improvement.

### Octaves, coordinated search and collateral edits

Clean octave revoicing is zero in both versions in all four groups. MAESTRO
calibration reference-octave availability increases 0 -> 24/60 targets;
selection and exact recovery increase 0 -> 12/60. MAESTRO held-out remains zero
for all three. POP909 calibration has 12/60 available before and after, but none
selected; POP909 held-out has none available. Legitimate octave repair is possible
without the trial's two clean octave errors, but no generalization is established.

Among 120 coordinated cases per split, POP909 calibration has all required
values available in 15 before and after; jointly entered states increase 8 -> 11,
scored states 7 -> 10, but none survive or fully recover. POP909 held-out has six
available, entered 2 -> 4, none scored or recovered. MAESTRO has zero fully
available coordinated states in both splits. There is no real-corpus coordinated
full-recovery success to claim.

Unnecessary field edits (including clean runs and untouched fields on corrupted
notes) expose regressions hidden by aggregate edited-note rates:

| Corpus / split | Pitch | Timing | Duration | Runs farther from reference, including clean |
|---|---:|---:|---:|---:|
| POP909 calibration | 233 -> 230 | 192 -> 39 | 89 -> 155 | 156 -> 127 |
| POP909 held-out | 279 -> 301 | 162 -> 51 | 65 -> 113 | 115 -> 129 |
| MAESTRO calibration | 282 -> 256 | 0 -> 14 | 0 -> 0 | 87 -> 85 |
| MAESTRO held-out | 285 -> 277 | 0 -> 9 | 20 -> 8 | 116 -> 123 |

Thus both held-out corpora have **more runs made worse**, despite fewer clean
notes edited. Clean POP909 timing edits fall 23 -> 4 (calibration), 18 -> 5
(held-out), but duration edits rise 9 -> 15 and 8 -> 13, respectively. Clean
MAESTRO gains two calibration timing edits and one held-out timing edit.
The full report retains harmony/motif/register/timing/duration cause tags and
overlapping search-interaction tags. These are diagnostic hypotheses, not proof
that the model's musical explanation is correct.

### Failure classification and score-loss examples

Final corrupted-field counts (840 per POP909 split; 900 per MAESTRO split):

| Diagnostic category | POP cal | POP held-out | MAESTRO cal | MAESTRO held-out |
|---|---:|---:|---:|---:|
| Preservation locked | 168 | 168 | 180 | 180 |
| Correct candidate missing | 394 | 469 | 624 | 664 |
| Constraint rejected | 47 | 26 | 9 | 17 |
| Candidate pruned | 36 | 11 | 0 | 0 |
| Generated, not entered | 22 | 21 | 0 | 0 |
| Coordinated-search failure | 82 | 58 | 33 | 13 |
| Scoring rejected correct candidate | 73 | 69 | 39 | 20 |
| Recovered field | 18 | 18 | 15 | 6 |

Analysis failure cannot be uniquely attributed from a search trace: missing
evidence and missing generation can overlap. Pruning history likewise does not
prove causality because improving alternatives may be retained outside the beam.
The reports preserve these distinctions rather than inventing certainty.

The final JSON also includes counterfactuals from **actual scored states containing
the reference field**, with their stored component weights, complete edits and
round/pruning history. These differ from hypothetical complete-reference states
and may contain collateral edits. Examples from the frozen engine:

- MAESTRO calibration `2009/MIDI-Unprocessed_10_R1_2009_03-05_ORIG_MID--AUDIO_10_R1_2009_10_R1_2009_03_WAV.midi@368:376`,
  timing+duration, Balanced, preservation 0: note 1384's correct onset 391 was
  scored in round 1. The best observed state containing it loses by 0.170 objective
  units: retention contributes 0.125 and harmony 0.045.
- MAESTRO held-out `2004/MIDI-Unprocessed_XP_08_R1_2004_04-06_ORIG_MID--AUDIO_08_R1_2004_05_Track05_wav--1.midi@444:452`,
  accidental, Minimal, preservation 0: note 2381's correct pitch 54 was scored in
  round 1 but loses by 0.057: harmony 0.029, resolution 0.024, bass 0.004.
- POP909 calibration `085/085.mid@152:160`, coordinated, Minimal, preservation
  0/0: note 620's correct pitch 82 occurs in round 2 and loses by 0.028 overall;
  harmony alone contributes 0.101, partly offset by other terms.
- POP909 held-out `105/105.mid@312:320`, pitch+timing, Creative, preservation
  0/0: note 1207's correct pitch 58 occurs in round 4 and loses by 0.009, from
  harmony. These post-freeze examples are diagnoses, not tuning targets.

### Runtime and profiling

| Corpus / split | Mean repair seconds | Total repair seconds | Relative mean increase |
|---|---:|---:|---:|
| POP909 calibration | 0.401 -> 0.633 | 216.4 -> 341.7 | 57.9% |
| POP909 held-out | 0.355 -> 0.487 | 191.6 -> 262.9 | 37.2% |
| MAESTRO calibration | 0.253 -> 0.329 | 151.8 -> 197.4 | 30.0% |
| MAESTRO held-out | 0.197 -> 0.271 | 118.4 -> 162.5 | 37.2% |

Frozen V0.5.4 wall times including loading/reporting are 348.8, 268.6, 201.5
and 166.6 seconds, respectively. Repair clocks include tracing, not loading,
corruption or metric calculation. These historical/current runs are not isolated
search microbenchmarks: scoring and scheduling changed together, so the table
cannot attribute the runtime increase to search alone.

An Oct 28 cProfile check on the two densest calibration clean passages (Creative,
preservation 0, all permissions) reaches the existing 420-evaluation ceiling:
59-note POP909 takes 5.495 instrumented seconds, 5.026 in `score_passage`, 1.563
in harmony inference and 0.935 in octave confidence; 58-note MAESTRO takes 6.978,
6.498, 2.879 and 2.123 seconds respectively. Cumulative values overlap and profiling
adds overhead; do not compare them to the unprofiled matrix means. Full-state
scoring, harmonic frame candidates and repeated octave-context checks dominate.
Local profiles are in `.test-tmp/v054-profile-oct28/`.

### Final validation

- Full pytest: **355 passed in 29.10 seconds** (342 incoming tests; 13 added).
- Ruff and `git diff --check`: passed.
- Independent actual search replay: **90/90 cases match**, 45 per corpus,
  across three presets and all five preservation values; runtime fields excluded.
- All **2,280 oracle diagnostic rows** independently regenerated and matched.
- Separate calibration clean controls: **60/60 per corpus** match matrix results.
- Source hash inventory unchanged; all four result matrices have the frozen SHA;
  no benchmark errors, skipped cases or truncated traces.
- GUI launch: `GLUE_GUI_SMOKE_OK`, both preservation defaults 100%.
- Single/pair repair and export/reload smoke: `GLUE_V05_SINGLE_PAIR_EXPORT_SMOKE_OK`.
  Pitch-only, timing-only, duration-only and coordinated fixture exports reload
  with the intended edits and preserved unrelated MIDI events. Intentional
  passing-tone, suspension and syncopated fixtures receive zero edits.

The synthetic smoke musical-fit estimates are pitch-only 93.209 -> 100 (one
pitch edit); timing-only 66.262 -> 100 (three timing edits); duration-only
92.879 -> 98.119 (one duration edit); pitch+timing 79.208 -> 100 (one pitch,
two timing); pitch+duration 92.879 -> 100 (one pitch, one duration). These prove
execution and regression behavior, not real-corpus recovery or audible quality.

New tests cover isolated post-hoc oracle operation, deterministic bounds,
preservation locks/top-k denominators, objective reconciliation, cause tags,
fingerprint/case matching and recorded-state counterfactuals; expressive phase
retention, permission-gated articulation, supported legato octave restoration,
bounded existing-option bundles, compact-chord protection and intentional short
articulation. Existing tests were not removed or weakened.

### Highest-value follow-up hypotheses (not implemented after evaluation)

1. Improve same-voice and phrase evidence before further score tuning. Missing
   reference fields dominate MAESTRO; held-out expressive timing/duration recall
   remains zero. Longer context and pedal-aware duration evidence need new tests.
2. Make repair acceptance sensitive to confidence and collateral cost. Held-out
   damage increased, and pitch/duration substitution can hide behind reduced
   timing edits. Test abstention against clean and corrupted calibration controls.
3. Use diagnostic component margins to revise relationship scoring, especially
   local harmony versus voice/motif continuity and source-relative groove cost.
   Avoid a global weight sweep or tuning to the held-out cases printed above.
4. Investigate fixed-budget coordinated-state scheduling with controlled ablations.
   More joint states entered POP909 search without a single full joint recovery;
   distinguish missing complete states, pruning and scoring before widening search.
5. Cache reusable octave/register evidence and profile incremental harmony scoring.
   Preserve exact full-state semantics and replay results; runtime rose materially
   without a corresponding general recovery gain.

Further experiments require calibration or newly reserved works and a fresh
evaluation protocol. No claim of successful broad repair-quality improvement is
made, and no commit or push was performed.

## Reproduction

```powershell
# Use fresh paths. The old engine is required to rescore old counterfactuals;
# its saved oracle results are retained for comparisons with the current engine.
.venv\Scripts\python.exe -m scripts.run_real_baseline --split calibration --output .test-tmp/v054-repeat
.venv\Scripts\python.exe -m scripts.oracle_baseline --input .test-tmp/v054-repeat --output .test-tmp/v054-repeat --split calibration
.venv\Scripts\python.exe -m scripts.report_v054 --after .test-tmp/v054-repeat --split calibration
# Freeze and review calibration before running evaluation; do not retune afterward.
.venv\Scripts\python.exe -m scripts.run_real_baseline --split evaluation --output .test-tmp/v054-repeat
.venv\Scripts\python.exe -m scripts.oracle_baseline --input .test-tmp/v054-repeat --output .test-tmp/v054-repeat --split evaluation
.venv\Scripts\python.exe -m scripts.report_v054 --after .test-tmp/v054-repeat --split all
.venv\Scripts\python.exe -m scripts.replay_candidate_baseline --root .test-tmp/v054-repeat
.venv\Scripts\python.exe -m pytest --basetemp .test-tmp/v054-tests
.venv\Scripts\python.exe -m ruff check .
git diff --check
.venv\Scripts\python.exe -m glue --smoke-test
.venv\Scripts\python.exe -m scripts.validate_v05 --output-dir .test-tmp/v054-smoke
```

## Limitations

Approximate voices can change under edits. The model cannot uniquely recover a
performer's intended expressive timing from an eight-beat excerpt. Direct
reference-value recall is strict, and the oracle is intentionally not a repair
input. Pedal events are preserved on export, but acoustic pedal/sustain reasoning
is not implemented. Motif variations and chord roles remain ambiguous. Duration
constraints exclude some full recoveries. Historical/current runtime comparisons
are machine-dependent, not controlled microbenchmarks. Further development must
use calibration or new reserved works, not repeated tuning on the current audit set.

## Materially changed files in this iteration

- `src/glue/benchmark/oracle.py`: isolated reference-aware oracle and score diagnostics.
- `scripts/oracle_baseline.py`: fingerprint-checked post-hoc per-case reports.
- `scripts/report_v054.py`: matched corpus/split/settings oracle-versus-actual reports.
- `src/glue/analysis/relationships.py`: cached performance-relative rhythm/articulation evidence.
- `src/glue/analysis/voices.py`: corroborated octave confidence and chord-register safeguard.
- `src/glue/fixes/context_candidates.py`: bounded expressive and octave proposals.
- `src/glue/fixes/musical.py`: contextual score terms, consistent voice retention,
  evidence-conditioned rhythm, fair option scheduling and coherent onset bundles.
- `src/glue/fixes/musical_config.py`: centralized new component weights.
- `tests/test_oracle_v054.py`, `tests/test_relationship_repair_v054.py`: diagnostic and musical regressions.
- `pyproject.toml`, `src/glue/__init__.py`, `tests/test_scaffold.py`,
  `tests/test_repair_export.py`, `tests/test_gui_v03.py`: version 0.5.4 and expected-version assertions.
- `README.md`, `docs/PRODUCT_SPEC.md`, this report: version, contract and evidence.
- `benchmarks/baselines/v054-oracle-v053/`: original-engine oracle reports, four corpus/split JSON files.
- `benchmarks/baselines/v054-real/`: frozen measurements, oracle comparisons and validation evidence.

Existing uncommitted V0.5.1-V0.5.3 work is preserved. No GUI implementation,
MIDI parser/exporter, dataset source file or annotation is changed in this iteration.
