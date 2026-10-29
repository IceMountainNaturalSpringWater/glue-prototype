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
  "edit_type_diagnostics": {},
  "runs": 60,
  "errors": 0,
  "corrupted_notes": 0,
  "partial_field_recovery": null,
  "corrupted_note_improvement_rate": null,
  "clean_pitch_edits": 27,
  "clean_timing_edits": 0,
  "clean_duration_edits": 0,
  "clean_octave_displacements": 20,
  "clean_octave_displacement_rate": 0.011695906432748537,
  "clean_motif_disturbance_runs": 0,
  "exact_recovery_rate": null,
  "unnecessary_edit_count": 27,
  "unnecessary_field_edits": 27,
  "clean_runs": 60,
  "clean_notes": 1710,
  "clean_false_positive_rate": 0.015789473684210527,
  "made_worse_runs": 12,
  "mean_runtime_seconds": 0.09888741333173433,
  "total_runtime_seconds": 5.93324479990406,
  "mean_distance_before": null,
  "mean_distance_after": null
}
```

Skipped/inapplicable cases: 0 (see JSON for reasons).

## By dataset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| maestro | 60 | n/a | 27 / 27 | 0.0158 | 12 | 0.0989 |

## By kind

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| clean | 60 | n/a | 27 / 27 | 0.0158 | 12 | 0.0989 |

## By preset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| balanced | 20 | n/a | 9 / 9 | 0.0158 | 4 | 0.0730 |
| creative | 20 | n/a | 11 / 11 | 0.0193 | 4 | 0.1992 |
| minimal | 20 | n/a | 7 / 7 | 0.0123 | 4 | 0.0245 |

## By preservation

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| (0,) | 12 | n/a | 27 / 27 | 0.0789 | 12 | 0.1453 |
| (100,) | 12 | n/a | 0 / 0 | 0.0000 | 0 | 0.0028 |
| (25,) | 12 | n/a | 0 / 0 | 0.0000 | 0 | 0.1712 |
| (50,) | 12 | n/a | 0 / 0 | 0.0000 | 0 | 0.1178 |
| (75,) | 12 | n/a | 0 / 0 | 0.0000 | 0 | 0.0573 |

## By workflow

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| single | 60 | n/a | 27 / 27 | 0.0158 | 12 | 0.0989 |

## Worst examples (distance + 10 × unnecessary field edits)

- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / clean / creative / (0,): distance 0.000 → 45.000; 6 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / clean / balanced / (0,): distance 0.000 → 30.000; 4 unnecessary field edits.
- 2004/MIDI-Unprocessed_XP_08_R1_2004_04-06_ORIG_MID--AUDIO_08_R1_2004_05_Track05_wav--1.midi@444:452 / clean / balanced / (0,): distance 0.000 → 24.000; 2 unnecessary field edits.
- 2004/MIDI-Unprocessed_XP_08_R1_2004_04-06_ORIG_MID--AUDIO_08_R1_2004_05_Track05_wav--1.midi@444:452 / clean / creative / (0,): distance 0.000 → 24.000; 2 unnecessary field edits.
- 2004/MIDI-Unprocessed_XP_08_R1_2004_04-06_ORIG_MID--AUDIO_08_R1_2004_05_Track05_wav--1.midi@444:452 / clean / minimal / (0,): distance 0.000 → 24.000; 2 unnecessary field edits.
- 2008/MIDI-Unprocessed_17_R1_2008_01-04_ORIG_MID--AUDIO_17_R1_2008_wav--3.midi@156:164 / clean / minimal / (0,): distance 0.000 → 24.000; 2 unnecessary field edits.
- 2009/MIDI-Unprocessed_03_R1_2009_03-08_ORIG_MID--AUDIO_03_R1_2009_03_R1_2009_03_WAV.midi@788:796 / clean / minimal / (0,): distance 0.000 → 24.000; 2 unnecessary field edits.
- 2009/MIDI-Unprocessed_03_R1_2009_03-08_ORIG_MID--AUDIO_03_R1_2009_03_R1_2009_03_WAV.midi@788:796 / clean / balanced / (0,): distance 0.000 → 15.000; 2 unnecessary field edits.
- 2009/MIDI-Unprocessed_03_R1_2009_03-08_ORIG_MID--AUDIO_03_R1_2009_03_R1_2009_03_WAV.midi@788:796 / clean / creative / (0,): distance 0.000 → 15.000; 2 unnecessary field edits.
- 2017/MIDI-Unprocessed_083_PIANO083_MID--AUDIO-split_07-09-17_Piano-e_2_-06_wav--1.midi@316:324 / clean / balanced / (0,): distance 0.000 → 12.000; 1 unnecessary field edits.

## Failure attribution

Hypotheses are not proven causes. Coverage gaps are observed; their upstream cause
may be analysis, harmony inference, filtering or permissions. Search and scoring
cannot always be distinguished without a production trace API.

```json
{
  "scoring": 22,
  "analysis": 12
}
```

See results.json for exact ledgers, source event bindings, component metrics,
retained-alternative diagnostics, failures, and runtime vs note count.
