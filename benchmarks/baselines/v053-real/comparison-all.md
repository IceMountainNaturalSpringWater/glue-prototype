# V0.5.2 -> V0.5.3 candidate comparison

Separate datasets and splits. Arrows mean before -> after; no pooled corpus score.
All counts repeat observations across settings. Unlocked excludes 100% preservation.
Candidate recall uses all targets in each group; unlocked excludes locked targets.
Recovery is exact unless marked partial. JSON also includes editable-field recall explicitly.

## pop909 / calibration

| Settings | Pitch recall | Timing recall | Duration recall | Exact notes | Partial fields | Clean FP | Untouched preservation | Mean seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| all | 46.00% -> 57.00% | 1.33% -> 19.67% | 0.00% -> 20.00% | 0.00% -> 0.19% | 1.31% -> 2.86% | 2.65% -> 1.68% | 97.30% -> 98.35% | 0.397 -> 0.401 |
| unlocked | 57.50% -> 71.25% | 1.67% -> 24.58% | 0.00% -> 25.00% | 0.00% -> 0.23% | 1.64% -> 3.57% | 3.31% -> 2.10% | 96.62% -> 97.93% | 0.494 -> 0.499 |
| preservation_0 | 58.33% -> 73.33% | 1.67% -> 25.00% | 0.00% -> 25.00% | 0.00% -> 0.93% | 4.76% -> 11.90% | 7.63% -> 6.85% | 92.12% -> 93.50% | 0.677 -> 0.665 |
| preservation_25 | 58.33% -> 71.67% | 1.67% -> 25.00% | 0.00% -> 25.00% | 0.00% -> 0.00% | 0.60% -> 1.79% | 4.83% -> 1.40% | 95.19% -> 98.37% | 0.553 -> 0.554 |
| preservation_50 | 58.33% -> 71.67% | 1.67% -> 25.00% | 0.00% -> 25.00% | 0.00% -> 0.00% | 1.19% -> 0.60% | 0.78% -> 0.16% | 99.16% -> 99.86% | 0.437 -> 0.454 |
| preservation_75 | 55.00% -> 68.33% | 1.67% -> 23.33% | 0.00% -> 25.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 100.00% -> 100.00% | 0.311 -> 0.323 |
| preservation_100 | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 100.00% -> 100.00% | 0.007 -> 0.007 |
| preset_minimal | 43.00% -> 53.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.71% -> 1.07% | 0.56% -> 0.56% | 99.38% -> 99.40% | 0.065 -> 0.092 |
| preset_balanced | 47.00% -> 58.00% | 4.00% -> 27.00% | 0.00% -> 15.00% | 0.00% -> 0.00% | 1.07% -> 2.50% | 3.27% -> 2.06% | 96.66% -> 98.03% | 0.401 -> 0.366 |
| preset_creative | 48.00% -> 60.00% | 0.00% -> 32.00% | 0.00% -> 45.00% | 0.00% -> 0.56% | 2.14% -> 5.00% | 4.11% -> 2.43% | 95.85% -> 97.60% | 0.725 -> 0.744 |

| Additional metric (all settings) | Before | After |
|---|---:|---:|
| clean_octave_displacements | 0 | 0 |
| clean_octave_displacement_rate | 0.0 | 0.0 |
| clean_timing_edits | 68 | 23 |
| clean_duration_edits | 4 | 9 |
| unnecessary_edit_count | 765 | 470 |
| made_worse_runs | 214 | 156 |
| total_runtime_seconds | 214.31617999996524 | 216.42611409979872 |
| Unnecessary pitch edits | 169 | 233 |
| Unnecessary onset_ticks edits | 613 | 192 |
| Unnecessary duration_ticks edits | 44 | 89 |

Coordinated-state counts (including locked controls):

```json
{
  "before": {
    "cases": 120,
    "all_generated": 0,
    "entered_search": 0,
    "scored": 0,
    "survived_beam": 0
  },
  "after": {
    "cases": 120,
    "all_generated": 15,
    "entered_search": 8,
    "scored": 7,
    "survived_beam": 0
  }
}
```

