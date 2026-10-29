# GLUE benchmark baseline

GLUE: 0.5.1
Algorithm SHA-256: `04e1428013ad46e2f3c0b2838429d5a841763db64a6ebf5221d7d16bc2c5df96`

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
      "candidate_recall": 0.15,
      "eligible_candidate_recall": 0.1875,
      "failure_counts": {
        "correct_candidate_never_generated": 156,
        "blocked_by_permissions_or_lock": 48,
        "recovered": 7,
        "scoring_preferred_another_result": 16,
        "required_combination_not_discovered": 9,
        "correct_candidate_generated_but_pruned": 4
      },
      "category_percent_of_all_targets": {
        "blocked_by_permissions_or_lock": 20.0,
        "correct_candidate_generated_but_pruned": 1.6666666666666667,
        "correct_candidate_never_generated": 65.0,
        "recovered": 2.9166666666666665,
        "required_combination_not_discovered": 3.75,
        "scoring_preferred_another_result": 6.666666666666667
      },
      "category_percent_of_eligible_failures": {
        "correct_candidate_generated_but_pruned": 2.1621621621621623,
        "correct_candidate_never_generated": 84.32432432432432,
        "required_combination_not_discovered": 4.864864864864865,
        "scoring_preferred_another_result": 8.64864864864865
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
  "partial_field_recovery": 0.0077777777777777776,
  "corrupted_note_improvement_rate": 0.011666666666666667,
  "clean_pitch_edits": 29,
  "clean_timing_edits": 0,
  "clean_duration_edits": 0,
  "clean_octave_displacements": 4,
  "clean_octave_displacement_rate": 0.002380952380952381,
  "clean_motif_disturbance_runs": 0,
  "exact_recovery_rate": 0.01,
  "unnecessary_edit_count": 278,
  "unnecessary_field_edits": 287,
  "clean_runs": 60,
  "clean_notes": 1680,
  "clean_false_positive_rate": 0.017261904761904763,
  "made_worse_runs": 78,
  "mean_runtime_seconds": 0.2641780576666012,
  "total_runtime_seconds": 158.5068345999607,
  "mean_distance_before": 2.000101273148148,
  "mean_distance_after": 3.8241753472222224
}
```

Skipped/inapplicable cases: 0 (see JSON for reasons).

## By dataset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| maestro | 600 | 0.0100 | 278 / 287 | 0.0173 | 78 | 0.2642 |

## By kind

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| accidental | 60 | 0.0000 | 32 / 32 | n/a | 8 | 0.2840 |
| clean | 60 | n/a | 29 / 29 | 0.0173 | 8 | 0.2740 |
| coordinated | 60 | 0.0000 | 30 / 30 | n/a | 9 | 0.2087 |
| early | 60 | 0.0000 | 25 / 28 | n/a | 8 | 0.2632 |
| groove | 60 | 0.0000 | 29 / 31 | n/a | 8 | 0.2745 |
| late | 60 | 0.0000 | 27 / 29 | n/a | 8 | 0.2648 |
| octave | 60 | 0.1000 | 27 / 27 | n/a | 6 | 0.2655 |
| short | 60 | 0.0000 | 27 / 27 | n/a | 7 | 0.2686 |
| sustain | 60 | 0.0000 | 27 / 29 | n/a | 8 | 0.2897 |
| timing_duration | 60 | 0.0000 | 25 / 25 | n/a | 8 | 0.2488 |

## By preset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| balanced | 200 | 0.0100 | 97 / 101 | 0.0179 | 29 | 0.1925 |
| creative | 200 | 0.0100 | 145 / 149 | 0.0268 | 31 | 0.5649 |
| minimal | 200 | 0.0100 | 36 / 37 | 0.0071 | 18 | 0.0352 |

## By preservation

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| (0,) | 120 | 0.0500 | 278 / 287 | 0.0863 | 78 | 0.4701 |
| (100,) | 120 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0034 |
| (25,) | 120 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.4413 |
| (50,) | 120 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.2979 |
| (75,) | 120 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.1082 |

## By workflow

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| single | 600 | 0.0100 | 278 / 287 | 0.0173 | 78 | 0.2642 |

## Worst examples (distance + 10 × unnecessary field edits)

- 2013/ORIG-MIDI_02_7_7_13_Group__MID--AUDIO_18_R1_2013_wav--1.midi@76:84 / accidental / creative / (0,): distance 1.000 → 42.000; 6 unnecessary field edits.
- 2013/ORIG-MIDI_02_7_7_13_Group__MID--AUDIO_18_R1_2013_wav--1.midi@76:84 / octave / creative / (0,): distance 12.000 → 40.000; 6 unnecessary field edits.
- 2013/ORIG-MIDI_02_7_7_13_Group__MID--AUDIO_18_R1_2013_wav--1.midi@76:84 / short / creative / (0,): distance 0.539 → 28.539; 6 unnecessary field edits.
- 2015/MIDI-Unprocessed_R2_D2-12-13-15_mid--AUDIO-from_mp3_12_R2_2015_wav--1.midi@256:264 / coordinated / creative / (0,): distance 3.250 → 18.250; 7 unnecessary field edits.
- 2013/ORIG-MIDI_02_7_7_13_Group__MID--AUDIO_18_R1_2013_wav--1.midi@76:84 / early / creative / (0,): distance 0.125 → 28.125; 6 unnecessary field edits.
- 2013/ORIG-MIDI_02_7_7_13_Group__MID--AUDIO_18_R1_2013_wav--1.midi@76:84 / late / creative / (0,): distance 0.125 → 28.125; 6 unnecessary field edits.
- 2013/ORIG-MIDI_02_7_7_13_Group__MID--AUDIO_18_R1_2013_wav--1.midi@76:84 / clean / creative / (0,): distance 0.000 → 28.000; 6 unnecessary field edits.
- 2013/ORIG-MIDI_02_7_7_13_Group__MID--AUDIO_18_R1_2013_wav--1.midi@76:84 / sustain / creative / (0,): distance 0.500 → 27.500; 6 unnecessary field edits.
- 2014/MIDI-UNPROCESSED_06-08_R1_2014_MID--AUDIO_07_R1_2014_wav--3.midi@384:392 / accidental / creative / (0,): distance 1.000 → 22.000; 6 unnecessary field edits.
- 2014/MIDI-UNPROCESSED_06-08_R1_2014_MID--AUDIO_07_R1_2014_wav--3.midi@384:392 / groove / creative / (0,): distance 0.125 → 28.125; 5 unnecessary field edits.

## Failure attribution

Hypotheses are not proven causes. Coverage gaps are observed; their upstream cause
may be analysis, harmony inference, filtering or permissions. Search and scoring
cannot always be distinguished without a production trace API.

```json
{
  "candidate generation": 408,
  "harmony inference": 408,
  "analysis": 416,
  "preservation penalties": 444,
  "timing logic": 240,
  "duration logic": 192,
  "scoring": 155,
  "search": 20
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
    "candidate_recall": 0.15,
    "eligible_candidate_recall": 0.1875,
    "failure_counts": {
      "correct_candidate_never_generated": 156,
      "blocked_by_permissions_or_lock": 48,
      "recovered": 7,
      "scoring_preferred_another_result": 16,
      "required_combination_not_discovered": 9,
      "correct_candidate_generated_but_pruned": 4
    },
    "category_percent_of_all_targets": {
      "blocked_by_permissions_or_lock": 20.0,
      "correct_candidate_generated_but_pruned": 1.6666666666666667,
      "correct_candidate_never_generated": 65.0,
      "recovered": 2.9166666666666665,
      "required_combination_not_discovered": 3.75,
      "scoring_preferred_another_result": 6.666666666666667
    },
    "category_percent_of_eligible_failures": {
      "correct_candidate_generated_but_pruned": 2.1621621621621623,
      "correct_candidate_never_generated": 84.32432432432432,
      "required_combination_not_discovered": 4.864864864864865,
      "scoring_preferred_another_result": 8.64864864864865
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
