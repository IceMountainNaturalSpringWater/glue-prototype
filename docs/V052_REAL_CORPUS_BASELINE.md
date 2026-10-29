# V0.5.2 real-corpus measurement checkpoint

## Engine and scope

The engine was frozen when real datasets became available. **No scoring weights
or repair behavior changed during this measurement phase.** Earlier, in-progress
V0.5.2 voice/octave, context-candidate and search changes were already present;
this is not the original V0.5.1 engine, nor a before/after test of those changes.
The package version still reads 0.5.1. The exact working-tree engine fingerprint is:

`04e1428013ad46e2f3c0b2838429d5a841763db64a6ebf5221d7d16bc2c5df96`

POP909 and MAESTRO are evaluated independently. Synthetic results in earlier
reports are not used as real-corpus validation. No corpus MIDI, annotations, or
metadata CSV is bundled in Git. Source files remain unchanged.

## Dataset validation

| Dataset | Detected | Parse-valid canonical/listed files | Split exclusions | Benchmark eligible |
|---|---:|---:|---:|---:|
| POP909 | 2,898 MIDI files | 909 canonical songs | 1,989 variants excluded | 909 |
| MAESTRO | 1,276 metadata-listed MIDI files | 1,275 | 11 performances in 4 conflicting work groups | 1,264 |

Every canonical/listed file was parsed, not just sampled files. POP909's extracted
release has `song/versions/*-vN.mid` alternatives; these are excluded rather than
assigned independent identities. Canonical tracks were successfully interpreted
as MELODY versus BRIDGE/PIANO accompaniment. Chord/beat/key sidecars are hashed and
retained as metadata; they are not silently interpreted as beat annotations.

MAESTRO's separate UTF-8 metadata CSV has 962 train, 137 validation and 177 test
rows. Train/validation map to calibration; test maps to held-out evaluation.
Normalized composition names expose four cross-split groups. The explicit
quarantine policy excludes all 11 related performances, without moving any file
between splits. One other file has unmatched/unterminated pitch-90 events and is
excluded under the existing strict reference-input policy. It is not rewritten.

Eligible splits: POP909 **700 calibration / 209 evaluation**; MAESTRO
**1,093 calibration / 171 evaluation**. Full hashes, warnings and quarantine
entries are recorded in each corpus's `inventory-manifest.json` and `audit.json`.

## Representative-subset protocol

- Eight distinct works per dataset: four calibration and four held-out.
- One eight-quarter-note-beat passage per work, 8–64 total notes; for POP909 both
  melody and accompaniment must contain at least two notes.
- One work per whole-file note-density quartile within each split, chosen by
  stable hash with seed 52. An interior passage is selected from up to eight
  deterministic locations using only note count/parser validity—not repair scores.
- Full original note durations/tails are retained; notes beginning before the
  window are excluded. This boundary-context limitation matters musically.
- Minimal, Balanced and Creative; preservation 0, 25, 50, 75 and 100. Pair controls
  use the same preservation on each clip. Pitch, Timing and Duration are explicitly
  enabled for these experiments, unlike the GUI's default pitch-only permissions.
- Corruption seed 52, severity 1, one corrupted note, or two for coordinated errors.
- POP909 kinds: accidental, octave, early, attack collision, sustain, short,
  pitch+timing, coordinated. MAESTRO: accidental, octave, early, late, groove,
  sustain, short, timing+duration, coordinated.
- Clean controls were run first, then repeated within the corruption matrix as a
  consistency check. The corpus summaries count one set of clean controls, not both.

The earlier 16-window `subset-manifest.json` is the inventory-stage candidate
sample. **`benchmark-manifest.json` contains the actual eight measured windows.**
Fresh runs of the inventory script now write both names for the requested sample.

## Results

Results and full per-preset, preservation and split breakdowns:

- [POP909 summary](../benchmarks/baselines/v052-real/pop909/corpus-summary.md),
  [machine-readable summary](../benchmarks/baselines/v052-real/pop909/corpus-summary.json).
- [MAESTRO summary](../benchmarks/baselines/v052-real/maestro/corpus-summary.md),
  [machine-readable summary](../benchmarks/baselines/v052-real/maestro/corpus-summary.json).

