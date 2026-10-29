# V0.5.1 baseline and implementation report

## Scope and integrity

V0.5 repair/search/analysis/GUI code and all musical weights remain unchanged.
Only the application version changed to 0.5.1 in production code. The benchmark
invokes the current repair engine without passing reference MIDI, error locations,
reference pitch alternatives or chord annotations as guidance. Candidate 0 is
measured; oracle-best retained alternatives are diagnostic only.

No tuning was performed. No commercial datasets were downloaded or bundled.
No POP909/MAESTRO producer-scale quality claim is made: only local adapters and
synthetic-format tests have been exercised. Actual corpus evaluation needs locally
supplied, licensed and reviewed references. See [usage and definitions](BENCHMARKING.md).

## Recorded baseline

[Calibration summary](../benchmarks/baselines/v051-synthetic/summary.md) and
[evaluation summary](../benchmarks/baselines/v051-evaluation/summary.md) each have
adjacent full `results.json`, `results.csv`, and `summary.json` artifacts.

The self-authored references are a repeated major melody, a C/F/G/C chord passage,
and a two-file call/response pair. One chromatic/syncopated phrase is held out for
evaluation. Each contains only 8–12 notes total per case, so this is a small
framework-validation corpus, not a representative final evaluation dataset.
All 19 corruption types were exercised somewhere in calibration. Inapplicable
combinations are visible skips rather than fabricated errors.

Protocol: seed 17, severity 1, one corrupted note (two for coordinated errors),
all edit permissions enabled, all three presets, preservation 0/50/90/100,
plus pair 100:0 and 0:100. A clean control runs for every preset/setting.

| Calibration preset | Runs | Exact corrupted-note recovery | Unnecessary note edits | Clean note false positives | Made-worse runs | Mean repair time |
|---|---:|---:|---:|---:|---:|---:|
| Minimal | 228 | 1.32% | 25 | 1.56% | 17 | 7.01 ms |
| Balanced | 228 | 1.75% | 32 | 1.56% | 24 | 10.94 ms |
| Creative | 228 | 1.75% | 34 | 1.56% | 24 | 15.06 ms |

Calibration totals: **684 runs, zero engine errors, 11 inapplicable cases**.
Exact recovery is 11/684 corrupted-note observations (1.61%). There are 91
unnecessary note/field edits and 65 made-worse runs, including three clean runs.
Clean false positives are 6/384 note observations (1.56%), across 42 clean runs.
Repair invocation time totals 7.525 seconds; mean 11.00 ms, maximum 672.77 ms.
These are local-machine measurements, excluding I/O, corruption and metric work.
The JSON summary includes individual runtime/note-count/preset/evaluation records.

**These aggregate rates include locked controls.** On calibration runs where every
clip is at 0% preservation, exact recovery is 11/147 corrupted-note observations
(7.48%), clean false positives are 6/84 (7.14%), and 55/147 runs move farther from
the reference. Those results are also weak; low recovery is not only a lock effect.
All 100% locked clips retain zero edits.

Held-out evaluation: **180 runs, zero errors, five inapplicable cases**. Exact
recovery is 0%; clean false positives 0/96; three unnecessary note edits and three
made-worse runs. Total repair time is 0.547 seconds. This is one synthetic phrase,
not evidence that unseen real-world material is safe. No changes followed the
evaluation results.

## Major failures and evidence-supported recommendations

1. **Unnecessary octave revoicing of clean chord material.** At 0% preservation,
   Minimal changes G2→G3 and B2→B3 in the clean G-major chord. Its estimate rises
   97.43→98.75, but reference distance worsens 0→24 semitones and two untouched
   notes change. Lower-ranked alternatives change one note rather than two.
   Recommendation: evaluate polyphonic voice assignment and gate optional
   revoicing as a musical preference, not an inferred error. Test clean voicings
   broadly before altering ordinary 0%-preservation penalties.
2. **Initial candidate coverage gaps.** Exact reference field values are absent
   from initial generated options in many failing runs (377 candidate-generation
   diagnostic mentions). This observation does not establish whether the cause
   is evidence ranking, ornament protection, harmony confidence or bounds.
   Recommendation: add an optional production search trace, then test evidence-
   conditioned alternatives on calibration examples before widening all pools.
3. **Timing/duration recovery is limited.** Diagnostics contain 205 timing and
   168 duration coverage hypotheses. Most injected isolated displacement/length
   errors are not exactly restored. Some are musically ambiguous, and recovery
   may be impossible under a selected preset's bounds or locked permissions.
   Recommendation: distinguish technical attack/overlap errors from expressive
   timing; test reversible local alternatives within existing consent/bounds.
4. **Ranking does not equal reference recovery.** Some lower-ranked retained
   candidates are closer to truth; compatibility improvements can accompany
   collateral edits. Recommendation: calibrate clean-reference conservatism and
   preference/uncertainty handling, checking unnecessary edits independently from
   harmony gains. Do not optimize the ancillary distance penalty alone.
