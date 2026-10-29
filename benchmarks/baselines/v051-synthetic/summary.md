# GLUE benchmark baseline

GLUE: 0.5.1
Algorithm SHA-256: `b9f12bfccfcf879514ab116511e486b87a8ae2de1e7fee504f144618a22c4a7f`

Dataset: synthetic-framework-validation; split: calibration.
Self-authored CC0 synthetic references; NOT POP909/MAESTRO results, not human-rated musical ground truth. Evaluation piece held out.

This measures recovery of designated references, not objective musical quality.
Top-ranked candidate only; no oracle selection or tuning. Clean controls are mandatory.
Timing is machine-dependent; deterministic digests exclude runtime/environment.

## Overall

```json
{
  "runs": 684,
  "errors": 0,
  "corrupted_notes": 684,
  "exact_recovery_rate": 0.01608187134502924,
  "unnecessary_edit_count": 91,
  "unnecessary_field_edits": 91,
  "clean_runs": 42,
  "clean_notes": 384,
  "clean_false_positive_rate": 0.015625,
  "made_worse_runs": 65,
  "mean_runtime_seconds": 0.011001433187147356,
  "total_runtime_seconds": 7.524980300008792,
  "mean_distance_before": 1.7114485981308412,
  "mean_distance_after": 2.9318535825545173
}
```

Skipped/inapplicable cases: 11 (see JSON for reasons).

## By kind

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| accidental | 42 | 0.0476 | 6 / 6 | n/a | 6 | 0.0098 |
| attack_collision | 30 | 0.0000 | 6 / 6 | n/a | 6 | 0.0058 |
| bass_lead_collision | 12 | 0.0000 | 6 / 6 | n/a | 3 | 0.0143 |
| bass_pitch | 42 | 0.1190 | 3 / 3 | n/a | 3 | 0.0124 |
| call_response | 18 | 0.0000 | 2 / 2 | n/a | 8 | 0.0121 |
| clean | 42 | n/a | 6 / 6 | 0.0156 | 3 | 0.0060 |
| coordinated | 42 | 0.0000 | 8 / 8 | n/a | 3 | 0.0103 |
| early | 42 | 0.0000 | 6 / 6 | n/a | 3 | 0.0072 |
| groove | 42 | 0.0000 | 0 / 0 | n/a | 0 | 0.0036 |
| harmony_overlap | 12 | 0.0000 | 3 / 3 | n/a | 3 | 0.0139 |
| late | 42 | 0.0000 | 0 / 0 | n/a | 0 | 0.0041 |
| motif | 12 | 0.2500 | 0 / 0 | n/a | 0 | 0.0049 |
| octave | 42 | 0.0000 | 6 / 6 | n/a | 3 | 0.0116 |
| pitch_duration | 42 | 0.0000 | 10 / 10 | n/a | 6 | 0.0529 |
| pitch_timing | 42 | 0.0000 | 0 / 0 | n/a | 0 | 0.0061 |
| short | 42 | 0.0000 | 6 / 6 | n/a | 3 | 0.0073 |
| sustain | 42 | 0.0000 | 6 / 6 | n/a | 3 | 0.0072 |
| timing_duration | 42 | 0.0000 | 3 / 3 | n/a | 3 | 0.0075 |
| wrong_chord_tone | 12 | 0.0000 | 6 / 6 | n/a | 3 | 0.0176 |
| wrong_diatonic | 42 | 0.0238 | 8 / 8 | n/a | 6 | 0.0092 |

## By preset

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| balanced | 228 | 0.0175 | 32 / 32 | 0.0156 | 24 | 0.0109 |
| creative | 228 | 0.0175 | 34 / 34 | 0.0156 | 24 | 0.0151 |
| minimal | 228 | 0.0132 | 25 / 25 | 0.0156 | 17 | 0.0070 |

## By preservation

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| (0, 0) | 48 | 0.0000 | 2 / 2 | 0.0000 | 4 | 0.0056 |
| (0, 100) | 48 | 0.0000 | 2 / 2 | 0.0000 | 4 | 0.0046 |
| (0,) | 99 | 0.1111 | 83 / 83 | 0.1000 | 51 | 0.0278 |
| (100, 0) | 48 | 0.0000 | 2 / 2 | 0.0000 | 2 | 0.0047 |
| (100, 100) | 48 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0039 |
| (100,) | 99 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0025 |
| (50, 50) | 48 | 0.0000 | 2 / 2 | 0.0000 | 4 | 0.0056 |
| (50,) | 99 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0217 |
| (90, 90) | 48 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0056 |
| (90,) | 99 | 0.0000 | 0 / 0 | 0.0000 | 0 | 0.0095 |

## By workflow

| Setting | Runs | Exact recovery | Unnecessary notes / fields | Clean FP | Worse | Mean s |
|---|---:|---:|---:|---:|---:|---:|
| pair | 288 | 0.0000 | 8 / 8 | 0.0000 | 14 | 0.0050 |
| single | 396 | 0.0278 | 83 / 83 | 0.0250 | 51 | 0.0154 |

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
  "candidate generation": 377,
  "harmony inference": 377,
  "analysis": 380,
  "preservation penalties": 471,
  "search": 12,
  "timing logic": 205,
  "scoring": 98,
  "duration logic": 168
}
```

See results.json for exact ledgers, source event bindings, component metrics,
retained-alternative diagnostics, failures, and runtime vs note count.
