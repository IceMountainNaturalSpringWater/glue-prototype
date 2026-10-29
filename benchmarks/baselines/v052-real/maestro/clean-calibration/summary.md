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
  "edit_type_diagnostics": {},
  "runs": 60,
  "errors": 0,
  "corrupted_notes": 0,
  "partial_field_recovery": null,
  "corrupted_note_improvement_rate": null,
  "clean_pitch_edits": 29,
  "clean_timing_edits": 0,
  "clean_duration_edits": 0,
  "clean_octave_displacements": 4,
  "clean_octave_displacement_rate": 0.002380952380952381,
  "clean_motif_disturbance_runs": 0,
  "exact_recovery_rate": null,
  "unnecessary_edit_count": 29,
  "unnecessary_field_edits": 29,
  "clean_runs": 60,
  "clean_notes": 1680,
  "clean_false_positive_rate": 0.017261904761904763,
  "made_worse_runs": 8,
  "mean_runtime_seconds": 0.27654041833399484,
  "total_runtime_seconds": 16.59242510003969,
  "mean_distance_before": null,
  "mean_distance_after": null
}
```

Skipped/inapplicable cases: 0 (see JSON for reasons).

## By dataset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| maestro | 60 | n/a | 29 / 29 | 0.0173 | 8 | 0.2765 |

## By kind

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| clean | 60 | n/a | 29 / 29 | 0.0173 | 8 | 0.2765 |

## By preset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| balanced | 20 | n/a | 10 / 10 | 0.0179 | 3 | 0.1938 |
| creative | 20 | n/a | 15 / 15 | 0.0268 | 3 | 0.5980 |
| minimal | 20 | n/a | 4 / 4 | 0.0071 | 2 | 0.0378 |

## By preservation

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| (0,) | 12 | n/a | 29 / 29 | 0.0863 | 8 | 0.4923 |
| (100,) | 12 | n/a | 0 / 0 | 0.0000 | 0 | 0.0034 |
| (25,) | 12 | n/a | 0 / 0 | 0.0000 | 0 | 0.4601 |
| (50,) | 12 | n/a | 0 / 0 | 0.0000 | 0 | 0.3137 |
| (75,) | 12 | n/a | 0 / 0 | 0.0000 | 0 | 0.1132 |

## By workflow

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| single | 60 | n/a | 29 / 29 | 0.0173 | 8 | 0.2765 |

## Worst examples (distance + 10 × unnecessary field edits)

- 2013/ORIG-MIDI_02_7_7_13_Group__MID--AUDIO_18_R1_2013_wav--1.midi@76:84 / clean / creative / (0,): distance 0.000 → 28.000; 6 unnecessary field edits.
- 2013/ORIG-MIDI_02_7_7_13_Group__MID--AUDIO_18_R1_2013_wav--1.midi@76:84 / clean / balanced / (0,): distance 0.000 → 29.000; 4 unnecessary field edits.
- 2015/MIDI-Unprocessed_R2_D2-12-13-15_mid--AUDIO-from_mp3_12_R2_2015_wav--1.midi@256:264 / clean / creative / (0,): distance 0.000 → 13.000; 5 unnecessary field edits.
- 2014/MIDI-UNPROCESSED_06-08_R1_2014_MID--AUDIO_07_R1_2014_wav--3.midi@384:392 / clean / creative / (0,): distance 0.000 → 22.000; 4 unnecessary field edits.
- 2015/MIDI-Unprocessed_R2_D2-12-13-15_mid--AUDIO-from_mp3_12_R2_2015_wav--1.midi@256:264 / clean / balanced / (0,): distance 0.000 → 7.000; 4 unnecessary field edits.
- 2013/ORIG-MIDI_02_7_7_13_Group__MID--AUDIO_18_R1_2013_wav--1.midi@76:84 / clean / minimal / (0,): distance 0.000 → 13.000; 2 unnecessary field edits.
- 2014/MIDI-UNPROCESSED_06-08_R1_2014_MID--AUDIO_07_R1_2014_wav--3.midi@384:392 / clean / balanced / (0,): distance 0.000 → 7.000; 2 unnecessary field edits.
- 2015/MIDI-Unprocessed_R2_D2-12-13-15_mid--AUDIO-from_mp3_12_R2_2015_wav--1.midi@256:264 / clean / minimal / (0,): distance 0.000 → 4.000; 2 unnecessary field edits.
- 2009/MIDI-Unprocessed_10_R1_2009_03-05_ORIG_MID--AUDIO_10_R1_2009_10_R1_2009_03_WAV.midi@368:376 / clean / balanced / (0,): distance 0.000 → 0.000; 0 unnecessary field edits.
- 2009/MIDI-Unprocessed_10_R1_2009_03-05_ORIG_MID--AUDIO_10_R1_2009_10_R1_2009_03_WAV.midi@368:376 / clean / balanced / (25,): distance 0.000 → 0.000; 0 unnecessary field edits.

## Failure attribution

Hypotheses are not proven causes. Coverage gaps are observed; their upstream cause
may be analysis, harmony inference, filtering or permissions. Search and scoring
cannot always be distinguished without a production trace API.

```json
{
  "scoring": 16,
  "analysis": 8
}
```

See results.json for exact ledgers, source event bindings, component metrics,
retained-alternative diagnostics, failures, and runtime vs note count.
