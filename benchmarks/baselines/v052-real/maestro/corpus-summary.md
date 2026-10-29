# maestro frozen real-corpus baseline

Engine SHA-256: `04e1428013ad46e2f3c0b2838429d5a841763db64a6ebf5221d7d16bc2c5df96`

## Counts

```json
{
  "detected_midi": 1276,
  "canonical_or_metadata_listed": 1276,
  "parse_valid": 1275,
  "excluded_variants": 0,
  "split_quarantined": 11,
  "benchmark_eligible": 1264,
  "eligible_splits": {
    "calibration": 1093,
    "evaluation": 171
  },
  "sampled_pieces": 8,
  "sampled_windows": 8,
  "unique_window_notes": 226,
  "sample_splits": {
    "calibration": 4,
    "evaluation": 4
  },
  "runs": 1200,
  "corrupted_runs": 1080,
  "clean_runs": 120,
  "skipped_cases": 0
}
```

No weights or repair behavior changed during this measurement phase.

## Corruption type

| Setting | Runs | Exact recovery | Field recovery | Corrupted notes improved | Untouched preservation | Clean FP |
|---|---:|---:|---:|---:|---:|---:|
| accidental | 120 | 1.67% | 1.67% | 1.67% | 98.26% | n/a |
| clean | 120 | n/a | n/a | n/a | n/a | 1.65% |
| coordinated | 120 | 0.00% | 1.11% | 3.33% | 98.16% | n/a |
| early | 120 | 0.00% | 0.00% | 0.00% | 98.41% | n/a |
| groove | 120 | 0.00% | 0.00% | 0.00% | 98.29% | n/a |
| late | 120 | 0.00% | 0.00% | 0.00% | 98.35% | n/a |
| octave | 120 | 5.00% | 5.00% | 5.00% | 98.38% | n/a |
| short | 120 | 0.00% | 0.00% | 0.00% | 98.35% | n/a |
| sustain | 120 | 0.00% | 0.00% | 0.00% | 98.29% | n/a |
| timing_duration | 120 | 0.00% | 0.00% | 0.00% | 98.35% | n/a |

## Preset

| Setting | Runs | Exact recovery | Field recovery | Corrupted notes improved | Untouched preservation | Clean FP |
|---|---:|---:|---:|---:|---:|---:|
| minimal | 400 | 0.50% | 1.00% | 1.50% | 99.07% | 0.97% |
| balanced | 400 | 0.75% | 0.83% | 1.25% | 98.26% | 1.68% |
| creative | 400 | 0.75% | 0.83% | 1.25% | 97.62% | 2.30% |

## Preservation

| Setting | Runs | Exact recovery | Field recovery | Corrupted notes improved | Untouched preservation | Clean FP |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 240 | 3.33% | 3.61% | 5.42% | 91.57% | 8.26% |
| 25 | 240 | 0.00% | 0.83% | 1.25% | 100.00% | 0.00% |
| 50 | 240 | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% |
| 75 | 240 | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% |
| 100 | 240 | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% |

## Split

| Setting | Runs | Exact recovery | Field recovery | Corrupted notes improved | Untouched preservation | Clean FP |
|---|---:|---:|---:|---:|---:|---:|
| calibration | 600 | 1.00% | 0.78% | 1.17% | 98.29% | 1.73% |
| evaluation | 600 | 0.33% | 1.00% | 1.50% | 98.34% | 1.58% |

## Candidate recall

All-target recall includes hard locks; editable recall excludes locked/disabled fields.

| Edit type | Targets | Generated | Recall | Editable recall |
|---|---:|---:|---:|---:|
| duration | 600 | 0 | 0.00% | 0.00% |
| pitch | 480 | 83 | 17.29% | 21.61% |
| timing | 720 | 0 | 0.00% | 0.00% |

## Failure classification

```json
{
  "duration": {
    "analysis_failure": null,
    "analysis_note": "Not independently attributable from note recovery alone; unknown, not zero.",
    "correct_candidate_missing": 480,
    "candidate_pruned": 0,
    "scoring_rejected_correct_candidate": 0,
    "coordinated_search_failure": 0,
    "other_outcomes": {
      "blocked_by_permissions_or_lock": 120
    },
    "percentages": {
      "blocked_by_permissions_or_lock": 20.0,
      "correct_candidate_never_generated": 80.0
    }
  },
  "pitch": {
    "analysis_failure": null,
    "analysis_note": "Not independently attributable from note recovery alone; unknown, not zero.",
    "correct_candidate_missing": 301,
    "candidate_pruned": 4,
    "scoring_rejected_correct_candidate": 34,
    "coordinated_search_failure": 29,
    "other_outcomes": {
      "blocked_by_permissions_or_lock": 96,
      "recovered": 16
    },
    "percentages": {
      "blocked_by_permissions_or_lock": 20.0,
      "correct_candidate_generated_but_pruned": 0.8333333333333334,
      "correct_candidate_never_generated": 62.708333333333336,
      "recovered": 3.3333333333333335,
      "required_combination_not_discovered": 6.041666666666667,
      "scoring_preferred_another_result": 7.083333333333333
    }
  },
  "timing": {
    "analysis_failure": null,
    "analysis_note": "Not independently attributable from note recovery alone; unknown, not zero.",
    "correct_candidate_missing": 576,
    "candidate_pruned": 0,
    "scoring_rejected_correct_candidate": 0,
    "coordinated_search_failure": 0,
    "other_outcomes": {
      "blocked_by_permissions_or_lock": 144
    },
    "percentages": {
      "blocked_by_permissions_or_lock": 20.0,
      "correct_candidate_never_generated": 80.0
    }
  }
}
```

Analysis attribution is unknown, not 0%. Missing candidates can have upstream analysis causes.
Pruned states can still be retained by the engine; pruning alone is not proof of loss.

## Clean edits and runtime

```json
{
  "clean_pitch_edits": 56,
  "clean_timing_edits": 0,
  "clean_duration_edits": 0,
  "clean_octave_displacements": 24,
  "clean_octave_displacement_rate": 0.007079646017699115,
  "clean_motif_disturbance_runs": 0,
  "clean_runs": 120,
  "clean_notes": 3390,
  "clean_false_positive_rate": 0.016519174041297935
}
```

```json
{
  "repair_seconds": 229.17078050010605,
  "median_seconds": 0.034227500000270084,
  "p95_seconds": 1.0588647999975365,
  "max_seconds": 1.7851582000002963,
  "scope": "repair invocation including trace, excluding loading/corruption/metrics"
}
```

## Limitations

- Eight short passages, not full-corpus musical validation.
- Density-stratified, count-bounded windows omit preceding sustained notes.
- Professional performance is a reference, not a proof every original note is correct.
- Clean/corrupted observations repeat across settings; not independent compositions.
- Analysis failure attribution remains unknown without independent context labels.

Full target ranks, scored components, rejection reasons and worst examples are in JSON.

