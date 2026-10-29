# GLUE benchmark baseline

GLUE: 0.5.1
Algorithm SHA-256: `33b7c822563062655b4afbe293640bfb4b082904ea5843bcf482740bccecd78f`

Dataset: synthetic-framework-validation; split: calibration.
Self-authored CC0 synthetic references; NOT POP909/MAESTRO results, not human-rated musical ground truth. Evaluation piece held out.

This measures recovery of designated references, not objective musical quality.
Top-ranked candidate only; no oracle selection or tuning. Clean controls are mandatory.
Timing is machine-dependent; deterministic digests exclude runtime/environment.

## Overall

```json
{
  "edit_type_diagnostics": {
    "duration": {
      "corrupted_fields": 336,
      "eligible_fields": 258,
      "candidate_recall": 0.0,
      "eligible_candidate_recall": 0.0,
      "failure_counts": {
        "correct_candidate_never_generated": 258,
        "blocked_by_permissions_or_lock": 78
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 23.214285714285715,
        "correct_candidate_never_generated": 76.78571428571429
      },
      "category_percent_of_eligible_failures": {
        "correct_candidate_never_generated": 100.0
      },
      "analysis_failure_percent": null
    },
    "pitch": {
      "corrupted_fields": 438,
      "eligible_fields": 336,
      "candidate_recall": 0.2785388127853881,
      "eligible_candidate_recall": 0.3630952380952381,
      "failure_counts": {
        "correct_candidate_never_generated": 214,
        "blocked_by_permissions_or_lock": 102,
        "scoring_preferred_another_result": 89,
        "recovered": 18,
        "required_combination_not_discovered": 15
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 23.28767123287671,
        "correct_candidate_never_generated": 48.858447488584474,
        "recovered": 4.109589041095891,
        "required_combination_not_discovered": 3.4246575342465753,
        "scoring_preferred_another_result": 20.319634703196346
      },
      "category_percent_of_eligible_failures": {
        "correct_candidate_never_generated": 67.29559748427673,
        "required_combination_not_discovered": 4.716981132075472,
        "scoring_preferred_another_result": 27.9874213836478
      },
      "analysis_failure_percent": null
    },
    "timing": {
      "corrupted_fields": 414,
      "eligible_fields": 315,
      "candidate_recall": 0.024154589371980676,
      "eligible_candidate_recall": 0.031746031746031744,
      "failure_counts": {
        "correct_candidate_never_generated": 305,
        "blocked_by_permissions_or_lock": 99,
        "scoring_preferred_another_result": 10
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 23.91304347826087,
        "correct_candidate_never_generated": 73.67149758454106,
        "scoring_preferred_another_result": 2.4154589371980677
      },
      "category_percent_of_eligible_failures": {
        "correct_candidate_never_generated": 96.82539682539682,
        "scoring_preferred_another_result": 3.1746031746031744
      },
      "analysis_failure_percent": null
    }
  },
  "runs": 831,
  "errors": 0,
  "corrupted_notes": 831,
  "partial_field_recovery": 0.015151515151515152,
  "corrupted_note_improvement_rate": 0.026474127557160047,
  "clean_pitch_edits": 6,
  "clean_timing_edits": 0,
  "clean_duration_edits": 0,
  "clean_octave_displacements": 6,
  "clean_octave_displacement_rate": 0.01282051282051282,
  "clean_motif_disturbance_runs": 3,
  "exact_recovery_rate": 0.013237063778580024,
  "unnecessary_edit_count": 93,
  "unnecessary_field_edits": 93,
  "clean_runs": 51,
  "clean_notes": 468,
  "clean_false_positive_rate": 0.01282051282051282,
  "made_worse_runs": 69,
  "mean_runtime_seconds": 0.01324015908546444,
  "total_runtime_seconds": 11.00257220002095,
  "mean_distance_before": 1.7153846153846153,
  "mean_distance_after": 2.716666666666667
}
```

Skipped/inapplicable cases: 11 (see JSON for reasons).

