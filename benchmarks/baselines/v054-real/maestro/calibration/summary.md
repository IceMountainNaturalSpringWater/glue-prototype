# GLUE benchmark baseline

GLUE: 0.5.4
Algorithm SHA-256: `a00c900cfe8da896d851a91a8d16a625da9c8204269e90b962cf66b993ed06c8`

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
      "candidate_recall": 0.30833333333333335,
      "eligible_candidate_recall": 0.3854166666666667,
      "failure_counts": {
        "correct_candidate_never_generated": 118,
        "blocked_by_permissions_or_lock": 48,
        "recovered": 14,
        "scoring_preferred_another_result": 31,
        "required_combination_not_discovered": 20,
        "constraint_or_budget_rejection": 9
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "constraint_or_budget_rejection": 3.75,
        "correct_candidate_never_generated": 49.166666666666664,
        "recovered": 5.833333333333333,
        "required_combination_not_discovered": 8.333333333333334,
        "scoring_preferred_another_result": 12.916666666666666
      },
      "category_percent_of_eligible_failures": {
        "constraint_or_budget_rejection": 5.056179775280899,
        "correct_candidate_never_generated": 66.29213483146067,
        "required_combination_not_discovered": 11.235955056179776,
        "scoring_preferred_another_result": 17.415730337078653
      },
      "analysis_failure_percent": null
    },
    "timing": {
      "corrupted_fields": 360,
      "eligible_fields": 288,
      "candidate_recall": 0.05,
      "eligible_candidate_recall": 0.0625,
      "failure_counts": {
        "correct_candidate_never_generated": 270,
        "blocked_by_permissions_or_lock": 72,
        "required_combination_not_discovered": 10,
        "scoring_preferred_another_result": 7,
        "recovered": 1
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "correct_candidate_never_generated": 75.0,
        "recovered": 0.2777777777777778,
        "required_combination_not_discovered": 2.7777777777777777,
        "scoring_preferred_another_result": 1.9444444444444444
      },
      "category_percent_of_eligible_failures": {
        "correct_candidate_never_generated": 94.07665505226481,
        "required_combination_not_discovered": 3.484320557491289,
        "scoring_preferred_another_result": 2.4390243902439024
      },
      "analysis_failure_percent": null
    }
  },
  "runs": 600,
  "errors": 0,
  "corrupted_notes": 600,
  "partial_field_recovery": 0.016666666666666666,
  "corrupted_note_improvement_rate": 0.041666666666666664,
  "clean_pitch_edits": 26,
  "clean_timing_edits": 2,
  "clean_duration_edits": 0,
  "clean_octave_displacements": 0,
  "clean_octave_displacement_rate": 0.0,
  "clean_motif_disturbance_runs": 0,
  "exact_recovery_rate": 0.02,
  "unnecessary_edit_count": 263,
  "unnecessary_field_edits": 270,
  "clean_runs": 60,
  "clean_notes": 1680,
  "clean_false_positive_rate": 0.016666666666666666,
  "made_worse_runs": 85,
  "mean_runtime_seconds": 0.32892256566653183,
  "total_runtime_seconds": 197.3535393999191,
  "mean_distance_before": 2.000101273148148,
  "mean_distance_after": 2.3925163966049383
}
```

Skipped/inapplicable cases: 0 (see JSON for reasons).

## By dataset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| maestro | 600 | 0.0200 | 263 / 270 | 0.0167 | 85 | 0.3289 |

## By kind

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| accidental | 60 | 0.0000 | 32 / 32 | n/a | 11 | 0.3235 |
| clean | 60 | n/a | 28 / 28 | 0.0167 | 8 | 0.3317 |
| coordinated | 60 | 0.0000 | 20 / 20 | n/a | 10 | 0.3342 |
| early | 60 | 0.0000 | 24 / 27 | n/a | 8 | 0.3313 |
| groove | 60 | 0.0000 | 28 / 29 | n/a | 9 | 0.3380 |
| late | 60 | 0.0000 | 25 / 25 | n/a | 8 | 0.3253 |
| octave | 60 | 0.2000 | 26 / 26 | n/a | 5 | 0.3251 |
| short | 60 | 0.0000 | 27 / 28 | n/a | 8 | 0.3402 |
| sustain | 60 | 0.0000 | 25 / 27 | n/a | 10 | 0.3414 |
| timing_duration | 60 | 0.0000 | 28 / 28 | n/a | 8 | 0.2984 |

## By preset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| balanced | 200 | 0.0200 | 90 / 93 | 0.0179 | 31 | 0.2608 |
| creative | 200 | 0.0200 | 134 / 137 | 0.0250 | 32 | 0.6819 |
| minimal | 200 | 0.0200 | 39 / 40 | 0.0071 | 22 | 0.0441 |

## By preservation

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| (0,) | 120 | 0.0500 | 262 / 268 | 0.0833 | 83 | 0.5803 |
| (100,) | 120 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0039 |
| (25,) | 120 | 0.0500 | 1 / 2 | 0.0000 | 2 | 0.5306 |
| (50,) | 120 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.3771 |
| (75,) | 120 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.1528 |

## By workflow

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| single | 600 | 0.0200 | 263 / 270 | 0.0167 | 85 | 0.3289 |

## Worst examples (distance + 10 × unnecessary field edits)

- 2015/MIDI-Unprocessed_R2_D2-12-13-15_mid--AUDIO-from_mp3_12_R2_2015_wav--1.midi@256:264 / timing_duration / creative / (0,): distance 0.625 → 10.625; 8 unnecessary field edits.
- 2015/MIDI-Unprocessed_R2_D2-12-13-15_mid--AUDIO-from_mp3_12_R2_2015_wav--1.midi@256:264 / sustain / creative / (0,): distance 0.500 → 13.006; 7 unnecessary field edits.
- 2015/MIDI-Unprocessed_R2_D2-12-13-15_mid--AUDIO-from_mp3_12_R2_2015_wav--1.midi@256:264 / accidental / creative / (0,): distance 1.000 → 9.000; 7 unnecessary field edits.
- 2015/MIDI-Unprocessed_R2_D2-12-13-15_mid--AUDIO-from_mp3_12_R2_2015_wav--1.midi@256:264 / short / creative / (0,): distance 0.058 → 8.058; 7 unnecessary field edits.
- 2015/MIDI-Unprocessed_R2_D2-12-13-15_mid--AUDIO-from_mp3_12_R2_2015_wav--1.midi@256:264 / early / creative / (0,): distance 0.125 → 8.027; 7 unnecessary field edits.
- 2015/MIDI-Unprocessed_R2_D2-12-13-15_mid--AUDIO-from_mp3_12_R2_2015_wav--1.midi@256:264 / groove / creative / (0,): distance 0.125 → 8.004; 7 unnecessary field edits.
- 2015/MIDI-Unprocessed_R2_D2-12-13-15_mid--AUDIO-from_mp3_12_R2_2015_wav--1.midi@256:264 / clean / creative / (0,): distance 0.000 → 8.000; 7 unnecessary field edits.
- 2015/MIDI-Unprocessed_R2_D2-12-13-15_mid--AUDIO-from_mp3_12_R2_2015_wav--1.midi@256:264 / octave / creative / (0,): distance 12.000 → 8.000; 7 unnecessary field edits.
- 2015/MIDI-Unprocessed_R2_D2-12-13-15_mid--AUDIO-from_mp3_12_R2_2015_wav--1.midi@256:264 / late / creative / (0,): distance 0.125 → 7.002; 7 unnecessary field edits.
- 2014/MIDI-UNPROCESSED_06-08_R1_2014_MID--AUDIO_07_R1_2014_wav--3.midi@384:392 / groove / creative / (0,): distance 0.125 → 13.125; 5 unnecessary field edits.

## Failure attribution

Hypotheses are not proven causes. Coverage gaps are observed; their upstream cause
may be analysis, harmony inference, filtering or permissions. Search and scoring
cannot always be distinguished without a production trace API.

```json
{
  "scoring": 156,
  "candidate generation": 390,
  "harmony inference": 390,
  "analysis": 398,
  "preservation penalties": 438,
  "timing logic": 226,
  "duration logic": 192,
  "search": 36
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
    "candidate_recall": 0.30833333333333335,
    "eligible_candidate_recall": 0.3854166666666667,
    "failure_counts": {
      "correct_candidate_never_generated": 118,
      "blocked_by_permissions_or_lock": 48,
      "recovered": 14,
      "scoring_preferred_another_result": 31,
      "required_combination_not_discovered": 20,
      "constraint_or_budget_rejection": 9
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "constraint_or_budget_rejection": 3.75,
      "correct_candidate_never_generated": 49.166666666666664,
      "recovered": 5.833333333333333,
      "required_combination_not_discovered": 8.333333333333334,
      "scoring_preferred_another_result": 12.916666666666666
    },
    "category_percent_of_eligible_failures": {
      "constraint_or_budget_rejection": 5.056179775280899,
      "correct_candidate_never_generated": 66.29213483146067,
      "required_combination_not_discovered": 11.235955056179776,
      "scoring_preferred_another_result": 17.415730337078653
    },
    "analysis_failure_percent": null
  },
  "timing": {
    "corrupted_fields": 360,
    "eligible_fields": 288,
    "candidate_recall": 0.05,
    "eligible_candidate_recall": 0.0625,
    "failure_counts": {
      "correct_candidate_never_generated": 270,
      "blocked_by_permissions_or_lock": 72,
      "required_combination_not_discovered": 10,
      "scoring_preferred_another_result": 7,
      "recovered": 1
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "correct_candidate_never_generated": 75.0,
      "recovered": 0.2777777777777778,
      "required_combination_not_discovered": 2.7777777777777777,
      "scoring_preferred_another_result": 1.9444444444444444
    },
    "category_percent_of_eligible_failures": {
      "correct_candidate_never_generated": 94.07665505226481,
      "required_combination_not_discovered": 3.484320557491289,
      "scoring_preferred_another_result": 2.4390243902439024
    },
    "analysis_failure_percent": null
  }
}
```

Full per-setting breakdowns are in summary.json; target ranks,
best component-scored states and rejection reasons are in results.json.
