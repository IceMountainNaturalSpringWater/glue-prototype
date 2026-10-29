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
  "edit_type_diagnostics": {
    "duration": {
      "corrupted_fields": 240,
      "eligible_fields": 192,
      "candidate_recall": 0.0,
      "eligible_candidate_recall": 0.0,
      "failure_counts": {
        "correct_candidate_never_generated": 192,
        "blocked_by_permissions_or_lock": 48
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "correct_candidate_never_generated": 80.0
      },
      "category_percent_of_eligible_failures": {
        "correct_candidate_never_generated": 100.0
      },
      "analysis_failure_percent": null
    },
    "pitch": {
      "corrupted_fields": 300,
      "eligible_fields": 240,
      "candidate_recall": 0.46,
      "eligible_candidate_recall": 0.575,
      "failure_counts": {
        "correct_candidate_never_generated": 102,
        "blocked_by_permissions_or_lock": 60,
        "recovered": 11,
        "scoring_preferred_another_result": 36,
        "required_combination_not_discovered": 42,
        "correct_candidate_generated_but_pruned": 18,
        "constraint_or_budget_rejection": 31
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "constraint_or_budget_rejection": 10.333333333333334,
        "correct_candidate_generated_but_pruned": 6.0,
        "correct_candidate_never_generated": 34.0,
        "recovered": 3.6666666666666665,
        "required_combination_not_discovered": 14.0,
        "scoring_preferred_another_result": 12.0
      },
      "category_percent_of_eligible_failures": {
        "constraint_or_budget_rejection": 13.537117903930131,
        "correct_candidate_generated_but_pruned": 7.860262008733624,
        "correct_candidate_never_generated": 44.54148471615721,
        "required_combination_not_discovered": 18.34061135371179,
        "scoring_preferred_another_result": 15.720524017467248
      },
      "analysis_failure_percent": null
    },
    "timing": {
      "corrupted_fields": 300,
      "eligible_fields": 240,
      "candidate_recall": 0.013333333333333334,
      "eligible_candidate_recall": 0.016666666666666666,
      "failure_counts": {
        "correct_candidate_never_generated": 236,
        "blocked_by_permissions_or_lock": 60,
        "scoring_preferred_another_result": 3,
        "correct_candidate_generated_but_pruned": 1
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "correct_candidate_generated_but_pruned": 0.3333333333333333,
        "correct_candidate_never_generated": 78.66666666666667,
        "scoring_preferred_another_result": 1.0
      },
      "category_percent_of_eligible_failures": {
        "correct_candidate_generated_but_pruned": 0.4166666666666667,
        "correct_candidate_never_generated": 98.33333333333333,
        "scoring_preferred_another_result": 1.25
      },
      "analysis_failure_percent": null
    }
  },
  "runs": 540,
  "errors": 0,
  "corrupted_notes": 540,
  "partial_field_recovery": 0.013095238095238096,
  "corrupted_note_improvement_rate": 0.024074074074074074,
  "clean_pitch_edits": 18,
  "clean_timing_edits": 68,
  "clean_duration_edits": 4,
  "clean_octave_displacements": 0,
  "clean_octave_displacement_rate": 0.0,
  "clean_motif_disturbance_runs": 0,
  "exact_recovery_rate": 0.0,
  "unnecessary_edit_count": 765,
  "unnecessary_field_edits": 826,
  "clean_runs": 60,
  "clean_notes": 3210,
  "clean_false_positive_rate": 0.0264797507788162,
  "made_worse_runs": 214,
  "mean_runtime_seconds": 0.39688181481475043,
  "total_runtime_seconds": 214.31617999996524,
  "mean_distance_before": 2.2985026041666665,
  "mean_distance_after": 2.9591319444444446
}
```

Skipped/inapplicable cases: 0 (see JSON for reasons).

## By dataset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| pop909 | 540 | 0.0000 | 765 / 826 | 0.0265 | 214 | 0.3969 |

## By kind

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| accidental | 60 | 0.0000 | 85 / 102 | n/a | 25 | 0.4117 |
| attack_collision | 60 | 0.0000 | 88 / 92 | n/a | 24 | 0.3788 |
| clean | 60 | n/a | 85 / 90 | 0.0265 | 24 | 0.3968 |
| coordinated | 60 | 0.0000 | 80 / 81 | n/a | 19 | 0.4442 |
| early | 60 | 0.0000 | 84 / 89 | n/a | 24 | 0.3700 |
| octave | 60 | 0.0000 | 88 / 93 | n/a | 24 | 0.3881 |
| pitch_timing | 60 | 0.0000 | 93 / 101 | n/a | 26 | 0.4315 |
| short | 60 | 0.0000 | 81 / 88 | n/a | 24 | 0.3725 |
| sustain | 60 | 0.0000 | 81 / 90 | n/a | 24 | 0.3783 |

## By preset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| balanced | 180 | 0.0000 | 315 / 343 | 0.0327 | 88 | 0.4010 |
| creative | 180 | 0.0000 | 392 / 425 | 0.0411 | 88 | 0.7249 |
| minimal | 180 | 0.0000 | 58 / 58 | 0.0056 | 38 | 0.0648 |

## By preservation

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| (0, 0) | 108 | 0.0000 | 445 / 466 | 0.0763 | 100 | 0.6772 |
| (100, 100) | 108 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0071 |
| (25, 25) | 108 | 0.0000 | 273 / 313 | 0.0483 | 80 | 0.5529 |
| (50, 50) | 108 | 0.0000 | 47 / 47 | 0.0078 | 34 | 0.4365 |
| (75, 75) | 108 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.3108 |

## By workflow

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| pair | 540 | 0.0000 | 765 / 826 | 0.0265 | 214 | 0.3969 |

## Worst examples (distance + 10 × unnecessary field edits)

- 253/253.mid@60:68 / octave / creative / (0, 0): distance 12.000 → 14.750; 8 unnecessary field edits.
- 412/412.mid@220:228 / octave / creative / (0, 0): distance 12.000 → 12.975; 8 unnecessary field edits.
- 085/085.mid@152:160 / accidental / creative / (0, 0): distance 1.000 → 6.625; 8 unnecessary field edits.
- 085/085.mid@152:160 / octave / creative / (0, 0): distance 12.000 → 16.625; 7 unnecessary field edits.
- 253/253.mid@60:68 / pitch_timing / creative / (0, 0): distance 1.125 → 4.750; 8 unnecessary field edits.
- 412/412.mid@220:228 / pitch_timing / creative / (0, 0): distance 1.125 → 4.000; 8 unnecessary field edits.
- 412/412.mid@220:228 / accidental / creative / (0, 0): distance 1.000 → 3.875; 8 unnecessary field edits.
- 253/253.mid@60:68 / accidental / creative / (0, 0): distance 1.000 → 3.750; 8 unnecessary field edits.
- 253/253.mid@60:68 / sustain / creative / (0, 0): distance 0.500 → 3.250; 8 unnecessary field edits.
- 253/253.mid@60:68 / early / creative / (0, 0): distance 0.125 → 2.875; 8 unnecessary field edits.

## Failure attribution

Hypotheses are not proven causes. Coverage gaps are observed; their upstream cause
may be analysis, harmony inference, filtering or permissions. Search and scoring
cannot always be distinguished without a production trace API.

```json
{
  "scoring": 320,
  "analysis": 368,
  "candidate generation": 344,
  "harmony inference": 344,
  "preservation penalties": 396,
  "search": 166,
  "timing logic": 188,
  "duration logic": 144
}
```

See results.json for exact ledgers, source event bindings, component metrics,
retained-alternative diagnostics, failures, and runtime vs note count.

## Candidate recall and search outcomes by edit type

```json
{
  "duration": {
    "corrupted_fields": 240,
    "eligible_fields": 192,
    "candidate_recall": 0.0,
    "eligible_candidate_recall": 0.0,
    "failure_counts": {
      "correct_candidate_never_generated": 192,
      "blocked_by_permissions_or_lock": 48
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "correct_candidate_never_generated": 80.0
    },
    "category_percent_of_eligible_failures": {
      "correct_candidate_never_generated": 100.0
    },
    "analysis_failure_percent": null
  },
  "pitch": {
    "corrupted_fields": 300,
    "eligible_fields": 240,
    "candidate_recall": 0.46,
    "eligible_candidate_recall": 0.575,
    "failure_counts": {
      "correct_candidate_never_generated": 102,
      "blocked_by_permissions_or_lock": 60,
      "recovered": 11,
      "scoring_preferred_another_result": 36,
      "required_combination_not_discovered": 42,
      "correct_candidate_generated_but_pruned": 18,
      "constraint_or_budget_rejection": 31
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "constraint_or_budget_rejection": 10.333333333333334,
      "correct_candidate_generated_but_pruned": 6.0,
      "correct_candidate_never_generated": 34.0,
      "recovered": 3.6666666666666665,
      "required_combination_not_discovered": 14.0,
      "scoring_preferred_another_result": 12.0
    },
    "category_percent_of_eligible_failures": {
      "constraint_or_budget_rejection": 13.537117903930131,
      "correct_candidate_generated_but_pruned": 7.860262008733624,
      "correct_candidate_never_generated": 44.54148471615721,
      "required_combination_not_discovered": 18.34061135371179,
      "scoring_preferred_another_result": 15.720524017467248
    },
    "analysis_failure_percent": null
  },
  "timing": {
    "corrupted_fields": 300,
    "eligible_fields": 240,
    "candidate_recall": 0.013333333333333334,
    "eligible_candidate_recall": 0.016666666666666666,
    "failure_counts": {
      "correct_candidate_never_generated": 236,
      "blocked_by_permissions_or_lock": 60,
      "scoring_preferred_another_result": 3,
      "correct_candidate_generated_but_pruned": 1
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "correct_candidate_generated_but_pruned": 0.3333333333333333,
      "correct_candidate_never_generated": 78.66666666666667,
      "scoring_preferred_another_result": 1.0
    },
    "category_percent_of_eligible_failures": {
      "correct_candidate_generated_but_pruned": 0.4166666666666667,
      "correct_candidate_never_generated": 98.33333333333333,
      "scoring_preferred_another_result": 1.25
    },
    "analysis_failure_percent": null
  }
}
```

Full per-setting breakdowns are in summary.json; target ranks,
best component-scored states and rejection reasons are in results.json.