Failure migration (corrupted fields):

| Before | After | Count |
|---|---|---:|
| blocked_by_permissions_or_lock | blocked_by_permissions_or_lock | 168 |
| constraint_or_budget_rejection | constraint_or_budget_rejection | 25 |
| constraint_or_budget_rejection | correct_candidate_never_generated | 4 |
| constraint_or_budget_rejection | recovered | 1 |
| constraint_or_budget_rejection | scoring_preferred_another_result | 1 |
| correct_candidate_generated_but_pruned | correct_candidate_generated_but_pruned | 15 |
| correct_candidate_generated_but_pruned | correct_candidate_never_generated | 1 |
| correct_candidate_generated_but_pruned | scoring_preferred_another_result | 3 |
| correct_candidate_never_generated | constraint_or_budget_rejection | 34 |
| correct_candidate_never_generated | correct_candidate_generated_but_pruned | 18 |
| correct_candidate_never_generated | correct_candidate_never_generated | 386 |
| correct_candidate_never_generated | generated_not_entered_search | 5 |
| correct_candidate_never_generated | recovered | 7 |
| correct_candidate_never_generated | required_combination_not_discovered | 45 |
| correct_candidate_never_generated | scoring_preferred_another_result | 35 |
| recovered | recovered | 10 |
| recovered | required_combination_not_discovered | 1 |
| required_combination_not_discovered | generated_not_entered_search | 1 |
| required_combination_not_discovered | required_combination_not_discovered | 38 |
| required_combination_not_discovered | scoring_preferred_another_result | 3 |
| scoring_preferred_another_result | correct_candidate_generated_but_pruned | 3 |
| scoring_preferred_another_result | correct_candidate_never_generated | 3 |
| scoring_preferred_another_result | recovered | 6 |
| scoring_preferred_another_result | required_combination_not_discovered | 3 |
| scoring_preferred_another_result | scoring_preferred_another_result | 24 |

Analysis attribution remains undetermined. Pruning is observed history, not proof of causation.
Ground-truth values and scoring-loss examples are diagnostic only, never repair inputs.

## pop909 / evaluation

| Settings | Pitch recall | Timing recall | Duration recall | Exact notes | Partial fields | Clean FP | Untouched preservation | Mean seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| all | 19.00% -> 40.67% | 8.00% -> 21.00% | 3.33% -> 8.33% | 0.19% -> 0.00% | 1.67% -> 1.43% | 1.94% -> 1.90% | 97.91% -> 98.04% | 0.292 -> 0.355 |
| unlocked | 23.75% -> 50.83% | 10.00% -> 26.25% | 4.17% -> 10.42% | 0.23% -> 0.00% | 2.08% -> 1.79% | 2.43% -> 2.38% | 97.39% -> 97.56% | 0.363 -> 0.442 |
| preservation_0 | 25.00% -> 53.33% | 10.00% -> 26.67% | 4.17% -> 10.42% | 0.93% -> 0.00% | 6.55% -> 5.36% | 6.48% -> 7.43% | 92.94% -> 92.35% | 0.492 -> 0.597 |
| preservation_25 | 25.00% -> 51.67% | 10.00% -> 26.67% | 4.17% -> 10.42% | 0.00% -> 0.00% | 1.79% -> 1.79% | 3.24% -> 2.10% | 96.68% -> 97.87% | 0.401 -> 0.492 |
| preservation_50 | 23.33% -> 50.00% | 10.00% -> 26.67% | 4.17% -> 10.42% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 99.95% -> 100.00% | 0.325 -> 0.398 |
| preservation_75 | 21.67% -> 48.33% | 10.00% -> 25.00% | 4.17% -> 10.42% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 100.00% -> 100.00% | 0.234 -> 0.282 |
| preservation_100 | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 100.00% -> 100.00% | 0.007 -> 0.006 |
| preset_minimal | 18.00% -> 37.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 1.07% -> 1.43% | 0.69% -> 0.80% | 99.31% -> 99.24% | 0.068 -> 0.091 |
| preset_balanced | 19.00% -> 41.00% | 12.00% -> 31.00% | 10.00% -> 5.00% | 0.56% -> 0.00% | 2.14% -> 1.43% | 1.94% -> 2.17% | 97.82% -> 97.80% | 0.296 -> 0.340 |
| preset_creative | 20.00% -> 44.00% | 12.00% -> 32.00% | 0.00% -> 20.00% | 0.00% -> 0.00% | 1.79% -> 1.43% | 3.20% -> 2.74% | 96.61% -> 97.10% | 0.511 -> 0.633 |

