# GLUE benchmark baseline

GLUE: 0.5.1
Algorithm SHA-256: `04e1428013ad46e2f3c0b2838429d5a841763db64a6ebf5221d7d16bc2c5df96`

Dataset: pop909; split: evaluation.
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
  "clean_pitch_edits": 17,
  "clean_timing_edits": 33,
  "clean_duration_edits": 4,
  "clean_octave_displacements": 0,
  "clean_octave_displacement_rate": 0.0,
  "clean_motif_disturbance_runs": 0,
  "exact_recovery_rate": null,
  "unnecessary_edit_count": 51,
  "unnecessary_field_edits": 54,
  "clean_runs": 60,
  "clean_notes": 2625,
  "clean_false_positive_rate": 0.019428571428571427,
  "made_worse_runs": 15,
  "mean_runtime_seconds": 0.2801813883331003,
  "total_runtime_seconds": 16.810883299986017,
  "mean_distance_before": null,
  "mean_distance_after": null
}
```

Skipped/inapplicable cases: 0 (see JSON for reasons).

## By dataset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| pop909 | 60 | n/a | 51 / 54 | 0.0194 | 15 | 0.2802 |

## By kind

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| clean | 60 | n/a | 51 / 54 | 0.0194 | 15 | 0.2802 |

## By preset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| balanced | 20 | n/a | 17 / 19 | 0.0194 | 5 | 0.2804 |
| creative | 20 | n/a | 28 / 29 | 0.0320 | 6 | 0.4947 |
| minimal | 20 | n/a | 6 / 6 | 0.0069 | 4 | 0.0655 |

## By preservation

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| (0, 0) | 12 | n/a | 34 / 37 | 0.0648 | 9 | 0.4622 |
| (100, 100) | 12 | n/a | 0 / 0 | 0.0000 | 0 | 0.0063 |
| (25, 25) | 12 | n/a | 17 / 17 | 0.0324 | 6 | 0.3846 |
| (50, 50) | 12 | n/a | 0 / 0 | 0.0000 | 0 | 0.3148 |
| (75, 75) | 12 | n/a | 0 / 0 | 0.0000 | 0 | 0.2330 |

## By workflow

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| pair | 60 | n/a | 51 / 54 | 0.0194 | 15 | 0.2802 |

## Worst examples (distance + 10 × unnecessary field edits)

- 865/865.mid@84:92 / clean / creative / (0, 0): distance 0.000 → 10.500; 8 unnecessary field edits.
- 496/496.mid@188:196 / clean / creative / (0, 0): distance 0.000 → 3.875; 8 unnecessary field edits.
- 496/496.mid@188:196 / clean / creative / (25, 25): distance 0.000 → 0.875; 7 unnecessary field edits.
- 496/496.mid@188:196 / clean / balanced / (0, 0): distance 0.000 → 1.625; 6 unnecessary field edits.
- 865/865.mid@84:92 / clean / balanced / (0, 0): distance 0.000 → 6.815; 5 unnecessary field edits.
- 496/496.mid@188:196 / clean / balanced / (25, 25): distance 0.000 → 0.625; 5 unnecessary field edits.
- 105/105.mid@312:320 / clean / creative / (0, 0): distance 0.000 → 2.250; 3 unnecessary field edits.
- 865/865.mid@84:92 / clean / minimal / (0, 0): distance 0.000 → 4.000; 2 unnecessary field edits.
- 105/105.mid@312:320 / clean / balanced / (0, 0): distance 0.000 → 2.250; 2 unnecessary field edits.
- 496/496.mid@188:196 / clean / minimal / (0, 0): distance 0.000 → 2.000; 2 unnecessary field edits.

## Failure attribution

Hypotheses are not proven causes. Coverage gaps are observed; their upstream cause
may be analysis, harmony inference, filtering or permissions. Search and scoring
cannot always be distinguished without a production trace API.

```json
{
  "scoring": 19,
  "analysis": 15
}
```

See results.json for exact ledgers, source event bindings, component metrics,
retained-alternative diagnostics, failures, and runtime vs note count.