## By dataset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| synthetic-framework-validation | 831 | 0.0132 | 93 / 93 | 0.0128 | 69 | 0.0132 |

## By kind

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| accidental | 51 | 0.0392 | 6 / 6 | n/a | 6 | 0.0112 |
| attack_collision | 36 | 0.0000 | 8 / 8 | n/a | 8 | 0.0060 |
| bass_lead_collision | 15 | 0.0000 | 6 / 6 | n/a | 3 | 0.0163 |
| bass_pitch | 51 | 0.0980 | 3 / 3 | n/a | 3 | 0.0151 |
| call_response | 21 | 0.0000 | 2 / 2 | n/a | 10 | 0.0126 |
| clean | 51 | n/a | 6 / 6 | 0.0128 | 3 | 0.0064 |
| coordinated | 51 | 0.0000 | 8 / 8 | n/a | 3 | 0.0124 |
| early | 51 | 0.0000 | 6 / 6 | n/a | 3 | 0.0080 |
| groove | 51 | 0.0000 | 0 / 0 | n/a | 0 | 0.0036 |
| harmony_overlap | 15 | 0.0000 | 3 / 3 | n/a | 3 | 0.0164 |
| late | 51 | 0.0000 | 0 / 0 | n/a | 0 | 0.0043 |
| motif | 15 | 0.2000 | 0 / 0 | n/a | 0 | 0.0052 |
| octave | 51 | 0.0000 | 6 / 6 | n/a | 3 | 0.0167 |
| pitch_duration | 51 | 0.0000 | 10 / 10 | n/a | 6 | 0.0689 |
| pitch_timing | 51 | 0.0000 | 0 / 0 | n/a | 0 | 0.0060 |
| short | 51 | 0.0000 | 6 / 6 | n/a | 3 | 0.0080 |
| sustain | 51 | 0.0000 | 6 / 6 | n/a | 3 | 0.0080 |
| timing_duration | 51 | 0.0000 | 3 / 3 | n/a | 3 | 0.0082 |
| wrong_chord_tone | 15 | 0.0000 | 6 / 6 | n/a | 3 | 0.0252 |
| wrong_diatonic | 51 | 0.0196 | 8 / 8 | n/a | 6 | 0.0109 |

## By preset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| balanced | 277 | 0.0144 | 33 / 33 | 0.0128 | 26 | 0.0127 |
| creative | 277 | 0.0144 | 35 / 35 | 0.0128 | 26 | 0.0190 |
| minimal | 277 | 0.0108 | 25 / 25 | 0.0128 | 17 | 0.0081 |

## By preservation

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| (0, 0) | 48 | 0.0000 | 2 / 2 | 0.0000 | 4 | 0.0055 |
| (0, 100) | 48 | 0.0000 | 2 / 2 | 0.0000 | 4 | 0.0045 |
| (0,) | 99 | 0.1111 | 83 / 83 | 0.1000 | 51 | 0.0288 |
| (100, 0) | 48 | 0.0000 | 2 / 2 | 0.0000 | 2 | 0.0047 |
| (100, 100) | 48 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0038 |
| (100,) | 99 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0026 |
| (25, 25) | 48 | 0.0000 | 2 / 2 | 0.0000 | 4 | 0.0055 |
| (25,) | 99 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0273 |
| (50, 50) | 48 | 0.0000 | 2 / 2 | 0.0000 | 4 | 0.0054 |
| (50,) | 99 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0221 |
| (75, 75) | 48 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0055 |
| (75,) | 99 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0134 |

## By workflow

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| pair | 336 | 0.0000 | 10 / 10 | 0.0000 | 18 | 0.0050 |
| single | 495 | 0.0222 | 83 / 83 | 0.0200 | 51 | 0.0188 |

## Worst examples (distance + 10 × unnecessary field edits)

