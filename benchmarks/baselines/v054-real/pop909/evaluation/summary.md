# GLUE benchmark baseline

GLUE: 0.5.4
Algorithm SHA-256: `a00c900cfe8da896d851a91a8d16a625da9c8204269e90b962cf66b993ed06c8`

Dataset: pop909; split: evaluation.
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
      "candidate_recall": 0.08333333333333333,
      "eligible_candidate_recall": 0.10416666666666667,
      "failure_counts": {
        "correct_candidate_never_generated": 172,
        "blocked_by_permissions_or_lock": 48,
        "generated_not_entered_search": 12,
        "scoring_preferred_another_result": 6,
        "required_combination_not_discovered": 2
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "correct_candidate_never_generated": 71.66666666666667,
        "generated_not_entered_search": 5.0,
        "required_combination_not_discovered": 0.8333333333333334,
        "scoring_preferred_another_result": 2.5
      },
      "category_percent_of_eligible_failures": {
        "correct_candidate_never_generated": 89.58333333333333,
        "generated_not_entered_search": 6.25,
        "required_combination_not_discovered": 1.0416666666666667,
        "scoring_preferred_another_result": 3.125
      },
      "analysis_failure_percent": null
    },
    "pitch": {
      "corrupted_fields": 300,
      "eligible_fields": 240,
      "candidate_recall": 0.4,
      "eligible_candidate_recall": 0.5,
      "failure_counts": {
        "correct_candidate_never_generated": 120,
        "blocked_by_permissions_or_lock": 60,
        "scoring_preferred_another_result": 41,
        "required_combination_not_discovered": 39,
        "constraint_or_budget_rejection": 19,
        "generated_not_entered_search": 5,
        "correct_candidate_generated_but_pruned": 3,
        "recovered": 13
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "constraint_or_budget_rejection": 6.333333333333333,
        "correct_candidate_generated_but_pruned": 1.0,
        "correct_candidate_never_generated": 40.0,
        "generated_not_entered_search": 1.6666666666666667,
        "recovered": 4.333333333333333,
        "required_combination_not_discovered": 13.0,
        "scoring_preferred_another_result": 13.666666666666666
      },
      "category_percent_of_eligible_failures": {
        "constraint_or_budget_rejection": 8.370044052863436,
        "correct_candidate_generated_but_pruned": 1.3215859030837005,
        "correct_candidate_never_generated": 52.863436123348016,
        "generated_not_entered_search": 2.202643171806167,
        "required_combination_not_discovered": 17.180616740088105,
        "scoring_preferred_another_result": 18.061674008810574
      },
      "analysis_failure_percent": null
    },
    "timing": {
      "corrupted_fields": 300,
      "eligible_fields": 240,
      "candidate_recall": 0.21,
      "eligible_candidate_recall": 0.2625,
      "failure_counts": {
        "correct_candidate_never_generated": 177,
        "blocked_by_permissions_or_lock": 60,
        "constraint_or_budget_rejection": 7,
        "scoring_preferred_another_result": 22,
        "correct_candidate_generated_but_pruned": 8,
        "recovered": 5,
        "required_combination_not_discovered": 17,
        "generated_not_entered_search": 4
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "constraint_or_budget_rejection": 2.3333333333333335,
        "correct_candidate_generated_but_pruned": 2.6666666666666665,
        "correct_candidate_never_generated": 59.0,
        "generated_not_entered_search": 1.3333333333333333,
        "recovered": 1.6666666666666667,
        "required_combination_not_discovered": 5.666666666666667,
        "scoring_preferred_another_result": 7.333333333333333
      },
      "category_percent_of_eligible_failures": {
        "constraint_or_budget_rejection": 2.978723404255319,
        "correct_candidate_generated_but_pruned": 3.404255319148936,
        "correct_candidate_never_generated": 75.31914893617021,
        "generated_not_entered_search": 1.702127659574468,
        "required_combination_not_discovered": 7.23404255319149,
        "scoring_preferred_another_result": 9.361702127659575
      },
      "analysis_failure_percent": null
    }
  },
  "runs": 540,
  "errors": 0,
  "corrupted_notes": 540,
  "partial_field_recovery": 0.02142857142857143,
  "corrupted_note_improvement_rate": 0.03518518518518519,
  "clean_pitch_edits": 35,
  "clean_timing_edits": 5,
  "clean_duration_edits": 13,
  "clean_octave_displacements": 0,
  "clean_octave_displacement_rate": 0.0,
  "clean_motif_disturbance_runs": 0,
  "exact_recovery_rate": 0.001851851851851852,
  "unnecessary_edit_count": 385,
  "unnecessary_field_edits": 465,
  "clean_runs": 60,
  "clean_notes": 2625,
  "clean_false_positive_rate": 0.016761904761904763,
  "made_worse_runs": 129,
  "mean_runtime_seconds": 0.48687193666959905,
  "total_runtime_seconds": 262.9108458015835,
  "mean_distance_before": 2.3313802083333335,
  "mean_distance_after": 3.7885286458333334
}
```

Skipped/inapplicable cases: 0 (see JSON for reasons).

## By dataset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| pop909 | 540 | 0.0019 | 385 / 465 | 0.0168 | 129 | 0.4869 |

## By kind

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| accidental | 60 | 0.0167 | 45 / 57 | n/a | 16 | 0.5064 |
| attack_collision | 60 | 0.0000 | 41 / 48 | n/a | 14 | 0.4376 |
| clean | 60 | n/a | 44 / 53 | 0.0168 | 14 | 0.4572 |
| coordinated | 60 | 0.0000 | 33 / 37 | n/a | 12 | 0.5489 |
| early | 60 | 0.0000 | 44 / 52 | n/a | 13 | 0.4517 |
| octave | 60 | 0.0000 | 55 / 62 | n/a | 18 | 0.4760 |
| pitch_timing | 60 | 0.0000 | 42 / 53 | n/a | 16 | 0.5503 |
| short | 60 | 0.0000 | 38 / 51 | n/a | 12 | 0.4720 |
| sustain | 60 | 0.0000 | 43 / 52 | n/a | 14 | 0.4816 |

## By preset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| balanced | 180 | 0.0000 | 145 / 184 | 0.0183 | 47 | 0.4525 |
| creative | 180 | 0.0056 | 183 / 223 | 0.0240 | 49 | 0.8807 |
| minimal | 180 | 0.0000 | 57 / 58 | 0.0080 | 33 | 0.1274 |

## By preservation

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| (0, 0) | 108 | 0.0093 | 326 / 388 | 0.0705 | 89 | 0.8321 |
| (100, 100) | 108 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0072 |
| (25, 25) | 108 | 0.0000 | 59 / 77 | 0.0133 | 40 | 0.6816 |
| (50, 50) | 108 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.5372 |
| (75, 75) | 108 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.3762 |

## By workflow

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| pair | 540 | 0.0019 | 385 / 465 | 0.0168 | 129 | 0.4869 |

## Worst examples (distance + 10 × unnecessary field edits)

- 496/496.mid@188:196 / octave / creative / (0, 0): distance 12.000 → 29.069; 8 unnecessary field edits.
- 865/865.mid@84:92 / octave / creative / (0, 0): distance 12.000 → 22.129; 8 unnecessary field edits.
- 496/496.mid@188:196 / attack_collision / creative / (0, 0): distance 0.250 → 15.000; 8 unnecessary field edits.
- 865/865.mid@84:92 / short / creative / (0, 0): distance 0.373 → 11.029; 8 unnecessary field edits.
- 865/865.mid@84:92 / sustain / creative / (0, 0): distance 0.500 → 10.750; 8 unnecessary field edits.
- 865/865.mid@84:92 / early / creative / (0, 0): distance 0.125 → 10.379; 8 unnecessary field edits.
- 865/865.mid@84:92 / clean / creative / (0, 0): distance 0.000 → 10.250; 8 unnecessary field edits.
- 496/496.mid@188:196 / pitch_timing / creative / (0, 0): distance 1.125 → 9.875; 8 unnecessary field edits.
- 496/496.mid@188:196 / accidental / creative / (0, 0): distance 1.000 → 9.750; 8 unnecessary field edits.
- 496/496.mid@188:196 / short / creative / (0, 0): distance 0.138 → 8.887; 8 unnecessary field edits.

## Failure attribution

Hypotheses are not proven causes. Coverage gaps are observed; their upstream cause
may be analysis, harmony inference, filtering or permissions. Search and scoring
cannot always be distinguished without a production trace API.

```json
{
  "scoring": 222,
  "analysis": 329,
  "candidate generation": 315,
  "harmony inference": 315,
  "preservation penalties": 396,
  "search": 168,
  "timing logic": 145,
  "duration logic": 136
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
    "candidate_recall": 0.08333333333333333,
    "eligible_candidate_recall": 0.10416666666666667,
    "failure_counts": {
      "correct_candidate_never_generated": 172,
      "blocked_by_permissions_or_lock": 48,
      "generated_not_entered_search": 12,
      "scoring_preferred_another_result": 6,
      "required_combination_not_discovered": 2
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "correct_candidate_never_generated": 71.66666666666667,
      "generated_not_entered_search": 5.0,
      "required_combination_not_discovered": 0.8333333333333334,
      "scoring_preferred_another_result": 2.5
    },
    "category_percent_of_eligible_failures": {
      "correct_candidate_never_generated": 89.58333333333333,
      "generated_not_entered_search": 6.25,
      "required_combination_not_discovered": 1.0416666666666667,
      "scoring_preferred_another_result": 3.125
    },
    "analysis_failure_percent": null
  },
  "pitch": {
    "corrupted_fields": 300,
    "eligible_fields": 240,
    "candidate_recall": 0.4,
    "eligible_candidate_recall": 0.5,
    "failure_counts": {
      "correct_candidate_never_generated": 120,
      "blocked_by_permissions_or_lock": 60,
      "scoring_preferred_another_result": 41,
      "required_combination_not_discovered": 39,
      "constraint_or_budget_rejection": 19,
      "generated_not_entered_search": 5,
      "correct_candidate_generated_but_pruned": 3,
      "recovered": 13
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "constraint_or_budget_rejection": 6.333333333333333,
      "correct_candidate_generated_but_pruned": 1.0,
      "correct_candidate_never_generated": 40.0,
      "generated_not_entered_search": 1.6666666666666667,
      "recovered": 4.333333333333333,
      "required_combination_not_discovered": 13.0,
      "scoring_preferred_another_result": 13.666666666666666
    },
    "category_percent_of_eligible_failures": {
      "constraint_or_budget_rejection": 8.370044052863436,
      "correct_candidate_generated_but_pruned": 1.3215859030837005,
      "correct_candidate_never_generated": 52.863436123348016,
      "generated_not_entered_search": 2.202643171806167,
      "required_combination_not_discovered": 17.180616740088105,
      "scoring_preferred_another_result": 18.061674008810574
    },
    "analysis_failure_percent": null
  },
  "timing": {
    "corrupted_fields": 300,
    "eligible_fields": 240,
    "candidate_recall": 0.21,
    "eligible_candidate_recall": 0.2625,
    "failure_counts": {
      "correct_candidate_never_generated": 177,
      "blocked_by_permissions_or_lock": 60,
      "constraint_or_budget_rejection": 7,
      "scoring_preferred_another_result": 22,
      "correct_candidate_generated_but_pruned": 8,
      "recovered": 5,
      "required_combination_not_discovered": 17,
      "generated_not_entered_search": 4
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "constraint_or_budget_rejection": 2.3333333333333335,
      "correct_candidate_generated_but_pruned": 2.6666666666666665,
      "correct_candidate_never_generated": 59.0,
      "generated_not_entered_search": 1.3333333333333333,
      "recovered": 1.6666666666666667,
      "required_combination_not_discovered": 5.666666666666667,
      "scoring_preferred_another_result": 7.333333333333333
    },
    "category_percent_of_eligible_failures": {
      "constraint_or_budget_rejection": 2.978723404255319,
      "correct_candidate_generated_but_pruned": 3.404255319148936,
      "correct_candidate_never_generated": 75.31914893617021,
      "generated_not_entered_search": 1.702127659574468,
      "required_combination_not_discovered": 7.23404255319149,
      "scoring_preferred_another_result": 9.361702127659575
    },
    "analysis_failure_percent": null
  }
}
```

Full per-setting breakdowns are in summary.json; target ranks,
best component-scored states and rejection reasons are in results.json.