Each corpus's `calibration/` and `evaluation/` directories contain `results.json`,
`results.csv`, `summary.json`, and `summary.md`. Full JSON includes corruption
ledgers, candidate ranks, per-field target coverage, beam outcomes, scored
components, rejection reasons and winning edits. The original reference and ledger
are joined only after repair; they are never passed to the optimizer.

| Measurement | POP909 (two clips) | MAESTRO (single clip) |
|---|---:|---:|
| Distinct works / windows | 8 / 8 | 8 / 8 |
| Unique notes in windows | 389 | 226 |
| Clean / corrupted runs | 120 / 960 | 120 / 1,080 |
| Errors / inapplicable cases | 0 / 0 | 0 / 0 |
| Exact corrupted-note recovery | 1 / 1,080 (0.093%) | 8 / 1,200 (0.667%) |
| Partial recovery (exact corrupted fields) | 1.49% | 0.89% |
| Corrupted notes closer to reference | 2.50% | 1.33% |
| Untouched-note preservation, corrupted runs | 97.57% | 98.31% |
| Clean false-positive note edits | 136 / 5,835 (2.33%) | 56 / 3,390 (1.65%) |
| Clean pitch / timing / duration edits | 35 / 101 / 8 | 56 / 0 / 0 |
| Clean octave revoicing / clean note observations | 0 / 5,835 (0%) | 24 / 3,390 (0.708%) |
| Unnecessary edited notes, all runs including clean | 1,243 | 550 |
| Runs farther from reference, including clean | 356 | 197 |
| Total onset error, corrupted runs, before -> after | 100 -> 207.75 beats | 90 -> 90 beats |
| Total duration error, corrupted runs, before -> after | 202.34 -> 216.47 beats | 266.13 -> 266.13 beats |

Denominators count repeated observations across presets and preservation settings,
including the intentional 100% lock controls. Coordinated corruption changes two
notes; field recovery and whole-note recovery consequently have different
denominators. Octave revoicing here means a selected pitch displacement of a
nonzero multiple of 12 on **clean** input, avoiding confusion with legitimate
recovery of an injected octave error. Edit-type counts can overlap on one note.

### Exact recovery by corruption type

| Corruption | POP909 | MAESTRO |
|---|---:|---:|
| Accidental | 0.83% | 1.67% |
| Octave | 0% | 5.00% |
| Early onset | 0% | 0% |
| Late onset | Not sampled | 0% |
| Attack collision | 0% | Not sampled |
| Groove displacement | Not sampled | 0% |
| Excessive sustain | 0% | 0% |
| Short duration | 0% | 0% |
| Pitch + timing | 0% | Not sampled |
| Timing + duration | Not sampled | 0% |
| Coordinated multi-note | 0% | 0% |

There are 120 runs per sampled corruption kind in each corpus. More search does
not reliably improve recovery: POP909 exact recovery for Minimal/Balanced/Creative
is 0% / 0.28% / 0%, while clean FP increases 0.62% / 2.67% / 3.70%.
MAESTRO exact recovery is 0.50% / 0.75% / 0.75%; clean FP is
0.97% / 1.68% / 2.30%. Broader searches frequently select additional untouched notes.

| Preservation | POP909 clean FP | MAESTRO clean FP |
|---|---:|---:|
| 0% | 7.11% | 8.26% |
| 25% | 4.11% | 0% |
| 50% | 0.43% | 0% |
| 75% | 0% | 0% |
| 100% | 0% | 0% |

These five-setting averages must not be mistaken for the default GUI's behavior.
Higher preservation also suppresses recovery, not just unnecessary edits.

### Candidate recall and failure classification

Recall asks whether the exact reference field value was generated anywhere in
the traced search. The editable denominator excludes 100% locked controls.
For expressive timing/duration, exact recall is deliberately strict, not a claim
that every other value is musically wrong; continuous error metrics are also kept.

| Edit type | POP909 all / editable | MAESTRO all / editable |
|---|---:|---:|
| Pitch | 32.50% / 40.63% | 17.29% / 21.61% |
| Timing | 4.67% / 5.83% | 0% / 0% |
| Duration | 1.67% / 2.08% | 0% / 0% |

Counts below are corrupted **field outcomes**, not run counts. Per-edit-type
breakdowns and percentages are in the corpus summaries.