- chords / pitch_duration / creative / (0,): distance 1.500 → 30.500; 4 unnecessary field edits.
- chords / coordinated / creative / (0,): distance 3.250 → 32.250; 3 unnecessary field edits.
- chords / coordinated / balanced / (0,): distance 3.250 → 28.250; 3 unnecessary field edits.
- chords / octave / balanced / (0,): distance 12.000 → 36.000; 2 unnecessary field edits.
- chords / octave / creative / (0,): distance 12.000 → 36.000; 2 unnecessary field edits.
- chords / octave / minimal / (0,): distance 12.000 → 36.000; 2 unnecessary field edits.
- chords / wrong_chord_tone / balanced / (0,): distance 5.000 → 29.000; 2 unnecessary field edits.
- chords / wrong_chord_tone / creative / (0,): distance 5.000 → 29.000; 2 unnecessary field edits.
- chords / wrong_chord_tone / minimal / (0,): distance 5.000 → 29.000; 2 unnecessary field edits.
- chords / coordinated / minimal / (0,): distance 3.250 → 27.250; 2 unnecessary field edits.

## Failure attribution

Hypotheses are not proven causes. Coverage gaps are observed; their upstream cause
may be analysis, harmony inference, filtering or permissions. Search and scoring
cannot always be distinguished without a production trace API.

```json
{
  "candidate generation": 489,
  "harmony inference": 489,
  "analysis": 492,
  "preservation penalties": 609,
  "search": 12,
  "timing logic": 266,
  "scoring": 102,
  "duration logic": 219
}
```

See results.json for exact ledgers, source event bindings, component metrics,
retained-alternative diagnostics, failures, and runtime vs note count.

## Candidate recall and search outcomes by edit type

```json
{
  "duration": {
    "corrupted_fields": 336,
    "eligible_fields": 258,
    "candidate_recall": 0.0,
    "eligible_candidate_recall": 0.0,
    "failure_counts": {
      "correct_candidate_never_generated": 258,
      "blocked_by_permissions_or_lock": 78
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 23.214285714285715,
      "correct_candidate_never_generated": 76.78571428571429
    },
    "category_percent_of_eligible_failures": {
      "correct_candidate_never_generated": 100.0
    },
    "analysis_failure_percent": null
  },
  "pitch": {
    "corrupted_fields": 438,
    "eligible_fields": 336,
    "candidate_recall": 0.2785388127853881,
    "eligible_candidate_recall": 0.3630952380952381,
    "failure_counts": {
      "correct_candidate_never_generated": 214,
      "blocked_by_permissions_or_lock": 102,
      "scoring_preferred_another_result": 89,
      "recovered": 18,
      "required_combination_not_discovered": 15
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 23.28767123287671,
      "correct_candidate_never_generated": 48.858447488584474,
      "recovered": 4.109589041095891,
      "required_combination_not_discovered": 3.4246575342465753,
      "scoring_preferred_another_result": 20.319634703196346
    },
    "category_percent_of_eligible_failures": {
      "correct_candidate_never_generated": 67.29559748427673,
      "required_combination_not_discovered": 4.716981132075472,
      "scoring_preferred_another_result": 27.9874213836478
    },
    "analysis_failure_percent": null
  },
  "timing": {
    "corrupted_fields": 414,
    "eligible_fields": 315,
    "candidate_recall": 0.024154589371980676,
    "eligible_candidate_recall": 0.031746031746031744,
    "failure_counts": {
      "correct_candidate_never_generated": 305,
      "blocked_by_permissions_or_lock": 99,
      "scoring_preferred_another_result": 10
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 23.91304347826087,
      "correct_candidate_never_generated": 73.67149758454106,
      "scoring_preferred_another_result": 2.4154589371980677
    },
    "category_percent_of_eligible_failures": {
      "correct_candidate_never_generated": 96.82539682539682,
      "scoring_preferred_another_result": 3.1746031746031744
    },
    "analysis_failure_percent": null
  }
}
```

Full per-setting breakdowns are in summary.json; target ranks,
best component-scored states and rejection reasons are in results.json.
