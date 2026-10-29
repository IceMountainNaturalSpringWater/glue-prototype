# GLUE benchmark baseline

GLUE: 0.5.1
Algorithm SHA-256: `04e1428013ad46e2f3c0b2838429d5a841763db64a6ebf5221d7d16bc2c5df96`

Dataset: pop909; split: calibration.
User-supplied references; quality and licensing require human review.

This measures recovery of designated references, not objective musical quality.
Top-ranked candidate only; no oracle selection or tuning. Clean controls are mandatory.
Timing is machine-dependent; deterministic digests exclude runtime/environment.

## Overall

```json
{
  "edit_type_diagnostics": {},
  "runs": 60,
  "errors": 0,
  "corrupted_notes": 0,
  "partial_field_recovery": null,
  "corrupted_note_improvement_rate": null,
  "clean_pitch_edits": 18,
  "clean_timing_edits": 68,
  "clean_duration_edits": 4,
  "clean_octave_displacements": 0,
  "clean_octave_displacement_rate": 0.0,
  "clean_motif_disturbance_runs": 0,
  "exact_recovery_rate": null,
  "unnecessary_edit_count": 85,
  "unnecessary_field_edits": 90,
  "clean_runs": 60,
  "clean_notes": 3210,
  "clean_false_positive_rate": 0.0264797507788162,
  "made_worse_runs": 24,
  "mean_runtime_seconds": 0.39297790500010404,
  "total_runtime_seconds": 23.57867430000624,
  "mean_distance_before": null,
  "mean_distance_after": null
}
```

Skipped/inapplicable cases: 0 (see JSON for reasons).

## By dataset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| pop909 | 60 | n/a | 85 / 90 | 0.0265 | 24 | 0.3930 |

## By kind

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| clean | 60 | n/a | 85 / 90 | 0.0265 | 24 | 0.3930 |

## By preset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| balanced | 20 | n/a | 35 / 37 | 0.0327 | 10 | 0.4195 |
| creative | 20 | n/a | 44 / 47 | 0.0411 | 10 | 0.7079 |
| minimal | 20 | n/a | 6 / 6 | 0.0056 | 4 | 0.0515 |

## By preservation

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| (0, 0) | 12 | n/a | 49 / 50 | 0.0763 | 11 | 0.6847 |
| (100, 100) | 12 | n/a | 0 / 0 | 0.0000 | 0 | 0.0077 |
| (25, 25) | 12 | n/a | 31 / 35 | 0.0483 | 9 | 0.5520 |
| (50, 50) | 12 | n/a | 5 / 5 | 0.0078 | 4 | 0.4256 |
| (75, 75) | 12 | n/a | 0 / 0 | 0.0000 | 0 | 0.2949 |

## By workflow

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| pair | 60 | n/a | 85 / 90 | 0.0265 | 24 | 0.3930 |

## Worst examples (distance + 10 × unnecessary field edits)

- 253/253.mid@60:68 / clean / creative / (0, 0): distance 0.000 → 2.750; 8 unnecessary field edits.
- 085/085.mid@152:160 / clean / creative / (0, 0): distance 0.000 → 4.625; 7 unnecessary field edits.
- 412/412.mid@220:228 / clean / creative / (0, 0): distance 0.000 → 1.750; 7 unnecessary field edits.
- 253/253.mid@60:68 / clean / balanced / (0, 0): distance 0.000 → 4.625; 6 unnecessary field edits.
- 253/253.mid@60:68 / clean / creative / (25, 25): distance 0.000 → 2.625; 6 unnecessary field edits.
- 085/085.mid@152:160 / clean / balanced / (0, 0): distance 0.000 → 2.625; 5 unnecessary field edits.
- 412/412.mid@220:228 / clean / balanced / (0, 0): distance 0.000 → 1.500; 5 unnecessary field edits.
- 085/085.mid@152:160 / clean / balanced / (25, 25): distance 0.000 → 0.750; 5 unnecessary field edits.
- 085/085.mid@152:160 / clean / creative / (25, 25): distance 0.000 → 0.625; 5 unnecessary field edits.
- 253/253.mid@60:68 / clean / balanced / (25, 25): distance 0.000 → 0.625; 5 unnecessary field edits.

## Failure attribution

Hypotheses are not proven causes. Coverage gaps are observed; their upstream cause
may be analysis, harmony inference, filtering or permissions. Search and scoring
cannot always be distinguished without a production trace API.

```json
{
  "scoring": 34,
  "analysis": 24
}
```

See results.json for exact ledgers, source event bindings, component metrics,
retained-alternative diagnostics, failures, and runtime vs note count.