| Observed category | POP909 (1,680 targets) | MAESTRO (1,800 targets) |
|---|---:|---:|
| Analysis failure | Undetermined | Undetermined |
| Correct candidate missing | 1,113 | 1,357 |
| Correct candidate generated but pruned | 19 | 4 |
| Scoring preferred another result | 62 | 34 |
| Required coordinated state not scored | 89 | 29 |
| Hard-locked controls | 336 | 360 |
| Constraint/budget rejection | 35 | 0 |
| Generated, not entered search | 1 | 0 |
| Recovered field | 25 | 16 |

Analysis failure is **undetermined**, not zero: ground-truth note recovery alone
cannot establish whether a missing candidate came from an analysis error versus
a candidate-generation gate. Missing, pruned, scoring-rejected and undiscovered
coordinated candidates are traced; locks, safety/budget rejection and truncation
remain separate rather than being forced into a misleading diagnosis.

Pruning is observed state history, not proof that widening the beam would recover
the reference: the engine can retain improving states outside its beam. Likewise,
an unscored coordinated reference state does not prove that scoring would accept
it. These are bounded diagnostic labels, not independently verified musical causes.

### Recurring patterns and ranked next changes (not implemented)

1. **Protect intentional melody/accompaniment co-attacks before allowing timing
   separation.** POP909 has 101 clean timing edits and total onset error more than
   doubles on corrupted cases. On calibration song `253/253.mid@60:68`, Creative
   at 0% edits eight clean notes, often by 1/8 beat, with competing-attack reasons.
   Add musical-role/context evidence rather than interpreting co-attacks alone as
   mistakes; validate against clean controls before expanding timing coverage.
2. **Strengthen polyphonic voice continuity and octave evidence.** MAESTRO still
   has 24 clean octave revoicings. On calibration
   `2013/ORIG-MIDI_02_7_7_13_Group__MID--AUDIO_18_R1_2013_wav--1.midi@76:84`,
   Balanced at 0% moves D#5 -> D#4 and C#5 -> C#4, citing large leaps from lower
   notes. This suggests investigating hand/voice assignment and longer register
   context before trusting leap-reduction evidence; it does not prove a unique
   correct voice assignment. Audit sustain-pedal context as part of this work.
3. **Increase contextual timing/duration candidate coverage without blanket
   quantization.** Zero MAESTRO timing/duration reference candidates and no reduction
   in their continuous errors show that scoring-weight tuning alone cannot solve
   those cases. Explore local expressive timing/motif templates and plausible
   release boundaries, retaining displacement bounds and clean-groove safeguards.
4. **Improve pitch candidate targeting and ambiguity handling.** Editable pitch
   recall is only 40.63% POP909 / 21.61% MAESTRO. Audit ornament/protection gates,
   note-pool selection, and local harmony labels before widening pitch ranges.
   POP909 song 253 also changes clean E5 -> F5 while describing the original as a
   weak-beat chord tone; analysis/rationale consistency needs review, not an
   automatic assertion that the original harmony was wrong.
5. **Then investigate coordinated coverage and ranking.** Reserve bounded search
   paths for complementary edits only after candidates are available. Compare
   traced reference-valued states and clean-preservation costs before any scoring
   change. Wider search alone is low priority given the dominant coverage gaps and
   increasing false positives. Any later tuning belongs on calibration only;
   this held-out measurement remains a fixed audit.

### Runtime

| Repair invocation including tracing | POP909 | MAESTRO |
|---|---:|---:|
| Total | 371.85 s | 229.17 s |
| Mean per run | 0.344 s | 0.191 s |
| Median per run | 0.160 s | 0.034 s |
| 95th percentile | 1.117 s | 1.059 s |
| Maximum | 1.767 s | 1.785 s |

Full matrix wall times including loading, corruption, metrics and report writing
were approximately 380.4 s POP909 and 233.7 s MAESTRO. Source inventory and the
separate clean-control/replay runs are additional. Raw records retain runtime,
note count, evaluation count and preset for subsequent scaling analysis.

## Reproduce (PowerShell)

The provided extraction has an extra directory level. Current effective paths:

```text
benchmarks/POP909/POP909/001/001.mid
benchmarks/POP909/POP909/001/chord_midi.txt
benchmarks/maestro-v3.0.0-midi/maestro-v3.0.0/2004/...midi
benchmarks/maestro-v3.0.0.csv
```

