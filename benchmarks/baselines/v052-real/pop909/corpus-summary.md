# pop909 frozen real-corpus baseline

Engine SHA-256: `04e1428013ad46e2f3c0b2838429d5a841763db64a6ebf5221d7d16bc2c5df96`

## Counts

```json
{
  "detected_midi": 2898,
  "canonical_or_metadata_listed": 909,
  "parse_valid": 909,
  "excluded_variants": 1989,
  "split_quarantined": 0,
  "benchmark_eligible": 909,
  "eligible_splits": {
    "calibration": 700,
    "evaluation": 209
  },
  "sampled_pieces": 8,
  "sampled_windows": 8,
  "unique_window_notes": 389,
  "sample_splits": {
    "calibration": 4,
    "evaluation": 4
  },
  "runs": 1080,
  "corrupted_runs": 960,
  "clean_runs": 120,
  "skipped_cases": 0
}
```

No weights or repair behavior changed during this measurement phase.

## Corruption type

| Setting | Runs | Exact recovery | Field recovery | Corrupted notes improved | Untouched preservation | Clean FP |
|---|---:|---:|---:|---:|---:|---:|
| accidental | 120 | 0.83% | 1.67% | 1.67% | 97.50% | n/a |
| attack_collision | 120 | 0.00% | 0.00% | 0.00% | 97.50% | n/a |
| clean | 120 | n/a | n/a | n/a | n/a | 2.33% |
| coordinated | 120 | 0.00% | 2.22% | 7.50% | 97.62% | n/a |
| early | 120 | 0.00% | 0.00% | 0.00% | 97.59% | n/a |
| octave | 120 | 0.00% | 0.00% | 0.00% | 97.55% | n/a |
| pitch_timing | 120 | 0.00% | 2.92% | 5.83% | 97.46% | n/a |
| short | 120 | 0.00% | 0.00% | 0.00% | 97.69% | n/a |
| sustain | 120 | 0.00% | 0.00% | 0.00% | 97.67% | n/a |

## Preset

| Setting | Runs | Exact recovery | Field recovery | Corrupted notes improved | Untouched preservation | Clean FP |
|---|---:|---:|---:|---:|---:|---:|
| minimal | 360 | 0.00% | 0.89% | 1.39% | 99.35% | 0.62% |
| balanced | 360 | 0.28% | 1.61% | 3.06% | 97.18% | 2.67% |
| creative | 360 | 0.00% | 1.96% | 3.06% | 96.19% | 3.70% |

## Preservation

| Setting | Runs | Exact recovery | Field recovery | Corrupted notes improved | Untouched preservation | Clean FP |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 216 | 0.46% | 5.65% | 9.26% | 92.49% | 7.11% |
| 25 | 216 | 0.00% | 1.19% | 2.31% | 95.86% | 4.11% |
| 50 | 216 | 0.00% | 0.60% | 0.93% | 99.52% | 0.43% |
| 75 | 216 | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% |
| 100 | 216 | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% |

## Split

| Setting | Runs | Exact recovery | Field recovery | Corrupted notes improved | Untouched preservation | Clean FP |
|---|---:|---:|---:|---:|---:|---:|
| calibration | 540 | 0.00% | 1.31% | 2.41% | 97.30% | 2.65% |
| evaluation | 540 | 0.19% | 1.67% | 2.59% | 97.91% | 1.94% |

## Candidate recall

All-target recall includes hard locks; editable recall excludes locked/disabled fields.

| Edit type | Targets | Generated | Recall | Editable recall |
|---|---:|---:|---:|---:|
| duration | 480 | 8 | 1.67% | 2.08% |
| pitch | 600 | 195 | 32.50% | 40.62% |
| timing | 600 | 28 | 4.67% | 5.83% |

## Failure classification

```json
{
  "duration": {
    "analysis_failure": null,
    "analysis_note": "Not independently attributable from note recovery alone; unknown, not zero.",
    "correct_candidate_missing": 376,
    "candidate_pruned": 0,
    "scoring_rejected_correct_candidate": 4,
    "coordinated_search_failure": 3,
    "other_outcomes": {
      "blocked_by_permissions_or_lock": 96,
      "generated_not_entered_search": 1
    },
    "percentages": {
      "blocked_by_permissions_or_lock": 20.0,
      "correct_candidate_never_generated": 78.33333333333333,
      "generated_not_entered_search": 0.20833333333333334,
      "required_combination_not_discovered": 0.625,
      "scoring_preferred_another_result": 0.8333333333333334
    }
  },
  "pitch": {
    "analysis_failure": null,
    "analysis_note": "Not independently attributable from note recovery alone; unknown, not zero.",
    "correct_candidate_missing": 285,
    "candidate_pruned": 18,
    "scoring_rejected_correct_candidate": 53,
    "coordinated_search_failure": 66,
    "other_outcomes": {
      "blocked_by_permissions_or_lock": 120,
      "recovered": 23,
      "constraint_or_budget_rejection": 35
    },
    "percentages": {
      "blocked_by_permissions_or_lock": 20.0,
      "constraint_or_budget_rejection": 5.833333333333333,
      "correct_candidate_generated_but_pruned": 3.0,
      "correct_candidate_never_generated": 47.5,
      "recovered": 3.8333333333333335,
      "required_combination_not_discovered": 11.0,
      "scoring_preferred_another_result": 8.833333333333334
    }
  },
  "timing": {
    "analysis_failure": null,
    "analysis_note": "Not independently attributable from note recovery alone; unknown, not zero.",
    "correct_candidate_missing": 452,
    "candidate_pruned": 1,
    "scoring_rejected_correct_candidate": 5,
    "coordinated_search_failure": 20,
    "other_outcomes": {
      "blocked_by_permissions_or_lock": 120,
      "recovered": 2
    },
    "percentages": {
      "blocked_by_permissions_or_lock": 20.0,
      "correct_candidate_generated_but_pruned": 0.16666666666666666,
      "correct_candidate_never_generated": 75.33333333333333,
      "recovered": 0.3333333333333333,
      "required_combination_not_discovered": 3.3333333333333335,
      "scoring_preferred_another_result": 0.8333333333333334
    }
  }
}
```

Analysis attribution is unknown, not 0%. Missing candidates can have upstream analysis causes.
Pruned states can still be retained by the engine; pruning alone is not proof of loss.

## Clean edits and runtime

```json
{
  "clean_pitch_edits": 35,
  "clean_timing_edits": 101,
  "clean_duration_edits": 8,
  "clean_octave_displacements": 0,
  "clean_octave_displacement_rate": 0.0,
  "clean_motif_disturbance_runs": 0,
  "clean_runs": 120,
  "clean_notes": 5835,
  "clean_false_positive_rate": 0.023307626392459296
}
```

```json
{
  "repair_seconds": 371.8480054000829,
  "median_seconds": 0.16030214999773307,
  "p95_seconds": 1.1169174000096973,
  "max_seconds": 1.7674682999931974,
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

