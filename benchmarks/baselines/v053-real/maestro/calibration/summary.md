# GLUE benchmark baseline

GLUE: 0.5.3
Algorithm SHA-256: `66e7374af98dc90556c96d64875d42803b7cea58f6b0a21149468cc7a9b98c53`

Dataset: maestro; split: calibration.
User-supplied references; quality and licensing require human review.

This measures recovery of designated references, not objective musical quality.
Top-ranked candidate only; no oracle selection or tuning. Clean controls are mandatory.
Timing is machine-dependent; deterministic digests exclude runtime/environment.

## Overall

```json
{
  "edit_type_diagnostics": {
    "duration": {
      "corrupted_fields": 300,
      "eligible_fields": 240,
      "candidate_recall": 0.013333333333333334,
      "eligible_candidate_recall": 0.016666666666666666,
      "failure_counts": {
        "correct_candidate_never_generated": 236,
        "blocked_by_permissions_or_lock": 60,
        "scoring_preferred_another_result": 1,
        "required_combination_not_discovered": 3
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "correct_candidate_never_generated": 78.66666666666667,
        "required_combination_not_discovered": 1.0,
        "scoring_preferred_another_result": 0.3333333333333333
      },
      "category_percent_of_eligible_failures": {
        "correct_candidate_never_generated": 98.33333333333333,
        "required_combination_not_discovered": 1.25,
        "scoring_preferred_another_result": 0.4166666666666667
      },
      "analysis_failure_percent": null
    },
    "pitch": {
      "corrupted_fields": 240,
      "eligible_fields": 192,
      "candidate_recall": 0.21666666666666667,
      "eligible_candidate_recall": 0.2708333333333333,
      "failure_counts": {
        "correct_candidate_never_generated": 140,
        "blocked_by_permissions_or_lock": 48,
        "scoring_preferred_another_result": 14,
        "required_combination_not_discovered": 21,
        "recovered": 4,
        "correct_candidate_generated_but_pruned": 1,
        "constraint_or_budget_rejection": 12
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "constraint_or_budget_rejection": 5.0,
        "correct_candidate_generated_but_pruned": 0.4166666666666667,
        "correct_candidate_never_generated": 58.333333333333336,
        "recovered": 1.6666666666666667,
        "required_combination_not_discovered": 8.75,
        "scoring_preferred_another_result": 5.833333333333333
      },
      "category_percent_of_eligible_failures": {
        "constraint_or_budget_rejection": 6.382978723404255,
        "correct_candidate_generated_but_pruned": 0.5319148936170213,
        "correct_candidate_never_generated": 74.46808510638297,
        "required_combination_not_discovered": 11.170212765957446,
        "scoring_preferred_another_result": 7.446808510638298
      },
      "analysis_failure_percent": null
    },
    "timing": {
      "corrupted_fields": 360,
      "eligible_fields": 288,
      "candidate_recall": 0.030555555555555555,
      "eligible_candidate_recall": 0.03819444444444445,
      "failure_counts": {
        "correct_candidate_never_generated": 277,
        "blocked_by_permissions_or_lock": 72,
        "required_combination_not_discovered": 8,
        "correct_candidate_generated_but_pruned": 3
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "correct_candidate_generated_but_pruned": 0.8333333333333334,
        "correct_candidate_never_generated": 76.94444444444444,
        "required_combination_not_discovered": 2.2222222222222223
      },
      "category_percent_of_eligible_failures": {
        "correct_candidate_generated_but_pruned": 1.0416666666666667,
        "correct_candidate_never_generated": 96.18055555555556,
        "required_combination_not_discovered": 2.7777777777777777
      },
      "analysis_failure_percent": null
    }
  },
  "runs": 600,
  "errors": 0,
  "corrupted_notes": 600,
  "partial_field_recovery": 0.0044444444444444444,
  "corrupted_note_improvement_rate": 0.008333333333333333,
  "clean_pitch_edits": 28,
  "clean_timing_edits": 0,
  "clean_duration_edits": 0,
  "clean_octave_displacements": 0,
  "clean_octave_displacement_rate": 0.0,
  "clean_motif_disturbance_runs": 0,
  "exact_recovery_rate": 0.0,
  "unnecessary_edit_count": 276,
  "unnecessary_field_edits": 282,
  "clean_runs": 60,
  "clean_notes": 1680,
  "clean_false_positive_rate": 0.016666666666666666,
  "made_worse_runs": 87,
  "mean_runtime_seconds": 0.2529507261663093,
  "total_runtime_seconds": 151.7704356997856,
  "mean_distance_before": 2.000101273148148,
  "mean_distance_after": 2.9714400077160494
}
```

