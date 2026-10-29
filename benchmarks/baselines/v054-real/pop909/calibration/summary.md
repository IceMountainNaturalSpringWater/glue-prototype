# GLUE benchmark baseline

GLUE: 0.5.4
Algorithm SHA-256: `a00c900cfe8da896d851a91a8d16a625da9c8204269e90b962cf66b993ed06c8`

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
      "candidate_recall": 0.2,
      "eligible_candidate_recall": 0.25,
      "failure_counts": {
        "correct_candidate_never_generated": 144,
        "blocked_by_permissions_or_lock": 48,
        "generated_not_entered_search": 20,
        "constraint_or_budget_rejection": 7,
        "recovered": 3,
        "scoring_preferred_another_result": 8,
        "required_combination_not_discovered": 10
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "constraint_or_budget_rejection": 2.9166666666666665,
        "correct_candidate_never_generated": 60.0,
        "generated_not_entered_search": 8.333333333333334,
        "recovered": 1.25,
        "required_combination_not_discovered": 4.166666666666667,
        "scoring_preferred_another_result": 3.3333333333333335
      },
      "category_percent_of_eligible_failures": {
        "constraint_or_budget_rejection": 3.7037037037037037,
        "correct_candidate_never_generated": 76.19047619047619,
        "generated_not_entered_search": 10.582010582010582,
        "required_combination_not_discovered": 5.291005291005291,
        "scoring_preferred_another_result": 4.232804232804233
      },
      "analysis_failure_percent": null
    },
    "pitch": {
      "corrupted_fields": 300,
      "eligible_fields": 240,
      "candidate_recall": 0.57,
      "eligible_candidate_recall": 0.7125,
      "failure_counts": {
        "correct_candidate_never_generated": 69,
        "blocked_by_permissions_or_lock": 60,
        "scoring_preferred_another_result": 49,
        "recovered": 14,
        "required_combination_not_discovered": 50,
        "correct_candidate_generated_but_pruned": 16,
        "constraint_or_budget_rejection": 40,
        "generated_not_entered_search": 2
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "constraint_or_budget_rejection": 13.333333333333334,
        "correct_candidate_generated_but_pruned": 5.333333333333333,
        "correct_candidate_never_generated": 23.0,
        "generated_not_entered_search": 0.6666666666666666,
        "recovered": 4.666666666666667,
        "required_combination_not_discovered": 16.666666666666668,
        "scoring_preferred_another_result": 16.333333333333332
      },
      "category_percent_of_eligible_failures": {
        "constraint_or_budget_rejection": 17.699115044247787,
        "correct_candidate_generated_but_pruned": 7.079646017699115,
        "correct_candidate_never_generated": 30.530973451327434,
        "generated_not_entered_search": 0.8849557522123894,
        "required_combination_not_discovered": 22.123893805309734,
        "scoring_preferred_another_result": 21.68141592920354
      },
      "analysis_failure_percent": null
    },
    "timing": {
      "corrupted_fields": 300,
      "eligible_fields": 240,
      "candidate_recall": 0.19666666666666666,
      "eligible_candidate_recall": 0.24583333333333332,
      "failure_counts": {
        "correct_candidate_never_generated": 181,
        "blocked_by_permissions_or_lock": 60,
        "scoring_preferred_another_result": 16,
        "correct_candidate_generated_but_pruned": 20,
        "required_combination_not_discovered": 22,
        "recovered": 1
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "correct_candidate_generated_but_pruned": 6.666666666666667,
        "correct_candidate_never_generated": 60.333333333333336,
        "recovered": 0.3333333333333333,
        "required_combination_not_discovered": 7.333333333333333,
        "scoring_preferred_another_result": 5.333333333333333
      },
      "category_percent_of_eligible_failures": {
        "correct_candidate_generated_but_pruned": 8.368200836820083,
        "correct_candidate_never_generated": 75.73221757322176,
        "required_combination_not_discovered": 9.205020920502092,
        "scoring_preferred_another_result": 6.694560669456067
      },
      "analysis_failure_percent": null
    }
  },
  "runs": 540,
  "errors": 0,
  "corrupted_notes": 540,
  "partial_field_recovery": 0.02142857142857143,
  "corrupted_note_improvement_rate": 0.03518518518518519,
  "clean_pitch_edits": 24,
  "clean_timing_edits": 4,
  "clean_duration_edits": 15,
  "clean_octave_displacements": 0,
  "clean_octave_displacement_rate": 0.0,
  "clean_motif_disturbance_runs": 0,
  "exact_recovery_rate": 0.001851851851851852,
  "unnecessary_edit_count": 382,
  "unnecessary_field_edits": 424,
  "clean_runs": 60,
  "clean_notes": 3210,
  "clean_false_positive_rate": 0.01277258566978193,
  "made_worse_runs": 127,
  "mean_runtime_seconds": 0.6327014903725487,
  "total_runtime_seconds": 341.6588048011763,
  "mean_distance_before": 2.2985026041666665,
  "mean_distance_after": 3.104509548611111
}
```

Skipped/inapplicable cases: 0 (see JSON for reasons).

## By dataset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| pop909 | 540 | 0.0019 | 382 / 424 | 0.0128 | 127 | 0.6327 |

## By kind

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| accidental | 60 | 0.0000 | 51 / 61 | n/a | 15 | 0.6523 |
| attack_collision | 60 | 0.0000 | 38 / 41 | n/a | 12 | 0.5973 |
| clean | 60 | n/a | 41 / 43 | 0.0128 | 14 | 0.5841 |
| coordinated | 60 | 0.0000 | 38 / 42 | n/a | 13 | 0.6827 |
| early | 60 | 0.0000 | 41 / 44 | n/a | 14 | 0.6609 |
| octave | 60 | 0.0000 | 42 / 44 | n/a | 14 | 0.6496 |
| pitch_timing | 60 | 0.0000 | 48 / 57 | n/a | 17 | 0.6467 |
| short | 60 | 0.0000 | 42 / 46 | n/a | 14 | 0.6123 |
| sustain | 60 | 0.0167 | 41 / 46 | n/a | 14 | 0.6084 |

## By preset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| balanced | 180 | 0.0000 | 137 / 154 | 0.0140 | 45 | 0.5645 |
| creative | 180 | 0.0056 | 189 / 214 | 0.0187 | 51 | 1.1931 |
| minimal | 180 | 0.0000 | 56 / 56 | 0.0056 | 31 | 0.1405 |

## By preservation

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| (0, 0) | 108 | 0.0093 | 344 / 385 | 0.0592 | 94 | 1.0709 |
| (100, 100) | 108 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0083 |
| (25, 25) | 108 | 0.0000 | 38 / 39 | 0.0047 | 33 | 0.8848 |
| (50, 50) | 108 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.7134 |
| (75, 75) | 108 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.4862 |

## By workflow

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| pair | 540 | 0.0019 | 382 / 424 | 0.0128 | 127 | 0.6327 |

## Worst examples (distance + 10 × unnecessary field edits)

- 412/412.mid@220:228 / accidental / creative / (0, 0): distance 1.000 → 8.250; 13 unnecessary field edits.
- 085/085.mid@152:160 / short / creative / (0, 0): distance 0.140 → 11.529; 8 unnecessary field edits.
- 085/085.mid@152:160 / accidental / creative / (0, 0): distance 1.000 → 8.665; 8 unnecessary field edits.
- 412/412.mid@220:228 / pitch_timing / creative / (0, 0): distance 1.125 → 7.681; 8 unnecessary field edits.
- 085/085.mid@152:160 / sustain / creative / (0, 0): distance 0.500 → 12.665; 7 unnecessary field edits.
- 253/253.mid@60:68 / pitch_timing / creative / (0, 0): distance 1.125 → 9.823; 7 unnecessary field edits.
- 412/412.mid@220:228 / octave / creative / (0, 0): distance 12.000 → 17.475; 6 unnecessary field edits.
- 412/412.mid@220:228 / early / creative / (0, 0): distance 0.125 → 6.725; 7 unnecessary field edits.
- 253/253.mid@60:68 / octave / creative / (0, 0): distance 12.000 → 15.200; 6 unnecessary field edits.
- 253/253.mid@60:68 / accidental / creative / (0, 0): distance 1.000 → 3.263; 7 unnecessary field edits.

## Failure attribution

Hypotheses are not proven causes. Coverage gaps are observed; their upstream cause
may be analysis, harmony inference, filtering or permissions. Search and scoring
cannot always be distinguished without a production trace API.

```json
{
  "scoring": 213,
  "analysis": 304,
  "candidate generation": 290,
  "harmony inference": 290,
  "preservation penalties": 396,
  "search": 187,
  "timing logic": 149,
  "duration logic": 120
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
    "candidate_recall": 0.2,
    "eligible_candidate_recall": 0.25,
    "failure_counts": {
      "correct_candidate_never_generated": 144,
      "blocked_by_permissions_or_lock": 48,
      "generated_not_entered_search": 20,
      "constraint_or_budget_rejection": 7,
      "recovered": 3,
      "scoring_preferred_another_result": 8,
      "required_combination_not_discovered": 10
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "constraint_or_budget_rejection": 2.9166666666666665,
      "correct_candidate_never_generated": 60.0,
      "generated_not_entered_search": 8.333333333333334,
      "recovered": 1.25,
      "required_combination_not_discovered": 4.166666666666667,
      "scoring_preferred_another_result": 3.3333333333333335
    },
    "category_percent_of_eligible_failures": {
      "constraint_or_budget_rejection": 3.7037037037037037,
      "correct_candidate_never_generated": 76.19047619047619,
      "generated_not_entered_search": 10.582010582010582,
      "required_combination_not_discovered": 5.291005291005291,
      "scoring_preferred_another_result": 4.232804232804233
    },
    "analysis_failure_percent": null
  },
  "pitch": {
    "corrupted_fields": 300,
    "eligible_fields": 240,
    "candidate_recall": 0.57,
    "eligible_candidate_recall": 0.7125,
    "failure_counts": {
      "correct_candidate_never_generated": 69,
      "blocked_by_permissions_or_lock": 60,
      "scoring_preferred_another_result": 49,
      "recovered": 14,
      "required_combination_not_discovered": 50,
      "correct_candidate_generated_but_pruned": 16,
      "constraint_or_budget_rejection": 40,
      "generated_not_entered_search": 2
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "constraint_or_budget_rejection": 13.333333333333334,
      "correct_candidate_generated_but_pruned": 5.333333333333333,
      "correct_candidate_never_generated": 23.0,
      "generated_not_entered_search": 0.6666666666666666,
      "recovered": 4.666666666666667,
      "required_combination_not_discovered": 16.666666666666668,
      "scoring_preferred_another_result": 16.333333333333332
    },
    "category_percent_of_eligible_failures": {
      "constraint_or_budget_rejection": 17.699115044247787,
      "correct_candidate_generated_but_pruned": 7.079646017699115,
      "correct_candidate_never_generated": 30.530973451327434,
      "generated_not_entered_search": 0.8849557522123894,
      "required_combination_not_discovered": 22.123893805309734,
      "scoring_preferred_another_result": 21.68141592920354
    },
    "analysis_failure_percent": null
  },
  "timing": {
    "corrupted_fields": 300,
    "eligible_fields": 240,
    "candidate_recall": 0.19666666666666666,
    "eligible_candidate_recall": 0.24583333333333332,
    "failure_counts": {
      "correct_candidate_never_generated": 181,
      "blocked_by_permissions_or_lock": 60,
      "scoring_preferred_another_result": 16,
      "correct_candidate_generated_but_pruned": 20,
      "required_combination_not_discovered": 22,
      "recovered": 1
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "correct_candidate_generated_but_pruned": 6.666666666666667,
      "correct_candidate_never_generated": 60.333333333333336,
      "recovered": 0.3333333333333333,
      "required_combination_not_discovered": 7.333333333333333,
      "scoring_preferred_another_result": 5.333333333333333
    },
    "category_percent_of_eligible_failures": {
      "correct_candidate_generated_but_pruned": 8.368200836820083,
      "correct_candidate_never_generated": 75.73221757322176,
      "required_combination_not_discovered": 9.205020920502092,
      "scoring_preferred_another_result": 6.694560669456067
    },
    "analysis_failure_percent": null
  }
}
```

Full per-setting breakdowns are in summary.json; target ranks,
best component-scored states and rejection reasons are in results.json.