| Additional metric (all settings) | Before | After |
|---|---:|---:|
| clean_octave_displacements | 0 | 0 |
| clean_octave_displacement_rate | 0.0 | 0.0 |
| clean_timing_edits | 33 | 18 |
| clean_duration_edits | 4 | 8 |
| unnecessary_edit_count | 478 | 450 |
| made_worse_runs | 142 | 115 |
| total_runtime_seconds | 157.53182540011767 | 191.62695419916417 |
| Unnecessary pitch edits | 176 | 279 |
| Unnecessary onset_ticks edits | 304 | 162 |
| Unnecessary duration_ticks edits | 38 | 65 |

Coordinated-state counts (including locked controls):

```json
{
  "before": {
    "cases": 120,
    "all_generated": 0,
    "entered_search": 0,
    "scored": 0,
    "survived_beam": 0
  },
  "after": {
    "cases": 120,
    "all_generated": 6,
    "entered_search": 2,
    "scored": 0,
    "survived_beam": 0
  }
}
```

Failure migration (corrupted fields):

| Before | After | Count |
|---|---|---:|
| blocked_by_permissions_or_lock | blocked_by_permissions_or_lock | 168 |
| constraint_or_budget_rejection | constraint_or_budget_rejection | 4 |
| correct_candidate_never_generated | constraint_or_budget_rejection | 23 |
| correct_candidate_never_generated | correct_candidate_generated_but_pruned | 14 |
| correct_candidate_never_generated | correct_candidate_never_generated | 454 |
| correct_candidate_never_generated | generated_not_entered_search | 8 |
| correct_candidate_never_generated | recovered | 3 |
| correct_candidate_never_generated | required_combination_not_discovered | 27 |
| correct_candidate_never_generated | scoring_preferred_another_result | 54 |
| generated_not_entered_search | correct_candidate_never_generated | 1 |
| recovered | correct_candidate_never_generated | 2 |
| recovered | recovered | 8 |
| recovered | scoring_preferred_another_result | 4 |
| required_combination_not_discovered | correct_candidate_never_generated | 8 |
| required_combination_not_discovered | generated_not_entered_search | 1 |
| required_combination_not_discovered | required_combination_not_discovered | 38 |
| scoring_preferred_another_result | correct_candidate_generated_but_pruned | 1 |
| scoring_preferred_another_result | correct_candidate_never_generated | 2 |
| scoring_preferred_another_result | recovered | 1 |
| scoring_preferred_another_result | required_combination_not_discovered | 3 |
| scoring_preferred_another_result | scoring_preferred_another_result | 16 |

Analysis attribution remains undetermined. Pruning is observed history, not proof of causation.
Ground-truth values and scoring-loss examples are diagnostic only, never repair inputs.

## maestro / calibration