```powershell
# Parse/inventory both datasets and build strict, deterministic subsets.
.venv\Scripts\python.exe -m scripts.benchmark_real_corpora --output .test-tmp/real-inventory --per-split 4 --max-notes 64 --window-beats 8

# Defaults use the paths above; override --pop-root, --maestro-root and
# --maestro-metadata for other extraction locations or a separate CSV.

# Measure each dataset/split separately, with tracing and all five settings.
.venv\Scripts\python.exe -m scripts.run_real_baseline --manifests .test-tmp/real-inventory --output .test-tmp/real-inventory

# Existing recorded manifests can also be reused without repeating the audit.
.venv\Scripts\python.exe -m scripts.run_real_baseline --manifests benchmarks/baselines/v052-real --output .test-tmp/real-repeat

# Summarize the recorded matrices independently (writes new summary files).
.venv\Scripts\python.exe -m scripts.summarize_real_baseline --root .test-tmp/real-inventory

# Replay 45 cases per corpus and compare separately recorded clean controls.
# Requires the original clean-{split} controls alongside the matrices.
.venv\Scripts\python.exe -m scripts.repeat_real_baseline

.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .
git diff --check
```

Outputs must be new directories; existing baselines are not overwritten. Use
`--dataset pop909` or `--dataset maestro`, and `--split calibration` or
`--split evaluation` to run one matrix. Generic adapter entry points remain
`python -m glue.benchmark manifest` with `--dataset`, `--metadata`, `--pop-pairs`,
and explicit `--quarantine-split-conflicts` if needed.

## Changed files and validation

Measurement-stage files: `.gitignore`, `README.md`,
`src/glue/benchmark/manifest.py`, `src/glue/benchmark/__main__.py`,
`scripts/benchmark_real_corpora.py`, `scripts/run_real_baseline.py`,
`scripts/summarize_real_baseline.py`, `scripts/repeat_real_baseline.py`,
`tests/test_real_corpus_protocol.py`, and this report. Generated manifests,
audits, traced JSON/CSV matrices and summaries are under
`benchmarks/baselines/v052-real/`. Earlier uncommitted benchmark/engine work remains
in place; this list identifies only the current real-data measurement phase.

Tests cover canonical POP selection, composition/content-connected split
quarantine without reassignment, deterministic subset selection, weighted summary
denominators and replay normalization. Existing engine, GUI, MIDI preservation,
trace isolation and corruption tests remain intact.

- Initial full measurement-stage validation: **327 tests passed**, Ruff passed,
  and `git diff --check` passed (Git emitted only line-ending conversion warnings).
- A separate process replayed **45 cases per corpus**, covering clean, accidental,
  and coordinated inputs on one calibration passage, all three presets and five
  preservation levels. All results, edits, metrics and traces matched exactly
  after excluding only runtime and diagnostic duration.
- All **120 separate clean controls per corpus** matched their matrix counterparts.
  No trace was truncated in either full matrix. See
  [replay verification](../benchmarks/baselines/v052-real/replay-verification.json).
- `python -m glue --smoke-test`: passed.
- `python -m scripts.validate_v05 --output-dir .test-tmp/v052-real-gui-smoke`:
  single/pair, pitch/timing/duration/coordinated edits, intentional ornament/groove
  preservation, and MIDI export/reload smoke checks passed. These synthetic checks
  remain regression tests, not real-corpus musical validation.
- Final validation after adding the replay-helper regression test: **328 passed
  in 34.20 s**; Ruff passed; `git diff --check` passed.
- Post-run hashes matched all **4,545 POP909 source/annotation files** and
  **1,276 MAESTRO source files** in the inventories, including quarantined entries.
  The engine fingerprint still matches the frozen value at the top of this report.

No source corpus was edited, no dependencies were added, and no changes were
committed or pushed. Measurement stops here; recommendations above are not tuning.

## Limitations

This is a first diagnostic subset, not full-corpus musical validation. Rates are
reference-relative: a professional performance is not proof every event is perfect,
and a corruption can accidentally produce a musically valid alternative. Repeated
settings are not independent pieces. Sparse count-bounded windows underrepresent
very dense passages and lose some phrase/harmony context. Corpus-specific chord
annotation accuracy and subjective listening ratings were not measured.

Timing is measured around repair (including tracing), excluding MIDI loading,
corruption creation and report metrics. Datasets are run sequentially on the same
machine. No weights are tuned against either calibration or evaluation results.
