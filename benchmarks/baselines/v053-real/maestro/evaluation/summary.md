# GLUE benchmark baseline

GLUE: 0.5.3
Algorithm SHA-256: `66e7374af98dc90556c96d64875d42803b7cea58f6b0a21149468cc7a9b98c53`

Dataset: maestro; split: evaluation.
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
      "candidate_recall": 0.0,
      "eligible_candidate_recall": 0.0,
      "failure_counts": {
        "correct_candidate_never_generated": 240,
        "blocked_by_permissions_or_lock": 60
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
      "corrupted_fields": 240,
      "eligible_fields": 192,
      "candidate_recall": 0.24583333333333332,
      "eligible_candidate_recall": 0.3072916666666667,
      "failure_counts": {
        "scoring_preferred_another_result": 21,
        "blocked_by_permissions_or_lock": 48,
        "correct_candidate_never_generated": 133,
        "recovered": 6,
        "required_combination_not_discovered": 14,
        "constraint_or_budget_rejection": 18
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "constraint_or_budget_rejection": 7.5,
        "correct_candidate_never_generated": 55.416666666666664,
        "recovered": 2.5,
        "required_combination_not_discovered": 5.833333333333333,
        "scoring_preferred_another_result": 8.75
      },
      "category_percent_of_eligible_failures": {
        "constraint_or_budget_rejection": 9.67741935483871,
        "correct_candidate_never_generated": 71.50537634408602,
        "required_combination_not_discovered": 7.526881720430108,
        "scoring_preferred_another_result": 11.290322580645162
      },
      "analysis_failure_percent": null
    },
    "timing": {
      "corrupted_fields": 360,
      "eligible_fields": 288,
      "candidate_recall": 0.0,
      "eligible_candidate_recall": 0.0,
      "failure_counts": {
        "correct_candidate_never_generated": 288,
        "blocked_by_permissions_or_lock": 72
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "correct_candidate_never_generated": 80.0
      },
      "category_percent_of_eligible_failures": {
        "correct_candidate_never_generated": 100.0
      },
      "analysis_failure_percent": null
    }
  },
  "runs": 600,
  "errors": 0,
  "corrupted_notes": 600,
  "partial_field_recovery": 0.006666666666666667,
  "corrupted_note_improvement_rate": 0.01,
  "clean_pitch_edits": 29,
  "clean_timing_edits": 0,
  "clean_duration_edits": 2,
  "clean_octave_displacements": 0,
  "clean_octave_displacement_rate": 0.0,
  "clean_motif_disturbance_runs": 0,
  "exact_recovery_rate": 0.0,
  "unnecessary_edit_count": 294,
  "unnecessary_field_edits": 305,
  "clean_runs": 60,
  "clean_notes": 1710,
  "clean_false_positive_rate": 0.017543859649122806,
  "made_worse_runs": 116,
  "mean_runtime_seconds": 0.1974151578322441,
  "total_runtime_seconds": 118.44909469934646,
  "mean_distance_before": 1.9927372685185185,
  "mean_distance_after": 2.9936149691358023
}
```

Skipped/inapplicable cases: 0 (see JSON for reasons).

## By dataset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| maestro | 600 | 0.0000 | 294 / 305 | 0.0175 | 116 | 0.1974 |

## By kind

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| accidental | 60 | 0.0000 | 28 / 28 | n/a | 9 | 0.2217 |
| clean | 60 | n/a | 30 / 31 | 0.0175 | 12 | 0.1883 |
| coordinated | 60 | 0.0000 | 25 / 25 | n/a | 11 | 0.2224 |
| early | 60 | 0.0000 | 27 / 30 | n/a | 12 | 0.2110 |
| groove | 60 | 0.0000 | 33 / 33 | n/a | 12 | 0.1928 |
| late | 60 | 0.0000 | 31 / 31 | n/a | 12 | 0.1883 |
| octave | 60 | 0.0000 | 32 / 33 | n/a | 12 | 0.1979 |
| short | 60 | 0.0000 | 30 / 31 | n/a | 12 | 0.1805 |
| sustain | 60 | 0.0000 | 31 / 32 | n/a | 12 | 0.1809 |
| timing_duration | 60 | 0.0000 | 27 / 31 | n/a | 12 | 0.1902 |

## By preset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| balanced | 200 | 0.0000 | 98 / 100 | 0.0175 | 39 | 0.1563 |
| creative | 200 | 0.0000 | 137 / 144 | 0.0246 | 39 | 0.3971 |
| minimal | 200 | 0.0000 | 59 / 61 | 0.0105 | 38 | 0.0388 |

## By preservation

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| (0,) | 120 | 0.0000 | 294 / 305 | 0.0877 | 116 | 0.3137 |
| (100,) | 120 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0032 |
| (25,) | 120 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.3194 |
| (50,) | 120 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.2366 |
| (75,) | 120 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.1142 |

## By workflow

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| single | 600 | 0.0000 | 294 / 305 | 0.0175 | 116 | 0.1974 |

## Worst examples (distance + 10 × unnecessary field edits)

- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / octave / creative / (0,): distance 12.000 → 21.786; 8 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / groove / creative / (0,): distance 0.125 → 11.539; 8 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / late / creative / (0,): distance 0.125 → 11.411; 8 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / timing_duration / creative / (0,): distance 0.625 → 10.411; 8 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / short / creative / (0,): distance 0.029 → 9.815; 8 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / clean / creative / (0,): distance 0.000 → 9.786; 8 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / coordinated / creative / (0,): distance 3.250 → 25.250; 6 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / early / creative / (0,): distance 0.125 → 11.911; 7 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / accidental / creative / (0,): distance 1.000 → 11.286; 7 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / sustain / creative / (0,): distance 0.500 → 9.841; 7 unnecessary field edits.

## Failure attribution

Hypotheses are not proven causes. Coverage gaps are observed; their upstream cause
may be analysis, harmony inference, filtering or permissions. Search and scoring
cannot always be distinguished without a production trace API.

```json
{
  "scoring": 195,
  "analysis": 426,
  "search": 22,
  "preservation penalties": 444,
  "candidate generation": 414,
  "harmony inference": 414,
  "timing logic": 240,
  "duration logic": 192
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
    "candidate_recall": 0.0,
    "eligible_candidate_recall": 0.0,
    "failure_counts": {
      "correct_candidate_never_generated": 240,
      "blocked_by_permissions_or_lock": 60
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
    "corrupted_fields": 240,
    "eligible_fields": 192,
    "candidate_recall": 0.24583333333333332,
    "eligible_candidate_recall": 0.3072916666666667,
    "failure_counts": {
      "scoring_preferred_another_result": 21,
      "blocked_by_permissions_or_lock": 48,
      "correct_candidate_never_generated": 133,
      "recovered": 6,
      "required_combination_not_discovered": 14,
      "constraint_or_budget_rejection": 18
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "constraint_or_budget_rejection": 7.5,
      "correct_candidate_never_generated": 55.416666666666664,
      "recovered": 2.5,
      "required_combination_not_discovered": 5.833333333333333,
      "scoring_preferred_another_result": 8.75
    },
    "category_percent_of_eligible_failures": {
      "constraint_or_budget_rejection": 9.67741935483871,
      "correct_candidate_never_generated": 71.50537634408602,
      "required_combination_not_discovered": 7.526881720430108,
      "scoring_preferred_another_result": 11.290322580645162
    },
    "analysis_failure_percent": null
  },
  "timing": {
    "corrupted_fields": 360,
    "eligible_fields": 288,
    "candidate_recall": 0.0,
    "eligible_candidate_recall": 0.0,
    "failure_counts": {
      "correct_candidate_never_generated": 288,
      "blocked_by_permissions_or_lock": 72
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "correct_candidate_never_generated": 80.0
    },
    "category_percent_of_eligible_failures": {
      "correct_candidate_never_generated": 100.0
    },
    "analysis_failure_percent": null
  }
}
```

Full per-setting breakdowns are in summary.json; target ranks,
best component-scored states and rejection reasons are in results.json.
