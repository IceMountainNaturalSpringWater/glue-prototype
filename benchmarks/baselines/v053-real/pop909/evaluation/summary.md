# GLUE benchmark baseline

GLUE: 0.5.3
Algorithm SHA-256: `66e7374af98dc90556c96d64875d42803b7cea58f6b0a21149468cc7a9b98c53`

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
        "scoring_preferred_another_result": 11,
        "required_combination_not_discovered": 8,
        "generated_not_entered_search": 1
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "correct_candidate_never_generated": 71.66666666666667,
        "generated_not_entered_search": 0.4166666666666667,
        "required_combination_not_discovered": 3.3333333333333335,
        "scoring_preferred_another_result": 4.583333333333333
      },
      "category_percent_of_eligible_failures": {
        "correct_candidate_never_generated": 89.58333333333333,
        "generated_not_entered_search": 0.5208333333333334,
        "required_combination_not_discovered": 4.166666666666667,
        "scoring_preferred_another_result": 5.729166666666667
      },
      "analysis_failure_percent": null
    },
    "pitch": {
      "corrupted_fields": 300,
      "eligible_fields": 240,
      "candidate_recall": 0.4066666666666667,
      "eligible_candidate_recall": 0.5083333333333333,
      "failure_counts": {
        "correct_candidate_never_generated": 118,
        "blocked_by_permissions_or_lock": 60,
        "scoring_preferred_another_result": 43,
        "required_combination_not_discovered": 42,
        "constraint_or_budget_rejection": 20,
        "correct_candidate_generated_but_pruned": 5,
        "recovered": 12
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "constraint_or_budget_rejection": 6.666666666666667,
        "correct_candidate_generated_but_pruned": 1.6666666666666667,
        "correct_candidate_never_generated": 39.333333333333336,
        "recovered": 4.0,
        "required_combination_not_discovered": 14.0,
        "scoring_preferred_another_result": 14.333333333333334
      },
      "category_percent_of_eligible_failures": {
        "constraint_or_budget_rejection": 8.771929824561404,
        "correct_candidate_generated_but_pruned": 2.192982456140351,
        "correct_candidate_never_generated": 51.75438596491228,
        "required_combination_not_discovered": 18.42105263157895,
        "scoring_preferred_another_result": 18.859649122807017
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
        "scoring_preferred_another_result": 20,
        "correct_candidate_generated_but_pruned": 10,
        "generated_not_entered_search": 8,
        "required_combination_not_discovered": 18
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "constraint_or_budget_rejection": 2.3333333333333335,
        "correct_candidate_generated_but_pruned": 3.3333333333333335,
        "correct_candidate_never_generated": 59.0,
        "generated_not_entered_search": 2.6666666666666665,
        "required_combination_not_discovered": 6.0,
        "scoring_preferred_another_result": 6.666666666666667
      },
      "category_percent_of_eligible_failures": {
        "constraint_or_budget_rejection": 2.9166666666666665,
        "correct_candidate_generated_but_pruned": 4.166666666666667,
        "correct_candidate_never_generated": 73.75,
        "generated_not_entered_search": 3.3333333333333335,
        "required_combination_not_discovered": 7.5,
        "scoring_preferred_another_result": 8.333333333333334
      },
      "analysis_failure_percent": null
    }
  },
  "runs": 540,
  "errors": 0,
  "corrupted_notes": 540,
  "partial_field_recovery": 0.014285714285714285,
  "corrupted_note_improvement_rate": 0.025925925925925925,
  "clean_pitch_edits": 30,
  "clean_timing_edits": 18,
  "clean_duration_edits": 8,
  "clean_octave_displacements": 0,
  "clean_octave_displacement_rate": 0.0,
  "clean_motif_disturbance_runs": 0,
  "exact_recovery_rate": 0.0,
  "unnecessary_edit_count": 450,
  "unnecessary_field_edits": 506,
  "clean_runs": 60,
  "clean_notes": 2625,
  "clean_false_positive_rate": 0.01904761904761905,
  "made_worse_runs": 115,
  "mean_runtime_seconds": 0.3548647299984522,
  "total_runtime_seconds": 191.62695419916417,
  "mean_distance_before": 2.3313802083333335,
  "mean_distance_after": 3.5317925347222223
}
```

Skipped/inapplicable cases: 0 (see JSON for reasons).

## By dataset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| pop909 | 540 | 0.0000 | 450 / 506 | 0.0190 | 115 | 0.3549 |

## By kind

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| accidental | 60 | 0.0000 | 52 / 60 | n/a | 14 | 0.3803 |
| attack_collision | 60 | 0.0000 | 50 / 56 | n/a | 14 | 0.3206 |
| clean | 60 | n/a | 50 / 56 | 0.0190 | 12 | 0.3442 |
| coordinated | 60 | 0.0000 | 49 / 51 | n/a | 11 | 0.3862 |
| early | 60 | 0.0000 | 50 / 54 | n/a | 12 | 0.3146 |
| octave | 60 | 0.0000 | 53 / 59 | n/a | 14 | 0.3622 |
| pitch_timing | 60 | 0.0000 | 50 / 58 | n/a | 14 | 0.3839 |
| short | 60 | 0.0000 | 47 / 56 | n/a | 12 | 0.3372 |
| sustain | 60 | 0.0000 | 49 / 56 | n/a | 12 | 0.3647 |

## By preset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| balanced | 180 | 0.0000 | 169 / 197 | 0.0217 | 40 | 0.3404 |
| creative | 180 | 0.0000 | 222 / 249 | 0.0274 | 40 | 0.6332 |
| minimal | 180 | 0.0000 | 59 / 60 | 0.0080 | 35 | 0.0910 |

## By preservation

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| (0, 0) | 108 | 0.0000 | 352 / 384 | 0.0743 | 88 | 0.5972 |
| (100, 100) | 108 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0064 |
| (25, 25) | 108 | 0.0000 | 98 / 122 | 0.0210 | 27 | 0.4916 |
| (50, 50) | 108 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.3976 |
| (75, 75) | 108 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.2816 |

## By workflow

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| pair | 540 | 0.0000 | 450 / 506 | 0.0190 | 115 | 0.3549 |

## Worst examples (distance + 10 × unnecessary field edits)

- 105/105.mid@312:320 / coordinated / creative / (0, 0): distance 3.250 → 35.250; 7 unnecessary field edits.
- 865/865.mid@84:92 / octave / creative / (0, 0): distance 12.000 → 20.902; 8 unnecessary field edits.
- 496/496.mid@188:196 / octave / creative / (0, 0): distance 12.000 → 18.625; 8 unnecessary field edits.
- 865/865.mid@84:92 / attack_collision / creative / (0, 0): distance 0.500 → 13.277; 8 unnecessary field edits.
- 496/496.mid@188:196 / coordinated / creative / (0, 0): distance 3.250 → 9.875; 8 unnecessary field edits.
- 865/865.mid@84:92 / sustain / creative / (0, 0): distance 0.500 → 9.402; 8 unnecessary field edits.
- 865/865.mid@84:92 / short / creative / (0, 0): distance 0.373 → 9.275; 8 unnecessary field edits.
- 865/865.mid@84:92 / early / creative / (0, 0): distance 0.125 → 9.031; 8 unnecessary field edits.
- 865/865.mid@84:92 / clean / creative / (0, 0): distance 0.000 → 8.902; 8 unnecessary field edits.
- 496/496.mid@188:196 / pitch_timing / creative / (0, 0): distance 1.125 → 7.750; 8 unnecessary field edits.

## Failure attribution

Hypotheses are not proven causes. Coverage gaps are observed; their upstream cause
may be analysis, harmony inference, filtering or permissions. Search and scoring
cannot always be distinguished without a production trace API.

```json
{
  "scoring": 204,
  "analysis": 326,
  "candidate generation": 314,
  "harmony inference": 314,
  "preservation penalties": 396,
  "search": 169,
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
      "scoring_preferred_another_result": 11,
      "required_combination_not_discovered": 8,
      "generated_not_entered_search": 1
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "correct_candidate_never_generated": 71.66666666666667,
      "generated_not_entered_search": 0.4166666666666667,
      "required_combination_not_discovered": 3.3333333333333335,
      "scoring_preferred_another_result": 4.583333333333333
    },
    "category_percent_of_eligible_failures": {
      "correct_candidate_never_generated": 89.58333333333333,
      "generated_not_entered_search": 0.5208333333333334,
      "required_combination_not_discovered": 4.166666666666667,
      "scoring_preferred_another_result": 5.729166666666667
    },
    "analysis_failure_percent": null
  },
  "pitch": {
    "corrupted_fields": 300,
    "eligible_fields": 240,
    "candidate_recall": 0.4066666666666667,
    "eligible_candidate_recall": 0.5083333333333333,
    "failure_counts": {
      "correct_candidate_never_generated": 118,
      "blocked_by_permissions_or_lock": 60,
      "scoring_preferred_another_result": 43,
      "required_combination_not_discovered": 42,
      "constraint_or_budget_rejection": 20,
      "correct_candidate_generated_but_pruned": 5,
      "recovered": 12
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "constraint_or_budget_rejection": 6.666666666666667,
      "correct_candidate_generated_but_pruned": 1.6666666666666667,
      "correct_candidate_never_generated": 39.333333333333336,
      "recovered": 4.0,
      "required_combination_not_discovered": 14.0,
      "scoring_preferred_another_result": 14.333333333333334
    },
    "category_percent_of_eligible_failures": {
      "constraint_or_budget_rejection": 8.771929824561404,
      "correct_candidate_generated_but_pruned": 2.192982456140351,
      "correct_candidate_never_generated": 51.75438596491228,
      "required_combination_not_discovered": 18.42105263157895,
      "scoring_preferred_another_result": 18.859649122807017
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
      "scoring_preferred_another_result": 20,
      "correct_candidate_generated_but_pruned": 10,
      "generated_not_entered_search": 8,
      "required_combination_not_discovered": 18
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "constraint_or_budget_rejection": 2.3333333333333335,
      "correct_candidate_generated_but_pruned": 3.3333333333333335,
      "correct_candidate_never_generated": 59.0,
      "generated_not_entered_search": 2.6666666666666665,
      "required_combination_not_discovered": 6.0,
      "scoring_preferred_another_result": 6.666666666666667
    },
    "category_percent_of_eligible_failures": {
      "constraint_or_budget_rejection": 2.9166666666666665,
      "correct_candidate_generated_but_pruned": 4.166666666666667,
      "correct_candidate_never_generated": 73.75,
      "generated_not_entered_search": 3.3333333333333335,
      "required_combination_not_discovered": 7.5,
      "scoring_preferred_another_result": 8.333333333333334
    },
    "analysis_failure_percent": null
  }
}
```

Full per-setting breakdowns are in summary.json; target ranks,
best component-scored states and rejection reasons are in results.json.