Skipped/inapplicable cases: 0 (see JSON for reasons).

## By dataset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| maestro | 600 | 0.0000 | 276 / 282 | 0.0167 | 87 | 0.2530 |

## By kind

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| accidental | 60 | 0.0000 | 32 / 32 | n/a | 12 | 0.2384 |
| clean | 60 | n/a | 28 / 28 | 0.0167 | 8 | 0.2434 |
| coordinated | 60 | 0.0000 | 21 / 21 | n/a | 10 | 0.2285 |
| early | 60 | 0.0000 | 25 / 28 | n/a | 8 | 0.2407 |
| groove | 60 | 0.0000 | 31 / 33 | n/a | 9 | 0.2882 |
| late | 60 | 0.0000 | 28 / 28 | n/a | 8 | 0.2469 |
| octave | 60 | 0.0000 | 29 / 29 | n/a | 8 | 0.2340 |
| short | 60 | 0.0000 | 27 / 28 | n/a | 8 | 0.2632 |
| sustain | 60 | 0.0000 | 27 / 27 | n/a | 8 | 0.3060 |
| timing_duration | 60 | 0.0000 | 28 / 28 | n/a | 8 | 0.2404 |

## By preset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| balanced | 200 | 0.0000 | 96 / 98 | 0.0179 | 31 | 0.1943 |
| creative | 200 | 0.0000 | 138 / 141 | 0.0250 | 32 | 0.5218 |
| minimal | 200 | 0.0000 | 42 / 43 | 0.0071 | 24 | 0.0428 |

## By preservation

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| (0,) | 120 | 0.0000 | 276 / 282 | 0.0833 | 87 | 0.4298 |
| (100,) | 120 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0040 |
| (25,) | 120 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.4275 |
| (50,) | 120 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.2943 |
| (75,) | 120 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.1091 |

## By workflow

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| single | 600 | 0.0000 | 276 / 282 | 0.0167 | 87 | 0.2530 |

## Worst examples (distance + 10 × unnecessary field edits)

- 2015/MIDI-Unprocessed_R2_D2-12-13-15_mid--AUDIO-from_mp3_12_R2_2015_wav--1.midi@256:264 / octave / creative / (0,): distance 12.000 → 22.000; 8 unnecessary field edits.
- 2014/MIDI-UNPROCESSED_06-08_R1_2014_MID--AUDIO_07_R1_2014_wav--3.midi@384:392 / groove / creative / (0,): distance 0.125 → 31.125; 7 unnecessary field edits.
- 2015/MIDI-Unprocessed_R2_D2-12-13-15_mid--AUDIO-from_mp3_12_R2_2015_wav--1.midi@256:264 / timing_duration / creative / (0,): distance 0.625 → 11.625; 8 unnecessary field edits.
- 2015/MIDI-Unprocessed_R2_D2-12-13-15_mid--AUDIO-from_mp3_12_R2_2015_wav--1.midi@256:264 / sustain / creative / (0,): distance 0.500 → 13.500; 7 unnecessary field edits.
- 2015/MIDI-Unprocessed_R2_D2-12-13-15_mid--AUDIO-from_mp3_12_R2_2015_wav--1.midi@256:264 / accidental / creative / (0,): distance 1.000 → 10.000; 7 unnecessary field edits.
- 2015/MIDI-Unprocessed_R2_D2-12-13-15_mid--AUDIO-from_mp3_12_R2_2015_wav--1.midi@256:264 / early / creative / (0,): distance 0.125 → 9.125; 7 unnecessary field edits.
- 2015/MIDI-Unprocessed_R2_D2-12-13-15_mid--AUDIO-from_mp3_12_R2_2015_wav--1.midi@256:264 / groove / creative / (0,): distance 0.125 → 9.125; 7 unnecessary field edits.
- 2015/MIDI-Unprocessed_R2_D2-12-13-15_mid--AUDIO-from_mp3_12_R2_2015_wav--1.midi@256:264 / late / creative / (0,): distance 0.125 → 9.125; 7 unnecessary field edits.
- 2015/MIDI-Unprocessed_R2_D2-12-13-15_mid--AUDIO-from_mp3_12_R2_2015_wav--1.midi@256:264 / short / creative / (0,): distance 0.058 → 9.058; 7 unnecessary field edits.
- 2015/MIDI-Unprocessed_R2_D2-12-13-15_mid--AUDIO-from_mp3_12_R2_2015_wav--1.midi@256:264 / clean / creative / (0,): distance 0.000 → 9.000; 7 unnecessary field edits.

