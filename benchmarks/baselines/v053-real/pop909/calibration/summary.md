# GLUE benchmark baseline

GLUE: 0.5.3
Algorithm SHA-256: `66e7374af98dc90556c96d64875d42803b7cea58f6b0a21149468cc7a9b98c53`

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
        "constraint_or_budget_rejection": 15,
        "generated_not_entered_search": 3,
        "recovered": 6,
        "scoring_preferred_another_result": 7,
        "correct_candidate_generated_but_pruned": 5,
        "required_combination_not_discovered": 12
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "constraint_or_budget_rejection": 6.25,
        "correct_candidate_generated_but_pruned": 2.0833333333333335,
        "correct_candidate_never_generated": 60.0,
        "generated_not_entered_search": 1.25,
        "recovered": 2.5,
        "required_combination_not_discovered": 5.0,
        "scoring_preferred_another_result": 2.9166666666666665
      },
      "category_percent_of_eligible_failures": {
        "constraint_or_budget_rejection": 8.064516129032258,
        "correct_candidate_generated_but_pruned": 2.6881720430107525,
        "correct_candidate_never_generated": 77.41935483870968,
        "generated_not_entered_search": 1.6129032258064515,
        "required_combination_not_discovered": 6.451612903225806,
        "scoring_preferred_another_result": 3.763440860215054
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
        "scoring_preferred_another_result": 43,
        "recovered": 18,
        "required_combination_not_discovered": 51,
        "correct_candidate_generated_but_pruned": 21,
        "constraint_or_budget_rejection": 37,
        "generated_not_entered_search": 1
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "constraint_or_budget_rejection": 12.333333333333334,
        "correct_candidate_generated_but_pruned": 7.0,
        "correct_candidate_never_generated": 23.0,
        "generated_not_entered_search": 0.3333333333333333,
        "recovered": 6.0,
        "required_combination_not_discovered": 17.0,
        "scoring_preferred_another_result": 14.333333333333334
      },
      "category_percent_of_eligible_failures": {
        "constraint_or_budget_rejection": 16.666666666666668,
        "correct_candidate_generated_but_pruned": 9.45945945945946,
        "correct_candidate_never_generated": 31.08108108108108,
        "generated_not_entered_search": 0.45045045045045046,
        "required_combination_not_discovered": 22.972972972972972,
        "scoring_preferred_another_result": 19.36936936936937
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
        "correct_candidate_generated_but_pruned": 10,
        "required_combination_not_discovered": 24,
        "generated_not_entered_search": 2,
        "constraint_or_budget_rejection": 7
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "constraint_or_budget_rejection": 2.3333333333333335,
        "correct_candidate_generated_but_pruned": 3.3333333333333335,
        "correct_candidate_never_generated": 60.333333333333336,
        "generated_not_entered_search": 0.6666666666666666,
        "required_combination_not_discovered": 8.0,
        "scoring_preferred_another_result": 5.333333333333333
      },
      "category_percent_of_eligible_failures": {
        "constraint_or_budget_rejection": 2.9166666666666665,
        "correct_candidate_generated_but_pruned": 4.166666666666667,
        "correct_candidate_never_generated": 75.41666666666667,
        "generated_not_entered_search": 0.8333333333333334,
        "required_combination_not_discovered": 10.0,
        "scoring_preferred_another_result": 6.666666666666667
      },
      "analysis_failure_percent": null
    }
  },
  "runs": 540,
  "errors": 0,
  "corrupted_notes": 540,
  "partial_field_recovery": 0.02857142857142857,
  "corrupted_note_improvement_rate": 0.040740740740740744,
  "clean_pitch_edits": 24,
  "clean_timing_edits": 23,
  "clean_duration_edits": 9,
  "clean_octave_displacements": 0,
  "clean_octave_displacement_rate": 0.0,
  "clean_motif_disturbance_runs": 0,
  "exact_recovery_rate": 0.001851851851851852,
  "unnecessary_edit_count": 470,
  "unnecessary_field_edits": 514,
  "clean_runs": 60,
  "clean_notes": 3210,
  "clean_false_positive_rate": 0.016822429906542057,
  "made_worse_runs": 156,
  "mean_runtime_seconds": 0.40078910018481245,
  "total_runtime_seconds": 216.42611409979872,
  "mean_distance_before": 2.2985026041666665,
  "mean_distance_after": 3.0606901041666665
}
```

Skipped/inapplicable cases: 0 (see JSON for reasons).

## By dataset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| pop909 | 540 | 0.0019 | 470 / 514 | 0.0168 | 156 | 0.4008 |

## By kind

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| accidental | 60 | 0.0000 | 54 / 67 | n/a | 18 | 0.4229 |
| attack_collision | 60 | 0.0000 | 52 / 54 | n/a | 15 | 0.3737 |
| clean | 60 | n/a | 54 / 56 | 0.0168 | 17 | 0.3910 |
| coordinated | 60 | 0.0000 | 44 / 48 | n/a | 16 | 0.4524 |
| early | 60 | 0.0000 | 50 / 55 | n/a | 17 | 0.3850 |
| octave | 60 | 0.0000 | 56 / 57 | n/a | 17 | 0.3809 |
| pitch_timing | 60 | 0.0000 | 57 / 66 | n/a | 22 | 0.4288 |
| short | 60 | 0.0000 | 51 / 54 | n/a | 17 | 0.3799 |
| sustain | 60 | 0.0167 | 52 / 57 | n/a | 17 | 0.3925 |

## By preset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| balanced | 180 | 0.0000 | 187 / 204 | 0.0206 | 56 | 0.3664 |
| creative | 180 | 0.0056 | 227 / 254 | 0.0243 | 69 | 0.7435 |
| minimal | 180 | 0.0000 | 56 / 56 | 0.0056 | 31 | 0.0924 |

## By preservation

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| (0, 0) | 108 | 0.0093 | 371 / 410 | 0.0685 | 96 | 0.6651 |
| (100, 100) | 108 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0071 |
| (25, 25) | 108 | 0.0000 | 91 / 96 | 0.0140 | 52 | 0.5540 |
| (50, 50) | 108 | 0.0000 | 8 / 8 | 0.0016 | 8 | 0.4543 |
| (75, 75) | 108 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.3234 |

## By workflow

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| pair | 540 | 0.0019 | 470 / 514 | 0.0168 | 156 | 0.4008 |

## Worst examples (distance + 10 × unnecessary field edits)

- 412/412.mid@220:228 / pitch_timing / creative / (0, 0): distance 1.125 → 10.375; 8 unnecessary field edits.
- 253/253.mid@60:68 / pitch_timing / creative / (0, 0): distance 1.125 → 8.844; 8 unnecessary field edits.
- 085/085.mid@152:160 / accidental / creative / (0, 0): distance 1.000 → 8.625; 8 unnecessary field edits.
- 085/085.mid@152:160 / octave / creative / (0, 0): distance 12.000 → 18.165; 7 unnecessary field edits.
- 412/412.mid@220:228 / octave / creative / (0, 0): distance 12.000 → 17.600; 7 unnecessary field edits.
- 412/412.mid@220:228 / accidental / creative / (0, 0): distance 1.000 → 7.500; 8 unnecessary field edits.
- 085/085.mid@152:160 / early / creative / (0, 0): distance 0.125 → 6.850; 8 unnecessary field edits.
- 085/085.mid@152:160 / clean / creative / (0, 0): distance 0.000 → 6.725; 8 unnecessary field edits.
- 412/412.mid@220:228 / octave / balanced / (0, 0): distance 12.000 → 18.317; 6 unnecessary field edits.
- 253/253.mid@60:68 / sustain / creative / (0, 0): distance 0.500 → 6.971; 7 unnecessary field edits.

## Failure attribution

Hypotheses are not proven causes. Coverage gaps are observed; their upstream cause
may be analysis, harmony inference, filtering or permissions. Search and scoring
cannot always be distinguished without a production trace API.

```json
{
  "scoring": 244,
  "analysis": 307,
  "candidate generation": 290,
  "harmony inference": 290,
  "preservation penalties": 396,
  "search": 167,
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
      "constraint_or_budget_rejection": 15,
      "generated_not_entered_search": 3,
      "recovered": 6,
      "scoring_preferred_another_result": 7,
      "correct_candidate_generated_but_pruned": 5,
      "required_combination_not_discovered": 12
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "constraint_or_budget_rejection": 6.25,
      "correct_candidate_generated_but_pruned": 2.0833333333333335,
      "correct_candidate_never_generated": 60.0,
      "generated_not_entered_search": 1.25,
      "recovered": 2.5,
      "required_combination_not_discovered": 5.0,
      "scoring_preferred_another_result": 2.9166666666666665
    },
    "category_percent_of_eligible_failures": {
      "constraint_or_budget_rejection": 8.064516129032258,
      "correct_candidate_generated_but_pruned": 2.6881720430107525,
      "correct_candidate_never_generated": 77.41935483870968,
      "generated_not_entered_search": 1.6129032258064515,
      "required_combination_not_discovered": 6.451612903225806,
      "scoring_preferred_another_result": 3.763440860215054
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
      "scoring_preferred_another_result": 43,
      "recovered": 18,
      "required_combination_not_discovered": 51,
      "correct_candidate_generated_but_pruned": 21,
      "constraint_or_budget_rejection": 37,
      "generated_not_entered_search": 1
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "constraint_or_budget_rejection": 12.333333333333334,
      "correct_candidate_generated_but_pruned": 7.0,
      "correct_candidate_never_generated": 23.0,
      "generated_not_entered_search": 0.3333333333333333,
      "recovered": 6.0,
      "required_combination_not_discovered": 17.0,
      "scoring_preferred_another_result": 14.333333333333334
    },
    "category_percent_of_eligible_failures": {
      "constraint_or_budget_rejection": 16.666666666666668,
      "correct_candidate_generated_but_pruned": 9.45945945945946,
      "correct_candidate_never_generated": 31.08108108108108,
      "generated_not_entered_search": 0.45045045045045046,
      "required_combination_not_discovered": 22.972972972972972,
      "scoring_preferred_another_result": 19.36936936936937
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
      "correct_candidate_generated_but_pruned": 10,
      "required_combination_not_discovered": 24,
      "generated_not_entered_search": 2,
      "constraint_or_budget_rejection": 7
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "constraint_or_budget_rejection": 2.3333333333333335,
      "correct_candidate_generated_but_pruned": 3.3333333333333335,
      "correct_candidate_never_generated": 60.333333333333336,
      "generated_not_entered_search": 0.6666666666666666,
      "required_combination_not_discovered": 8.0,
      "scoring_preferred_another_result": 5.333333333333333
    },
    "category_percent_of_eligible_failures": {
      "constraint_or_budget_rejection": 2.9166666666666665,
      "correct_candidate_generated_but_pruned": 4.166666666666667,
      "correct_candidate_never_generated": 75.41666666666667,
      "generated_not_entered_search": 0.8333333333333334,
      "required_combination_not_discovered": 10.0,
      "scoring_preferred_another_result": 6.666666666666667
    },
    "analysis_failure_percent": null
  }
}
```

Full per-setting breakdowns are in summary.json; target ranks,
best component-scored states and rejection reasons are in results.json.