| Settings | Pitch recall | Timing recall | Duration recall | Exact notes | Partial fields | Clean FP | Untouched preservation | Mean seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| all | 15.00% -> 21.67% | 0.00% -> 3.06% | 0.00% -> 1.33% | 1.00% -> 0.00% | 0.78% -> 0.44% | 1.73% -> 1.67% | 98.29% -> 98.29% | 0.264 -> 0.253 |
| unlocked | 18.75% -> 27.08% | 0.00% -> 3.82% | 0.00% -> 1.67% | 1.25% -> 0.00% | 0.97% -> 0.56% | 2.16% -> 2.08% | 97.86% -> 97.87% | 0.329 -> 0.315 |
| preservation_0 | 18.75% -> 29.17% | 0.00% -> 5.56% | 0.00% -> 1.67% | 5.00% -> 0.00% | 3.89% -> 2.22% | 8.63% -> 8.33% | 91.43% -> 91.46% | 0.470 -> 0.430 |
| preservation_25 | 18.75% -> 29.17% | 0.00% -> 4.17% | 0.00% -> 1.67% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 100.00% -> 100.00% | 0.441 -> 0.428 |
| preservation_50 | 18.75% -> 25.00% | 0.00% -> 2.78% | 0.00% -> 1.67% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 100.00% -> 100.00% | 0.298 -> 0.294 |
| preservation_75 | 18.75% -> 25.00% | 0.00% -> 2.78% | 0.00% -> 1.67% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 100.00% -> 100.00% | 0.108 -> 0.109 |
| preservation_100 | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 100.00% -> 100.00% | 0.003 -> 0.004 |
| preset_minimal | 15.00% -> 17.50% | 0.00% -> 0.00% | 0.00% -> 0.00% | 1.00% -> 0.00% | 1.00% -> 0.00% | 0.71% -> 0.71% | 99.34% -> 99.21% | 0.035 -> 0.043 |
| preset_balanced | 15.00% -> 22.50% | 0.00% -> 4.17% | 0.00% -> 0.00% | 1.00% -> 0.00% | 0.67% -> 0.67% | 1.79% -> 1.79% | 98.20% -> 98.22% | 0.192 -> 0.194 |
| preset_creative | 15.00% -> 25.00% | 0.00% -> 5.00% | 0.00% -> 4.00% | 1.00% -> 0.00% | 0.67% -> 0.67% | 2.68% -> 2.50% | 97.31% -> 97.44% | 0.565 -> 0.522 |

| Additional metric (all settings) | Before | After |
|---|---:|---:|
| clean_octave_displacements | 4 | 0 |
| clean_octave_displacement_rate | 0.002380952380952381 | 0.0 |
| clean_timing_edits | 0 | 0 |
| clean_duration_edits | 0 | 0 |
| unnecessary_edit_count | 278 | 276 |
| made_worse_runs | 78 | 87 |
| total_runtime_seconds | 158.5068345999607 | 151.7704356997856 |
| Unnecessary pitch edits | 287 | 282 |
| Unnecessary onset_ticks edits | 0 | 0 |
| Unnecessary duration_ticks edits | 0 | 0 |

Coordinated-state counts (including locked controls):

```json
{
  "before": {
    "cases": 120,
    "all_generated": 0,
    "entered_search": 0,
    "scored": 0,
    "survived_beam": 0
  },
  "after": {
    "cases": 120,
    "all_generated": 0,
    "entered_search": 0,
    "scored": 0,
    "survived_beam": 0
  }
}
```

Failure migration (corrupted fields):

| Before | After | Count |
|---|---|---:|
| blocked_by_permissions_or_lock | blocked_by_permissions_or_lock | 180 |
| correct_candidate_generated_but_pruned | correct_candidate_never_generated | 4 |
| correct_candidate_never_generated | constraint_or_budget_rejection | 12 |
| correct_candidate_never_generated | correct_candidate_generated_but_pruned | 4 |
| correct_candidate_never_generated | correct_candidate_never_generated | 629 |
| correct_candidate_never_generated | recovered | 2 |
| correct_candidate_never_generated | required_combination_not_discovered | 23 |
| correct_candidate_never_generated | scoring_preferred_another_result | 14 |
| recovered | correct_candidate_never_generated | 6 |
| recovered | scoring_preferred_another_result | 1 |
| required_combination_not_discovered | required_combination_not_discovered | 9 |
| scoring_preferred_another_result | correct_candidate_never_generated | 14 |
| scoring_preferred_another_result | recovered | 2 |

Analysis attribution remains undetermined. Pruning is observed history, not proof of causation.
Ground-truth values and scoring-loss examples are diagnostic only, never repair inputs.

