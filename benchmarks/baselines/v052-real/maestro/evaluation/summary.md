# GLUE benchmark baseline

GLUE: 0.5.1
Algorithm SHA-256: `04e1428013ad46e2f3c0b2838429d5a841763db64a6ebf5221d7d16bc2c5df96`

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
      "candidate_recall": 0.19583333333333333,
      "eligible_candidate_recall": 0.24479166666666666,
      "failure_counts": {
        "correct_candidate_never_generated": 145,
        "blocked_by_permissions_or_lock": 48,
        "recovered": 9,
        "scoring_preferred_another_result": 18,
        "required_combination_not_discovered": 20
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "correct_candidate_never_generated": 60.416666666666664,
        "recovered": 3.75,
        "required_combination_not_discovered": 8.333333333333334,
        "scoring_preferred_another_result": 7.5
      },
      "category_percent_of_eligible_failures": {
        "correct_candidate_never_generated": 79.23497267759562,
        "required_combination_not_discovered": 10.92896174863388,
        "scoring_preferred_another_result": 9.836065573770492
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
  "partial_field_recovery": 0.01,
  "corrupted_note_improvement_rate": 0.015,
  "clean_pitch_edits": 27,
  "clean_timing_edits": 0,
  "clean_duration_edits": 0,
  "clean_octave_displacements": 20,
  "clean_octave_displacement_rate": 0.011695906432748537,
  "clean_motif_disturbance_runs": 0,
  "exact_recovery_rate": 0.0033333333333333335,
  "unnecessary_edit_count": 272,
  "unnecessary_field_edits": 272,
  "clean_runs": 60,
  "clean_notes": 1710,
  "clean_false_positive_rate": 0.015789473684210527,
  "made_worse_runs": 119,
  "mean_runtime_seconds": 0.11777324316690889,
  "total_runtime_seconds": 70.66394590014534,
  "mean_distance_before": 1.9927372685185185,
  "mean_distance_after": 6.201996527777778
}
```

Skipped/inapplicable cases: 0 (see JSON for reasons).

## By dataset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| maestro | 600 | 0.0033 | 272 / 272 | 0.0158 | 119 | 0.1178 |

## By kind

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| accidental | 60 | 0.0333 | 25 / 25 | n/a | 12 | 0.1135 |
| clean | 60 | n/a | 27 / 27 | 0.0158 | 12 | 0.1085 |
| coordinated | 60 | 0.0000 | 28 / 28 | n/a | 11 | 0.2091 |
| early | 60 | 0.0000 | 27 / 27 | n/a | 12 | 0.1176 |
| groove | 60 | 0.0000 | 27 / 27 | n/a | 12 | 0.1077 |
| late | 60 | 0.0000 | 27 / 27 | n/a | 12 | 0.1072 |
| octave | 60 | 0.0000 | 26 / 26 | n/a | 12 | 0.0906 |
| short | 60 | 0.0000 | 27 / 27 | n/a | 12 | 0.1030 |
| sustain | 60 | 0.0000 | 29 / 29 | n/a | 12 | 0.1088 |
| timing_duration | 60 | 0.0000 | 29 / 29 | n/a | 12 | 0.1116 |

## By preset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| balanced | 200 | 0.0050 | 92 / 92 | 0.0158 | 40 | 0.0884 |
| creative | 200 | 0.0050 | 114 / 114 | 0.0193 | 40 | 0.2383 |
| minimal | 200 | 0.0000 | 66 / 66 | 0.0123 | 39 | 0.0267 |

## By preservation

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| (0,) | 120 | 0.0167 | 272 / 272 | 0.0789 | 119 | 0.1755 |
| (100,) | 120 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0031 |
| (25,) | 120 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.2035 |
| (50,) | 120 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.1396 |
| (75,) | 120 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0672 |

## By workflow

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| single | 600 | 0.0033 | 272 / 272 | 0.0158 | 119 | 0.1178 |

## Worst examples (distance + 10 × unnecessary field edits)

- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / coordinated / creative / (0,): distance 3.250 → 51.250; 6 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / accidental / creative / (0,): distance 1.000 → 46.000; 6 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / timing_duration / creative / (0,): distance 0.625 → 45.625; 6 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / sustain / creative / (0,): distance 0.500 → 45.500; 6 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / early / creative / (0,): distance 0.125 → 45.125; 6 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / groove / creative / (0,): distance 0.125 → 45.125; 6 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / late / creative / (0,): distance 0.125 → 45.125; 6 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / short / creative / (0,): distance 0.029 → 45.029; 6 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / clean / creative / (0,): distance 0.000 → 45.000; 6 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / octave / creative / (0,): distance 12.000 → 45.000; 5 unnecessary field edits.

## Failure attribution

Hypotheses are not proven causes. Coverage gaps are observed; their upstream cause
may be analysis, harmony inference, filtering or permissions. Search and scoring
cannot always be distinguished without a production trace API.

```json
{
  "scoring": 219,
  "analysis": 432,
  "candidate generation": 420,
  "harmony inference": 420,
  "preservation penalties": 444,
  "timing logic": 240,
  "duration logic": 192,
  "search": 2
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
    "candidate_recall": 0.19583333333333333,
    "eligible_candidate_recall": 0.24479166666666666,
    "failure_counts": {
      "correct_candidate_never_generated": 145,
      "blocked_by_permissions_or_lock": 48,
      "recovered": 9,
      "scoring_preferred_another_result": 18,
      "required_combination_not_discovered": 20
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "correct_candidate_never_generated": 60.416666666666664,
      "recovered": 3.75,
      "required_combination_not_discovered": 8.333333333333334,
      "scoring_preferred_another_result": 7.5
    },
    "category_percent_of_eligible_failures": {
      "correct_candidate_never_generated": 79.23497267759562,
      "required_combination_not_discovered": 10.92896174863388,
      "scoring_preferred_another_result": 9.836065573770492
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
