# GLUE benchmark baseline

GLUE: 0.5.4
Algorithm SHA-256: `a00c900cfe8da896d851a91a8d16a625da9c8204269e90b962cf66b993ed06c8`

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
      "candidate_recall": 0.23333333333333334,
      "eligible_candidate_recall": 0.2916666666666667,
      "failure_counts": {
        "scoring_preferred_another_result": 20,
        "blocked_by_permissions_or_lock": 48,
        "correct_candidate_never_generated": 136,
        "recovered": 6,
        "required_combination_not_discovered": 13,
        "constraint_or_budget_rejection": 17
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "constraint_or_budget_rejection": 7.083333333333333,
        "correct_candidate_never_generated": 56.666666666666664,
        "recovered": 2.5,
        "required_combination_not_discovered": 5.416666666666667,
        "scoring_preferred_another_result": 8.333333333333334
      },
      "category_percent_of_eligible_failures": {
        "constraint_or_budget_rejection": 9.13978494623656,
        "correct_candidate_never_generated": 73.11827956989248,
        "required_combination_not_discovered": 6.989247311827957,
        "scoring_preferred_another_result": 10.75268817204301
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
  "clean_pitch_edits": 27,
  "clean_timing_edits": 1,
  "clean_duration_edits": 1,
  "clean_octave_displacements": 0,
  "clean_octave_displacement_rate": 0.0,
  "clean_motif_disturbance_runs": 0,
  "exact_recovery_rate": 0.0,
  "unnecessary_edit_count": 285,
  "unnecessary_field_edits": 294,
  "clean_runs": 60,
  "clean_notes": 1710,
  "clean_false_positive_rate": 0.01695906432748538,
  "made_worse_runs": 123,
  "mean_runtime_seconds": 0.27086404533241876,
  "total_runtime_seconds": 162.51842719945125,
  "mean_distance_before": 1.9927372685185185,
  "mean_distance_after": 2.812369791666667
}
```

Skipped/inapplicable cases: 0 (see JSON for reasons).

## By dataset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| maestro | 600 | 0.0000 | 285 / 294 | 0.0170 | 123 | 0.2709 |

## By kind

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| accidental | 60 | 0.0000 | 27 / 27 | n/a | 9 | 0.3069 |
| clean | 60 | n/a | 29 / 29 | 0.0170 | 12 | 0.2546 |
| coordinated | 60 | 0.0000 | 24 / 24 | n/a | 11 | 0.2988 |
| early | 60 | 0.0000 | 26 / 32 | n/a | 14 | 0.2907 |
| groove | 60 | 0.0000 | 27 / 27 | n/a | 11 | 0.2509 |
| late | 60 | 0.0000 | 35 / 35 | n/a | 15 | 0.2510 |
| octave | 60 | 0.0000 | 34 / 34 | n/a | 15 | 0.2819 |
| short | 60 | 0.0000 | 29 / 29 | n/a | 12 | 0.2506 |
| sustain | 60 | 0.0000 | 28 / 28 | n/a | 12 | 0.2485 |
| timing_duration | 60 | 0.0000 | 26 / 29 | n/a | 12 | 0.2746 |

## By preset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| balanced | 200 | 0.0000 | 99 / 102 | 0.0175 | 42 | 0.2079 |
| creative | 200 | 0.0000 | 129 / 133 | 0.0228 | 42 | 0.5613 |
| minimal | 200 | 0.0000 | 57 / 59 | 0.0105 | 39 | 0.0434 |

## By preservation

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| (0,) | 120 | 0.0000 | 279 / 286 | 0.0848 | 115 | 0.4474 |
| (100,) | 120 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0036 |
| (25,) | 120 | 0.0000 | 6 / 8 | 0.0000 | 8 | 0.4302 |
| (50,) | 120 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.3251 |
| (75,) | 120 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.1480 |

## By workflow

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| single | 600 | 0.0000 | 285 / 294 | 0.0170 | 123 | 0.2709 |

## Worst examples (distance + 10 × unnecessary field edits)

- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / early / creative / (0,): distance 0.125 → 10.591; 8 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / octave / creative / (0,): distance 12.000 → 20.570; 7 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / timing_duration / creative / (0,): distance 0.625 → 9.195; 7 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / groove / creative / (0,): distance 0.125 → 8.695; 7 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / late / creative / (0,): distance 0.125 → 8.695; 7 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / short / creative / (0,): distance 0.029 → 8.599; 7 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / clean / creative / (0,): distance 0.000 → 8.570; 7 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / sustain / creative / (0,): distance 0.500 → 8.625; 6 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / accidental / creative / (0,): distance 1.000 → 8.570; 6 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / coordinated / creative / (0,): distance 3.250 → 15.047; 5 unnecessary field edits.

## Failure attribution

Hypotheses are not proven causes. Coverage gaps are observed; their upstream cause
may be analysis, harmony inference, filtering or permissions. Search and scoring
cannot always be distinguished without a production trace API.

```json
{
  "scoring": 206,
  "analysis": 427,
  "search": 23,
  "preservation penalties": 444,
  "candidate generation": 415,
  "harmony inference": 415,
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
    "candidate_recall": 0.23333333333333334,
    "eligible_candidate_recall": 0.2916666666666667,
    "failure_counts": {
      "scoring_preferred_another_result": 20,
      "blocked_by_permissions_or_lock": 48,
      "correct_candidate_never_generated": 136,
      "recovered": 6,
      "required_combination_not_discovered": 13,
      "constraint_or_budget_rejection": 17
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "constraint_or_budget_rejection": 7.083333333333333,
      "correct_candidate_never_generated": 56.666666666666664,
      "recovered": 2.5,
      "required_combination_not_discovered": 5.416666666666667,
      "scoring_preferred_another_result": 8.333333333333334
    },
    "category_percent_of_eligible_failures": {
      "constraint_or_budget_rejection": 9.13978494623656,
      "correct_candidate_never_generated": 73.11827956989248,
      "required_combination_not_discovered": 6.989247311827957,
      "scoring_preferred_another_result": 10.75268817204301
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