## Failure attribution

Hypotheses are not proven causes. Coverage gaps are observed; their upstream cause
may be analysis, harmony inference, filtering or permissions. Search and scoring
cannot always be distinguished without a production trace API.

```json
{
  "scoring": 156,
  "candidate generation": 417,
  "harmony inference": 417,
  "analysis": 425,
  "preservation penalties": 444,
  "timing logic": 229,
  "duration logic": 192,
  "search": 28
}
```

See results.json for exact ledgers, source event bindings, component metrics,
retained-alternative diagnostics, failures, and runtime vs note count.

## Candidate recall and search outcomes by edit type

```json
{
  "duration": {
    "corrupted_fields": 300,
    "eligible_fields": 240,
    "candidate_recall": 0.013333333333333334,
    "eligible_candidate_recall": 0.016666666666666666,
    "failure_counts": {
      "correct_candidate_never_generated": 236,
      "blocked_by_permissions_or_lock": 60,
      "scoring_preferred_another_result": 1,
      "required_combination_not_discovered": 3
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "correct_candidate_never_generated": 78.66666666666667,
      "required_combination_not_discovered": 1.0,
      "scoring_preferred_another_result": 0.3333333333333333
    },
    "category_percent_of_eligible_failures": {
      "correct_candidate_never_generated": 98.33333333333333,
      "required_combination_not_discovered": 1.25,
      "scoring_preferred_another_result": 0.4166666666666667
    },
    "analysis_failure_percent": null
  },
  "pitch": {
    "corrupted_fields": 240,
    "eligible_fields": 192,
    "candidate_recall": 0.21666666666666667,
    "eligible_candidate_recall": 0.2708333333333333,
    "failure_counts": {
      "correct_candidate_never_generated": 140,
      "blocked_by_permissions_or_lock": 48,
      "scoring_preferred_another_result": 14,
      "required_combination_not_discovered": 21,
      "recovered": 4,
      "correct_candidate_generated_but_pruned": 1,
      "constraint_or_budget_rejection": 12
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "constraint_or_budget_rejection": 5.0,
      "correct_candidate_generated_but_pruned": 0.4166666666666667,
      "correct_candidate_never_generated": 58.333333333333336,
      "recovered": 1.6666666666666667,
      "required_combination_not_discovered": 8.75,
      "scoring_preferred_another_result": 5.833333333333333
    },
    "category_percent_of_eligible_failures": {
      "constraint_or_budget_rejection": 6.382978723404255,
      "correct_candidate_generated_but_pruned": 0.5319148936170213,
      "correct_candidate_never_generated": 74.46808510638297,
      "required_combination_not_discovered": 11.170212765957446,
      "scoring_preferred_another_result": 7.446808510638298
    },
    "analysis_failure_percent": null
  },
  "timing": {
    "corrupted_fields": 360,
    "eligible_fields": 288,
    "candidate_recall": 0.030555555555555555,
    "eligible_candidate_recall": 0.03819444444444445,
    "failure_counts": {
      "correct_candidate_never_generated": 277,
      "blocked_by_permissions_or_lock": 72,
      "required_combination_not_discovered": 8,
      "correct_candidate_generated_but_pruned": 3
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "correct_candidate_generated_but_pruned": 0.8333333333333334,
      "correct_candidate_never_generated": 76.94444444444444,
      "required_combination_not_discovered": 2.2222222222222223
    },
    "category_percent_of_eligible_failures": {
      "correct_candidate_generated_but_pruned": 1.0416666666666667,
      "correct_candidate_never_generated": 96.18055555555556,
      "required_combination_not_discovered": 2.7777777777777777
    },
    "analysis_failure_percent": null
  }
}
```

Full per-setting breakdowns are in summary.json; target ranks,
best component-scored states and rejection reasons are in results.json.