5. **Search budget and preservation effects need isolated tests.** Twelve search
   diagnostics identify exhausted budgets or unresolved search/scoring effects;
   nonzero penalties and locks explain many other non-repairs. Recommendation:
   compare the same cases across presets/settings with a trace API before changing
   weights or increasing budgets. More edits are not evidence of better repair.

Diagnostic counts are mentions, not disjoint failure counts. Low-confidence
harmony is associated with coverage gaps; no causal harmony-inference failure is
proven by those counts. Annotated chord-accuracy evaluation is a future extension.

## Reproduction and validation

```powershell
.venv\Scripts\python.exe -m glue.benchmark synthetic --output-dir .test-tmp/my-v051-references
.venv\Scripts\python.exe -m glue.benchmark run .test-tmp/my-v051-references/manifest.json --output-dir .test-tmp/my-v051-baseline --preservation 0 50 90 100 --seeds 17 --pair-preservation 100:0 0:100
.venv\Scripts\python.exe -m glue.benchmark run .test-tmp/my-v051-references/manifest.json --output-dir .test-tmp/my-v051-evaluation --split evaluation --preservation 0 50 90 100 --seeds 17 --pair-preservation 100:0 0:100
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .
git diff --check
.venv\Scripts\python.exe -m glue --smoke-test
.venv\Scripts\python.exe -m scripts.validate_v05 --output-dir .test-tmp/my-v051-gui-smoke
```

- Original baseline before changes: 272 tests passed; Ruff passed.
- Final suite: 310 tests passed (38 new benchmark tests); Ruff and diff check passed.
- A separate process reran all 684 calibration runs with identical deterministic
  results. Digest: `7c80a43f2567d272acedfe3cd976526458eb4d249d64d92f8861823ac5f52839`.
- Algorithm fingerprint: `b9f12bfccfcf879514ab116511e486b87a8ae2de1e7fee504f144618a22c4a7f`.
- Benchmark fingerprint: `c118a208386d9db92a2a2ebec18f00eede59bafcaf135e78e03d556dc6dde08f`.
- GUI launch smoke and V0.5 single/pair repair/export-reload smoke passed. Pitch-only,
  timing-only, duration-only, coordinated edits and intentional-material controls
  retain the prior behavior. No production GUI changes were made.

Tests cover deterministic corruption and seeds, every corruption kind, severity,
immutable originals and byte-preserved source MIDI, exact event bindings, metric
arithmetic, collateral-field penalties, clean false positives, motif damage,
POP/MAESTRO/reference adapters, splits/hashes/path safety, window identities,
single/pair runs, permission/lock behavior, blind invocation, reproducibility,
visible engine errors, reports, no-overwrite behavior and CLI smoke.

## Architecture and remaining limitations

`manifest` inventories and verifies local files/splits; `corrupt` creates copies
and ledgers; `metrics` evaluates source-identity-aligned notes; `runner` makes a
blind engine call and post-hoc diagnostics; `report` writes component reports and
matched comparisons; `synthetic` supplies self-authored validation references;
`__main__` exposes the offline CLI. No production module imports this package.

Remaining limitations: no real-dataset baseline, no listening/human ratings,
small corpus/one seed in recorded results, heuristic reference scale/sonority
and motif detection, no chord-annotation accuracy metric, window boundary/context
loss, manually reviewed near-duplicate grouping, skip-based note-count bounds,
private read-only candidate introspection, and platform-dependent timings. MIDI
corruptions are in memory plus exact JSON ledgers, not standalone exported files.

## Materially changed files

Modified:

- `README.md`, `pyproject.toml`, `src/glue/__init__.py`
- `tests/test_scaffold.py`, `tests/test_gui_v03.py`, `tests/test_repair_export.py`
  (only version expectations in these existing tests)

Added:

- `src/glue/benchmark/__init__.py`
- `src/glue/benchmark/__main__.py`
- `src/glue/benchmark/manifest.py`
- `src/glue/benchmark/corrupt.py`
- `src/glue/benchmark/metrics.py`
- `src/glue/benchmark/runner.py`
- `src/glue/benchmark/report.py`
- `src/glue/benchmark/synthetic.py`
- `tests/test_benchmark_data.py`, `tests/test_benchmark_runner.py`
- `docs/BENCHMARKING.md`, `docs/V051_BASELINE.md`
- `benchmarks/baselines/v051-synthetic/results.json`
- `benchmarks/baselines/v051-synthetic/results.csv`
- `benchmarks/baselines/v051-synthetic/summary.json`
- `benchmarks/baselines/v051-synthetic/summary.md`
- `benchmarks/baselines/v051-evaluation/results.json`
- `benchmarks/baselines/v051-evaluation/results.csv`
- `benchmarks/baselines/v051-evaluation/summary.json`
- `benchmarks/baselines/v051-evaluation/summary.md`

Ignored validation artifacts are under `.test-tmp`: generated synthetic MIDI and
manifest, the preliminary/repeat reports, GUI smoke exports/screenshots and pytest
temporary files. No raw `sample_data` files were modified. No commits or pushes.
