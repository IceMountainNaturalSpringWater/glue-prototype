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
  "edit_type_diagnostics": {
    "duration": {
      "corrupted_fields": 240,
      "eligible_fields": 192,
      "candidate_recall": 0.03333333333333333,
      "eligible_candidate_recall": 0.041666666666666664,
      "failure_counts": {
        "correct_candidate_never_generated": 184,
        "blocked_by_permissions_or_lock": 48,
        "scoring_preferred_another_result": 4,
        "generated_not_entered_search": 1,
        "required_combination_not_discovered": 3
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "correct_candidate_never_generated": 76.66666666666667,
        "generated_not_entered_search": 0.4166666666666667,
        "required_combination_not_discovered": 1.25,
        "scoring_preferred_another_result": 1.6666666666666667
      },
      "category_percent_of_eligible_failures": {
        "correct_candidate_never_generated": 95.83333333333333,
        "generated_not_entered_search": 0.5208333333333334,
        "required_combination_not_discovered": 1.5625,
        "scoring_preferred_another_result": 2.0833333333333335
      },
      "analysis_failure_percent": null
    },
    "pitch": {
      "corrupted_fields": 300,
      "eligible_fields": 240,
      "candidate_recall": 0.19,
      "eligible_candidate_recall": 0.2375,
      "failure_counts": {
        "correct_candidate_never_generated": 183,
        "blocked_by_permissions_or_lock": 60,
        "recovered": 12,
        "scoring_preferred_another_result": 17,
        "required_combination_not_discovered": 24,
        "constraint_or_budget_rejection": 4
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "constraint_or_budget_rejection": 1.3333333333333333,
        "correct_candidate_never_generated": 61.0,
        "recovered": 4.0,
        "required_combination_not_discovered": 8.0,
        "scoring_preferred_another_result": 5.666666666666667
      },
      "category_percent_of_eligible_failures": {
        "constraint_or_budget_rejection": 1.7543859649122806,
        "correct_candidate_never_generated": 80.26315789473684,
        "required_combination_not_discovered": 10.526315789473685,
        "scoring_preferred_another_result": 7.456140350877193
      },
      "analysis_failure_percent": null
    },
    "timing": {
      "corrupted_fields": 300,
      "eligible_fields": 240,
      "candidate_recall": 0.08,
      "eligible_candidate_recall": 0.1,
      "failure_counts": {
        "correct_candidate_never_generated": 216,
        "blocked_by_permissions_or_lock": 60,
        "required_combination_not_discovered": 20,
        "scoring_preferred_another_result": 2,
        "recovered": 2
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "correct_candidate_never_generated": 72.0,
        "recovered": 0.6666666666666666,
        "required_combination_not_discovered": 6.666666666666667,
        "scoring_preferred_another_result": 0.6666666666666666
      },
      "category_percent_of_eligible_failures": {
        "correct_candidate_never_generated": 90.75630252100841,
        "required_combination_not_discovered": 8.403361344537815,
        "scoring_preferred_another_result": 0.8403361344537815
      },
      "analysis_failure_percent": null
    }
  },
  "runs": 540,
  "errors": 0,
  "corrupted_notes": 540,
  "partial_field_recovery": 0.016666666666666666,
  "corrupted_note_improvement_rate": 0.025925925925925925,
  "clean_pitch_edits": 17,
  "clean_timing_edits": 33,
  "clean_duration_edits": 4,
  "clean_octave_displacements": 0,
  "clean_octave_displacement_rate": 0.0,
  "clean_motif_disturbance_runs": 0,
  "exact_recovery_rate": 0.001851851851851852,
  "unnecessary_edit_count": 478,
  "unnecessary_field_edits": 518,
  "clean_runs": 60,
  "clean_notes": 2625,
  "clean_false_positive_rate": 0.019428571428571427,
  "made_worse_runs": 142,
  "mean_runtime_seconds": 0.2917256025928105,
  "total_runtime_seconds": 157.53182540011767,
  "mean_distance_before": 2.3313802083333335,
  "mean_distance_after": 3.185078125
}
```

Skipped/inapplicable cases: 0 (see JSON for reasons).

## By dataset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| pop909 | 540 | 0.0019 | 478 / 518 | 0.0194 | 142 | 0.2917 |

## By kind

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| accidental | 60 | 0.0167 | 58 / 64 | n/a | 18 | 0.3200 |
| attack_collision | 60 | 0.0000 | 55 / 59 | n/a | 15 | 0.2923 |
| clean | 60 | n/a | 51 / 54 | 0.0194 | 15 | 0.2839 |
| coordinated | 60 | 0.0000 | 53 / 57 | n/a | 14 | 0.3104 |
| early | 60 | 0.0000 | 54 / 62 | n/a | 18 | 0.2787 |
| octave | 60 | 0.0000 | 52 / 56 | n/a | 16 | 0.2914 |
| pitch_timing | 60 | 0.0000 | 52 / 55 | n/a | 16 | 0.2967 |
| short | 60 | 0.0000 | 51 / 54 | n/a | 15 | 0.2754 |
| sustain | 60 | 0.0000 | 52 / 57 | n/a | 15 | 0.2768 |

## By preset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| balanced | 180 | 0.0056 | 166 / 188 | 0.0194 | 50 | 0.2957 |
| creative | 180 | 0.0000 | 259 / 277 | 0.0320 | 56 | 0.5111 |
| minimal | 180 | 0.0000 | 53 / 53 | 0.0069 | 36 | 0.0683 |

## By preservation

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| (0, 0) | 108 | 0.0093 | 323 / 352 | 0.0648 | 84 | 0.4918 |
| (100, 100) | 108 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0067 |
| (25, 25) | 108 | 0.0000 | 153 / 160 | 0.0324 | 56 | 0.4009 |
| (50, 50) | 108 | 0.0000 | 2 / 6 | 0.0000 | 2 | 0.3247 |
| (75, 75) | 108 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.2345 |

## By workflow

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| pair | 540 | 0.0019 | 478 / 518 | 0.0194 | 142 | 0.2917 |

## Worst examples (distance + 10 × unnecessary field edits)

- 865/865.mid@84:92 / octave / creative / (0, 0): distance 12.000 → 22.500; 8 unnecessary field edits.
- 496/496.mid@188:196 / octave / creative / (0, 0): distance 12.000 → 15.875; 8 unnecessary field edits.
- 496/496.mid@188:196 / octave / creative / (25, 25): distance 12.000 → 15.875; 8 unnecessary field edits.
- 496/496.mid@188:196 / coordinated / creative / (0, 0): distance 3.250 → 11.125; 8 unnecessary field edits.
- 865/865.mid@84:92 / attack_collision / creative / (0, 0): distance 0.500 → 11.000; 8 unnecessary field edits.
- 865/865.mid@84:92 / short / creative / (0, 0): distance 0.373 → 10.873; 8 unnecessary field edits.
- 865/865.mid@84:92 / early / creative / (0, 0): distance 0.125 → 10.625; 8 unnecessary field edits.
- 865/865.mid@84:92 / clean / creative / (0, 0): distance 0.000 → 10.500; 8 unnecessary field edits.
- 105/105.mid@312:320 / coordinated / creative / (0, 0): distance 3.250 → 27.375; 6 unnecessary field edits.
- 496/496.mid@188:196 / coordinated / creative / (25, 25): distance 3.250 → 7.125; 8 unnecessary field edits.

## Failure attribution

Hypotheses are not proven causes. Coverage gaps are observed; their upstream cause
may be analysis, harmony inference, filtering or permissions. Search and scoring
cannot always be distinguished without a production trace API.

```json
{
  "scoring": 210,
  "analysis": 389,
  "candidate generation": 374,
  "harmony inference": 374,
  "preservation penalties": 396,
  "search": 132,
  "timing logic": 176,
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
    "candidate_recall": 0.03333333333333333,
    "eligible_candidate_recall": 0.041666666666666664,
    "failure_counts": {
      "correct_candidate_never_generated": 184,
      "blocked_by_permissions_or_lock": 48,
      "scoring_preferred_another_result": 4,
      "generated_not_entered_search": 1,
      "required_combination_not_discovered": 3
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "correct_candidate_never_generated": 76.66666666666667,
      "generated_not_entered_search": 0.4166666666666667,
      "required_combination_not_discovered": 1.25,
      "scoring_preferred_another_result": 1.6666666666666667
    },
    "category_percent_of_eligible_failures": {
      "correct_candidate_never_generated": 95.83333333333333,
      "generated_not_entered_search": 0.5208333333333334,
      "required_combination_not_discovered": 1.5625,
      "scoring_preferred_another_result": 2.0833333333333335
    },
    "analysis_failure_percent": null
  },
  "pitch": {
    "corrupted_fields": 300,
    "eligible_fields": 240,
    "candidate_recall": 0.19,
    "eligible_candidate_recall": 0.2375,
    "failure_counts": {
      "correct_candidate_never_generated": 183,
      "blocked_by_permissions_or_lock": 60,
      "recovered": 12,
      "scoring_preferred_another_result": 17,
      "required_combination_not_discovered": 24,
      "constraint_or_budget_rejection": 4
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "constraint_or_budget_rejection": 1.3333333333333333,
      "correct_candidate_never_generated": 61.0,
      "recovered": 4.0,
      "required_combination_not_discovered": 8.0,
      "scoring_preferred_another_result": 5.666666666666667
    },
    "category_percent_of_eligible_failures": {
      "constraint_or_budget_rejection": 1.7543859649122806,
      "correct_candidate_never_generated": 80.26315789473684,
      "required_combination_not_discovered": 10.526315789473685,
      "scoring_preferred_another_result": 7.456140350877193
    },
    "analysis_failure_percent": null
  },
  "timing": {
    "corrupted_fields": 300,
    "eligible_fields": 240,
    "candidate_recall": 0.08,
    "eligible_candidate_recall": 0.1,
    "failure_counts": {
      "correct_candidate_never_generated": 216,
      "blocked_by_permissions_or_lock": 60,
      "required_combination_not_discovered": 20,
      "scoring_preferred_another_result": 2,
      "recovered": 2
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "correct_candidate_never_generated": 72.0,
      "recovered": 0.6666666666666666,
      "required_combination_not_discovered": 6.666666666666667,
      "scoring_preferred_another_result": 0.6666666666666666
    },
    "category_percent_of_eligible_failures": {
      "correct_candidate_never_generated": 90.75630252100841,
      "required_combination_not_discovered": 8.403361344537815,
      "scoring_preferred_another_result": 0.8403361344537815
    },
    "analysis_failure_percent": null
  }
}
```

Full per-setting breakdowns are in summary.json; target ranks,
best component-scored states and rejection reasons are in results.json.