## maestro / evaluation

| Settings | Pitch recall | Timing recall | Duration recall | Exact notes | Partial fields | Clean FP | Untouched preservation | Mean seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| all | 19.58% -> 24.58% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.33% -> 0.00% | 1.00% -> 0.67% | 1.58% -> 1.75% | 98.34% -> 98.22% | 0.118 -> 0.197 |
| unlocked | 24.48% -> 30.73% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.42% -> 0.00% | 1.25% -> 0.83% | 1.97% -> 2.19% | 97.93% -> 97.77% | 0.146 -> 0.246 |
| preservation_0 | 25.00% -> 33.33% | 0.00% -> 0.00% | 0.00% -> 0.00% | 1.67% -> 0.00% | 3.33% -> 1.67% | 7.89% -> 8.77% | 91.72% -> 91.08% | 0.175 -> 0.314 |
| preservation_25 | 25.00% -> 33.33% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 1.67% -> 1.67% | 0.00% -> 0.00% | 100.00% -> 100.00% | 0.204 -> 0.319 |
| preservation_50 | 25.00% -> 31.25% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 100.00% -> 100.00% | 0.140 -> 0.237 |
| preservation_75 | 22.92% -> 25.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 100.00% -> 100.00% | 0.067 -> 0.114 |
| preservation_100 | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 100.00% -> 100.00% | 0.003 -> 0.003 |
| preset_minimal | 18.75% -> 17.50% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 1.00% -> 0.67% | 1.23% -> 1.05% | 98.80% -> 98.92% | 0.027 -> 0.039 |
| preset_balanced | 20.00% -> 26.25% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.50% -> 0.00% | 1.00% -> 0.67% | 1.58% -> 1.75% | 98.32% -> 98.22% | 0.088 -> 0.156 |
| preset_creative | 20.00% -> 30.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.50% -> 0.00% | 1.00% -> 0.67% | 1.93% -> 2.46% | 97.91% -> 97.51% | 0.238 -> 0.397 |

| Additional metric (all settings) | Before | After |
|---|---:|---:|
| clean_octave_displacements | 20 | 0 |
| clean_octave_displacement_rate | 0.011695906432748537 | 0.0 |
| clean_timing_edits | 0 | 0 |
| clean_duration_edits | 0 | 2 |
| unnecessary_edit_count | 272 | 294 |
| made_worse_runs | 119 | 116 |
| total_runtime_seconds | 70.66394590014534 | 118.44909469934646 |
| Unnecessary pitch edits | 272 | 285 |
| Unnecessary onset_ticks edits | 0 | 0 |
| Unnecessary duration_ticks edits | 0 | 20 |

Coordinated-state counts (including locked controls):

```json
{
  "before": {
    "cases": 120,
    "all_generated": 0,
    "entered_search": 0,
    "scored": 0,
    "survived_beam": 0
  },
  "after": {
    "cases": 120,
    "all_generated": 0,
    "entered_search": 0,
    "scored": 0,
    "survived_beam": 0
  }
}
```

Failure migration (corrupted fields):

| Before | After | Count |
|---|---|---:|
| blocked_by_permissions_or_lock | blocked_by_permissions_or_lock | 180 |
| correct_candidate_never_generated | constraint_or_budget_rejection | 18 |
| correct_candidate_never_generated | correct_candidate_never_generated | 637 |
| correct_candidate_never_generated | scoring_preferred_another_result | 18 |
| recovered | correct_candidate_never_generated | 5 |
| recovered | recovered | 4 |
| required_combination_not_discovered | correct_candidate_never_generated | 6 |
| required_combination_not_discovered | required_combination_not_discovered | 14 |
| scoring_preferred_another_result | correct_candidate_never_generated | 13 |
| scoring_preferred_another_result | recovered | 2 |
| scoring_preferred_another_result | scoring_preferred_another_result | 3 |

Analysis attribution remains undetermined. Pruning is observed history, not proof of causation.
Ground-truth values and scoring-loss examples are diagnostic only, never repair inputs.
