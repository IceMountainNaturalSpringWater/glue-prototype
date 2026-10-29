# GLUE benchmark baseline

GLUE: 0.5.1
Algorithm SHA-256: `b9f12bfccfcf879514ab116511e486b87a8ae2de1e7fee504f144618a22c4a7f`

Dataset: synthetic-framework-validation; split: evaluation.
Self-authored CC0 synthetic references; NOT POP909/MAESTRO results, not human-rated musical ground truth. Evaluation piece held out.

This measures recovery of designated references, not objective musical quality.
Top-ranked candidate only; no oracle selection or tuning. Clean controls are mandatory.
Timing is machine-dependent; deterministic digests exclude runtime/environment.

## Overall

```json
{
  "runs": 180,
  "errors": 0,
  "corrupted_notes": 180,
  "exact_recovery_rate": 0.0,
  "unnecessary_edit_count": 3,
  "unnecessary_field_edits": 3,
  "clean_runs": 12,
  "clean_notes": 96,
  "clean_false_positive_rate": 0.0,
  "made_worse_runs": 3,
  "mean_runtime_seconds": 0.003037981111053038,
  "total_runtime_seconds": 0.5468365999895468,
  "mean_distance_before": 1.6785714285714286,
  "mean_distance_after": 1.744047619047619
}
```

Skipped/inapplicable cases: 5 (see JSON for reasons).

## By kind

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| accidental | 12 | 0.0000 | 0 / 0 | n/a | 0 | 0.0027 |
| attack_collision | 12 | 0.0000 | 0 / 0 | n/a | 0 | 0.0024 |
| bass_pitch | 12 | 0.0000 | 0 / 0 | n/a | 0 | 0.0026 |
| clean | 12 | n/a | 0 / 0 | 0.0000 | 0 | 0.0028 |
| coordinated | 12 | 0.0000 | 0 / 0 | n/a | 0 | 0.0027 |
| early | 12 | 0.0000 | 0 / 0 | n/a | 0 | 0.0026 |
| groove | 12 | 0.0000 | 0 / 0 | n/a | 0 | 0.0024 |
| late | 12 | 0.0000 | 0 / 0 | n/a | 0 | 0.0024 |
| octave | 12 | 0.0000 | 3 / 3 | n/a | 3 | 0.0093 |
| pitch_duration | 12 | 0.0000 | 0 / 0 | n/a | 0 | 0.0026 |
| pitch_timing | 12 | 0.0000 | 0 / 0 | n/a | 0 | 0.0025 |
| short | 12 | 0.0000 | 0 / 0 | n/a | 0 | 0.0025 |
| sustain | 12 | 0.0000 | 0 / 0 | n/a | 0 | 0.0027 |
| timing_duration | 12 | 0.0000 | 0 / 0 | n/a | 0 | 0.0026 |
| wrong_diatonic | 12 | 0.0000 | 0 / 0 | n/a | 0 | 0.0027 |

## By preset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| balanced | 60 | 0.0000 | 1 / 1 | 0.0000 | 1 | 0.0031 |
| creative | 60 | 0.0000 | 1 / 1 | 0.0000 | 1 | 0.0031 |
| minimal | 60 | 0.0000 | 1 / 1 | 0.0000 | 1 | 0.0029 |

## By preservation

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| (0,) | 45 | 0.0000 | 3 / 3 | 0.0000 | 3 | 0.0033 |
| (100,) | 45 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0023 |
| (50,) | 45 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0033 |
| (90,) | 45 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0033 |

## By workflow

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| single | 180 | 0.0000 | 3 / 3 | 0.0000 | 3 | 0.0030 |

## Worst examples (distance + 10 × unnecessary field edits)

- intentional / octave / creative / (0,): distance 12.000 → 17.000; 1 unnecessary field edits.
- intentional / octave / balanced / (0,): distance 12.000 → 16.000; 1 unnecessary field edits.
- intentional / octave / minimal / (0,): distance 12.000 → 14.000; 1 unnecessary field edits.
- intentional / octave / balanced / (50,): distance 12.000 → 12.000; 0 unnecessary field edits.
- intentional / octave / balanced / (90,): distance 12.000 → 12.000; 0 unnecessary field edits.
- intentional / octave / balanced / (100,): distance 12.000 → 12.000; 0 unnecessary field edits.
- intentional / octave / creative / (50,): distance 12.000 → 12.000; 0 unnecessary field edits.
- intentional / octave / creative / (90,): distance 12.000 → 12.000; 0 unnecessary field edits.
- intentional / octave / creative / (100,): distance 12.000 → 12.000; 0 unnecessary field edits.
- intentional / octave / minimal / (50,): distance 12.000 → 12.000; 0 unnecessary field edits.

## Failure attribution

Hypotheses are not proven causes. Coverage gaps are observed; their upstream cause
may be analysis, harmony inference, filtering or permissions. Search and scoring
cannot always be distinguished without a production trace API.

```json
{
  "candidate generation": 126,
  "harmony inference": 126,
  "analysis": 126,
  "preservation penalties": 129,
  "scoring": 3,
  "timing logic": 63,
  "duration logic": 45
}
```

See results.json for exact ledgers, source event bindings, component metrics,
retained-alternative diagnostics, failures, and runtime vs note count.
