# V0.5.3 -> V0.5.4: actual recovery versus oracle

No pooled corpus score. Rates repeat passages across settings, not independent compositions.
Oracle = feasible no-collateral reference subsets. Availability is a relaxed upper bound,
not an exhaustive optimum over arbitrary collateral edits. Top-k ranks are per note/edit field.

## pop909 / calibration

| Group | Actual exact | Feasible oracle | Available upper bound | Clean FP | Untouched preservation | Mean seconds |
|---|---:|---:|---:|---:|---:|---:|
| all | 0.19% -> 0.19% | 16.85% -> 18.15% | 19.63% -> 19.63% | 1.68% -> 1.28% | 98.35% -> 98.64% | 0.401 -> 0.633 |
| unlocked | 0.23% -> 0.23% | 21.06% -> 22.69% | 24.54% -> 24.54% | 2.10% -> 1.60% | 97.93% -> 98.30% | 0.499 -> 0.789 |
| preservation_0 | 0.93% -> 0.93% | 21.30% -> 23.15% | 25.00% -> 25.00% | 6.85% -> 5.92% | 93.50% -> 93.91% | 0.665 -> 1.071 |
| preservation_25 | 0.00% -> 0.00% | 21.30% -> 23.15% | 25.00% -> 25.00% | 1.40% -> 0.47% | 98.37% -> 99.30% | 0.554 -> 0.885 |
| preservation_50 | 0.00% -> 0.00% | 21.30% -> 23.15% | 25.00% -> 25.00% | 0.16% -> 0.00% | 99.86% -> 100.00% | 0.454 -> 0.713 |
| preservation_75 | 0.00% -> 0.00% | 20.37% -> 21.30% | 23.15% -> 23.15% | 0.00% -> 0.00% | 100.00% -> 100.00% | 0.323 -> 0.486 |
| preservation_100 | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 100.00% -> 100.00% | 0.007 -> 0.008 |
| preset_minimal | 0.00% -> 0.00% | 8.89% -> 8.89% | 8.89% -> 8.89% | 0.56% -> 0.56% | 99.40% -> 99.40% | 0.092 -> 0.141 |
| preset_balanced | 0.00% -> 0.00% | 15.00% -> 16.67% | 21.11% -> 21.11% | 2.06% -> 1.40% | 98.03% -> 98.54% | 0.366 -> 0.564 |
| preset_creative | 0.56% -> 0.56% | 26.67% -> 28.89% | 28.89% -> 28.89% | 2.43% -> 1.87% | 97.60% -> 97.98% | 0.744 -> 1.193 |

### Candidate recall: all

| Edit type | Any rank | Top 1 | Top 3 | Top 5 |
|---|---:|---:|---:|---:|
| pitch | 57.00% -> 57.00% | 22.67% -> 22.67% | 51.67% -> 51.67% | 55.67% -> 55.67% |
| timing | 19.67% -> 19.67% | 15.67% -> 15.67% | 19.67% -> 19.67% | 19.67% -> 19.67% |
| duration | 20.00% -> 20.00% | 0.00% -> 0.00% | 1.67% -> 0.00% | 5.00% -> 5.00% |

### Candidate recall: unlocked

| Edit type | Any rank | Top 1 | Top 3 | Top 5 |
|---|---:|---:|---:|---:|
| pitch | 71.25% -> 71.25% | 28.33% -> 28.33% | 64.58% -> 64.58% | 69.58% -> 69.58% |
| timing | 24.58% -> 24.58% | 19.58% -> 19.58% | 24.58% -> 24.58% | 24.58% -> 24.58% |
| duration | 25.00% -> 25.00% | 0.00% -> 0.00% | 2.08% -> 0.00% | 6.25% -> 6.25% |

### Safety, octave, coordinated and failure diagnostics

```json
{
  "before": {
    "clean_octave_edits": 0,
    "clean_octave_rate": 0.0,
    "unnecessary_edits": {
      "pitch": 233,
      "onset_ticks": 192,
      "duration_ticks": 89
    },
    "octave": {
      "targets": 60,
      "generated": 12,
      "selected_reference_pitch": 0,
      "exact_notes": 0
    },
    "coordinated": {
      "cases": 120,
      "all_values_generated": 15,
      "entered_search": 8,
      "scored": 7,
      "survived": 0,
      "all_corrupted_notes_recovered": 0
    },
    "clean_cause_tags": {
      "harmony correction": 24,
      "search interaction (overlapping tag)": 12,
      "timing collision logic": 23,
      "duration logic": 9
    }
  },
  "after": {
    "clean_octave_edits": 0,
    "clean_octave_rate": 0.0,
    "unnecessary_edits": {
      "pitch": 230,
      "onset_ticks": 39,
      "duration_ticks": 155
    },
    "octave": {
      "targets": 60,
      "generated": 12,
      "selected_reference_pitch": 0,
      "exact_notes": 0
    },
    "coordinated": {
      "cases": 120,
      "all_values_generated": 15,
      "entered_search": 11,
      "scored": 10,
      "survived": 0,
      "all_corrupted_notes_recovered": 0
    },
    "clean_cause_tags": {
      "harmony correction": 24,
      "search interaction (overlapping tag)": 11,
      "timing collision logic": 4,
      "duration logic": 15
    }
  }
}
```

Failure migration:

| Before | After | Fields |
|---|---|---:|
| blocked_by_permissions_or_lock | blocked_by_permissions_or_lock | 168 |
| constraint_or_budget_rejection | constraint_or_budget_rejection | 44 |
| constraint_or_budget_rejection | correct_candidate_generated_but_pruned | 5 |
| constraint_or_budget_rejection | generated_not_entered_search | 8 |
| constraint_or_budget_rejection | scoring_preferred_another_result | 2 |
| correct_candidate_generated_but_pruned | constraint_or_budget_rejection | 1 |
| correct_candidate_generated_but_pruned | correct_candidate_generated_but_pruned | 25 |
| correct_candidate_generated_but_pruned | generated_not_entered_search | 2 |
| correct_candidate_generated_but_pruned | scoring_preferred_another_result | 8 |
| correct_candidate_never_generated | correct_candidate_never_generated | 394 |
| generated_not_entered_search | generated_not_entered_search | 1 |
| generated_not_entered_search | required_combination_not_discovered | 4 |
| generated_not_entered_search | scoring_preferred_another_result | 1 |
| recovered | recovered | 15 |
| recovered | required_combination_not_discovered | 4 |
| recovered | scoring_preferred_another_result | 5 |
| required_combination_not_discovered | constraint_or_budget_rejection | 1 |
| required_combination_not_discovered | correct_candidate_generated_but_pruned | 1 |
| required_combination_not_discovered | generated_not_entered_search | 8 |
| required_combination_not_discovered | recovered | 1 |
| required_combination_not_discovered | required_combination_not_discovered | 69 |
| required_combination_not_discovered | scoring_preferred_another_result | 7 |
| scoring_preferred_another_result | constraint_or_budget_rejection | 1 |
| scoring_preferred_another_result | correct_candidate_generated_but_pruned | 5 |
| scoring_preferred_another_result | generated_not_entered_search | 3 |
| scoring_preferred_another_result | recovered | 2 |
| scoring_preferred_another_result | required_combination_not_discovered | 5 |
| scoring_preferred_another_result | scoring_preferred_another_result | 50 |

Analysis attribution is undetermined; clean-cause tags are hypotheses.
Per-case side-by-side raw and weighted scores and counterfactual explanations are in oracle.json.

## pop909 / evaluation

| Group | Actual exact | Feasible oracle | Available upper bound | Clean FP | Untouched preservation | Mean seconds |
|---|---:|---:|---:|---:|---:|---:|
| all | 0.00% -> 0.19% | 12.59% -> 12.41% | 13.70% -> 13.52% | 1.90% -> 1.68% | 98.04% -> 98.33% | 0.355 -> 0.487 |
| unlocked | 0.00% -> 0.23% | 15.74% -> 15.51% | 17.13% -> 16.90% | 2.38% -> 2.10% | 97.56% -> 97.92% | 0.442 -> 0.607 |
| preservation_0 | 0.00% -> 0.93% | 15.74% -> 15.74% | 17.59% -> 17.59% | 7.43% -> 7.05% | 92.35% -> 92.94% | 0.597 -> 0.832 |
| preservation_25 | 0.00% -> 0.00% | 15.74% -> 15.74% | 17.59% -> 17.59% | 2.10% -> 1.33% | 97.87% -> 98.73% | 0.492 -> 0.682 |
| preservation_50 | 0.00% -> 0.00% | 15.74% -> 15.74% | 16.67% -> 16.67% | 0.00% -> 0.00% | 100.00% -> 100.00% | 0.398 -> 0.537 |
| preservation_75 | 0.00% -> 0.00% | 15.74% -> 14.81% | 16.67% -> 15.74% | 0.00% -> 0.00% | 100.00% -> 100.00% | 0.282 -> 0.376 |
| preservation_100 | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 100.00% -> 100.00% | 0.006 -> 0.007 |
| preset_minimal | 0.00% -> 0.00% | 6.67% -> 6.11% | 6.67% -> 6.11% | 0.80% -> 0.80% | 99.24% -> 99.27% | 0.091 -> 0.127 |
| preset_balanced | 0.00% -> 0.00% | 13.33% -> 13.33% | 14.44% -> 14.44% | 2.17% -> 1.83% | 97.80% -> 98.11% | 0.340 -> 0.452 |
| preset_creative | 0.00% -> 0.56% | 17.78% -> 17.78% | 20.00% -> 20.00% | 2.74% -> 2.40% | 97.10% -> 97.62% | 0.633 -> 0.881 |

### Candidate recall: all

| Edit type | Any rank | Top 1 | Top 3 | Top 5 |
|---|---:|---:|---:|---:|
| pitch | 40.67% -> 40.00% | 23.33% -> 23.33% | 30.33% -> 30.00% | 36.67% -> 36.00% |
| timing | 21.00% -> 21.00% | 18.33% -> 15.67% | 21.00% -> 19.67% | 21.00% -> 19.67% |
| duration | 8.33% -> 8.33% | 0.00% -> 0.00% | 1.67% -> 1.67% | 3.33% -> 3.33% |

### Candidate recall: unlocked

| Edit type | Any rank | Top 1 | Top 3 | Top 5 |
|---|---:|---:|---:|---:|
| pitch | 50.83% -> 50.00% | 29.17% -> 29.17% | 37.92% -> 37.50% | 45.83% -> 45.00% |
| timing | 26.25% -> 26.25% | 22.92% -> 19.58% | 26.25% -> 24.58% | 26.25% -> 24.58% |
| duration | 10.42% -> 10.42% | 0.00% -> 0.00% | 2.08% -> 2.08% | 4.17% -> 4.17% |

### Safety, octave, coordinated and failure diagnostics

```json
{
  "before": {
    "clean_octave_edits": 0,
    "clean_octave_rate": 0.0,
    "unnecessary_edits": {
      "pitch": 279,
      "duration_ticks": 65,
      "onset_ticks": 162
    },
    "octave": {
      "targets": 60,
      "generated": 0,
      "selected_reference_pitch": 0,
      "exact_notes": 0
    },
    "coordinated": {
      "cases": 120,
      "all_values_generated": 6,
      "entered_search": 2,
      "scored": 0,
      "survived": 0,
      "all_corrupted_notes_recovered": 0
    },
    "clean_cause_tags": {
      "harmony correction": 22,
      "register/voice correction": 8,
      "search interaction (overlapping tag)": 11,
      "duration logic": 8,
      "timing collision logic": 18
    }
  },
  "after": {
    "clean_octave_edits": 0,
    "clean_octave_rate": 0.0,
    "unnecessary_edits": {
      "pitch": 301,
      "duration_ticks": 113,
      "onset_ticks": 51
    },
    "octave": {
      "targets": 60,
      "generated": 0,
      "selected_reference_pitch": 0,
      "exact_notes": 0
    },
    "coordinated": {
      "cases": 120,
      "all_values_generated": 6,
      "entered_search": 4,
      "scored": 0,
      "survived": 0,
      "all_corrupted_notes_recovered": 0
    },
    "clean_cause_tags": {
      "harmony correction": 29,
      "register/voice correction": 6,
      "search interaction (overlapping tag)": 11,
      "duration logic": 13,
      "timing collision logic": 5
    }
  }
}
```

Failure migration:

| Before | After | Fields |
|---|---|---:|
| blocked_by_permissions_or_lock | blocked_by_permissions_or_lock | 168 |
| constraint_or_budget_rejection | constraint_or_budget_rejection | 26 |
| constraint_or_budget_rejection | generated_not_entered_search | 1 |
| correct_candidate_generated_but_pruned | correct_candidate_generated_but_pruned | 9 |
| correct_candidate_generated_but_pruned | scoring_preferred_another_result | 6 |
| correct_candidate_never_generated | correct_candidate_never_generated | 467 |
| generated_not_entered_search | generated_not_entered_search | 5 |
| generated_not_entered_search | required_combination_not_discovered | 2 |
| generated_not_entered_search | scoring_preferred_another_result | 2 |
| recovered | recovered | 11 |
| recovered | scoring_preferred_another_result | 1 |
| required_combination_not_discovered | correct_candidate_never_generated | 1 |
| required_combination_not_discovered | generated_not_entered_search | 8 |
| required_combination_not_discovered | recovered | 2 |
| required_combination_not_discovered | required_combination_not_discovered | 56 |
| required_combination_not_discovered | scoring_preferred_another_result | 1 |
| scoring_preferred_another_result | correct_candidate_generated_but_pruned | 2 |
| scoring_preferred_another_result | correct_candidate_never_generated | 1 |
| scoring_preferred_another_result | generated_not_entered_search | 7 |
| scoring_preferred_another_result | recovered | 5 |
| scoring_preferred_another_result | scoring_preferred_another_result | 59 |

Analysis attribution is undetermined; clean-cause tags are hypotheses.
Per-case side-by-side raw and weighted scores and counterfactual explanations are in oracle.json.

## maestro / calibration

| Group | Actual exact | Feasible oracle | Available upper bound | Clean FP | Untouched preservation | Mean seconds |
|---|---:|---:|---:|---:|---:|---:|
| all | 0.00% -> 2.00% | 2.50% -> 7.00% | 2.50% -> 7.00% | 1.67% -> 1.67% | 98.29% -> 98.38% | 0.253 -> 0.329 |
| unlocked | 0.00% -> 2.50% | 3.12% -> 8.75% | 3.12% -> 8.75% | 2.08% -> 2.08% | 97.87% -> 97.98% | 0.315 -> 0.410 |
| preservation_0 | 0.00% -> 5.00% | 4.17% -> 10.83% | 4.17% -> 10.83% | 8.33% -> 8.33% | 91.46% -> 91.94% | 0.430 -> 0.580 |
| preservation_25 | 0.00% -> 5.00% | 3.33% -> 9.17% | 3.33% -> 9.17% | 0.00% -> 0.00% | 100.00% -> 99.97% | 0.428 -> 0.531 |
| preservation_50 | 0.00% -> 0.00% | 2.50% -> 7.50% | 2.50% -> 7.50% | 0.00% -> 0.00% | 100.00% -> 100.00% | 0.294 -> 0.377 |
| preservation_75 | 0.00% -> 0.00% | 2.50% -> 7.50% | 2.50% -> 7.50% | 0.00% -> 0.00% | 100.00% -> 100.00% | 0.109 -> 0.153 |
| preservation_100 | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 100.00% -> 100.00% | 0.004 -> 0.004 |
| preset_minimal | 0.00% -> 2.00% | 2.00% -> 6.00% | 2.00% -> 6.00% | 0.71% -> 0.71% | 99.21% -> 99.28% | 0.043 -> 0.044 |
| preset_balanced | 0.00% -> 2.00% | 2.50% -> 7.00% | 2.50% -> 7.00% | 1.79% -> 1.79% | 98.22% -> 98.35% | 0.194 -> 0.261 |
| preset_creative | 0.00% -> 2.00% | 3.00% -> 8.00% | 3.00% -> 8.00% | 2.50% -> 2.50% | 97.44% -> 97.52% | 0.522 -> 0.682 |

### Candidate recall: all

| Edit type | Any rank | Top 1 | Top 3 | Top 5 |
|---|---:|---:|---:|---:|
| pitch | 21.67% -> 30.83% | 19.17% -> 28.33% | 21.67% -> 30.83% | 21.67% -> 30.83% |
| timing | 3.06% -> 5.00% | 0.00% -> 0.00% | 2.22% -> 3.06% | 3.06% -> 5.00% |
| duration | 1.33% -> 1.33% | 0.00% -> 0.00% | 1.33% -> 1.33% | 1.33% -> 1.33% |

### Candidate recall: unlocked

| Edit type | Any rank | Top 1 | Top 3 | Top 5 |
|---|---:|---:|---:|---:|
| pitch | 27.08% -> 38.54% | 23.96% -> 35.42% | 27.08% -> 38.54% | 27.08% -> 38.54% |
| timing | 3.82% -> 6.25% | 0.00% -> 0.00% | 2.78% -> 3.82% | 3.82% -> 6.25% |
| duration | 1.67% -> 1.67% | 0.00% -> 0.00% | 1.67% -> 1.67% | 1.67% -> 1.67% |

### Safety, octave, coordinated and failure diagnostics

```json
{
  "before": {
    "clean_octave_edits": 0,
    "clean_octave_rate": 0.0,
    "unnecessary_edits": {
      "pitch": 282
    },
    "octave": {
      "targets": 60,
      "generated": 0,
      "selected_reference_pitch": 0,
      "exact_notes": 0
    },
    "coordinated": {
      "cases": 120,
      "all_values_generated": 0,
      "entered_search": 0,
      "scored": 0,
      "survived": 0,
      "all_corrupted_notes_recovered": 0
    },
    "clean_cause_tags": {
      "harmony correction": 20,
      "search interaction (overlapping tag)": 8,
      "register/voice correction": 3,
      "motif correction": 5
    }
  },
  "after": {
    "clean_octave_edits": 0,
    "clean_octave_rate": 0.0,
    "unnecessary_edits": {
      "pitch": 256,
      "onset_ticks": 14
    },
    "octave": {
      "targets": 60,
      "generated": 24,
      "selected_reference_pitch": 12,
      "exact_notes": 12
    },
    "coordinated": {
      "cases": 120,
      "all_values_generated": 0,
      "entered_search": 0,
      "scored": 0,
      "survived": 0,
      "all_corrupted_notes_recovered": 0
    },
    "clean_cause_tags": {
      "harmony correction": 17,
      "search interaction (overlapping tag)": 8,
      "timing collision logic": 2,
      "register/voice correction": 3,
      "motif correction": 6
    }
  }
}
```

Failure migration:

| Before | After | Fields |
|---|---|---:|
| blocked_by_permissions_or_lock | blocked_by_permissions_or_lock | 180 |
| constraint_or_budget_rejection | constraint_or_budget_rejection | 9 |
| constraint_or_budget_rejection | correct_candidate_never_generated | 1 |
| constraint_or_budget_rejection | required_combination_not_discovered | 1 |
| constraint_or_budget_rejection | scoring_preferred_another_result | 1 |
| correct_candidate_generated_but_pruned | scoring_preferred_another_result | 4 |
| correct_candidate_never_generated | correct_candidate_never_generated | 622 |
| correct_candidate_never_generated | recovered | 13 |
| correct_candidate_never_generated | required_combination_not_discovered | 2 |
| correct_candidate_never_generated | scoring_preferred_another_result | 16 |
| recovered | recovered | 2 |
| recovered | scoring_preferred_another_result | 2 |
| required_combination_not_discovered | correct_candidate_never_generated | 1 |
| required_combination_not_discovered | required_combination_not_discovered | 30 |
| required_combination_not_discovered | scoring_preferred_another_result | 1 |
| scoring_preferred_another_result | scoring_preferred_another_result | 15 |

Analysis attribution is undetermined; clean-cause tags are hypotheses.
Per-case side-by-side raw and weighted scores and counterfactual explanations are in oracle.json.

## maestro / evaluation

| Group | Actual exact | Feasible oracle | Available upper bound | Clean FP | Untouched preservation | Mean seconds |
|---|---:|---:|---:|---:|---:|---:|
| all | 0.00% -> 0.00% | 3.00% -> 2.83% | 3.00% -> 2.83% | 1.75% -> 1.70% | 98.22% -> 98.27% | 0.197 -> 0.271 |
| unlocked | 0.00% -> 0.00% | 3.75% -> 3.54% | 3.75% -> 3.54% | 2.19% -> 2.12% | 97.77% -> 97.84% | 0.246 -> 0.338 |
| preservation_0 | 0.00% -> 0.00% | 4.17% -> 4.17% | 4.17% -> 4.17% | 8.77% -> 8.48% | 91.08% -> 91.55% | 0.314 -> 0.447 |
| preservation_25 | 0.00% -> 0.00% | 4.17% -> 4.17% | 4.17% -> 4.17% | 0.00% -> 0.00% | 100.00% -> 99.80% | 0.319 -> 0.430 |
| preservation_50 | 0.00% -> 0.00% | 3.33% -> 3.33% | 3.33% -> 3.33% | 0.00% -> 0.00% | 100.00% -> 100.00% | 0.237 -> 0.325 |
| preservation_75 | 0.00% -> 0.00% | 3.33% -> 2.50% | 3.33% -> 2.50% | 0.00% -> 0.00% | 100.00% -> 100.00% | 0.114 -> 0.148 |
| preservation_100 | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 100.00% -> 100.00% | 0.003 -> 0.004 |
| preset_minimal | 0.00% -> 0.00% | 2.00% -> 2.00% | 2.00% -> 2.00% | 1.05% -> 1.05% | 98.92% -> 98.97% | 0.039 -> 0.043 |
| preset_balanced | 0.00% -> 0.00% | 3.00% -> 3.00% | 3.00% -> 3.00% | 1.75% -> 1.75% | 98.22% -> 98.19% | 0.156 -> 0.208 |
| preset_creative | 0.00% -> 0.00% | 4.00% -> 3.50% | 4.00% -> 3.50% | 2.46% -> 2.28% | 97.51% -> 97.65% | 0.397 -> 0.561 |

### Candidate recall: all

| Edit type | Any rank | Top 1 | Top 3 | Top 5 |
|---|---:|---:|---:|---:|
| pitch | 24.58% -> 23.33% | 9.58% -> 9.17% | 20.00% -> 19.17% | 21.25% -> 20.00% |
| timing | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% |
| duration | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% |

### Candidate recall: unlocked

| Edit type | Any rank | Top 1 | Top 3 | Top 5 |
|---|---:|---:|---:|---:|
| pitch | 30.73% -> 29.17% | 11.98% -> 11.46% | 25.00% -> 23.96% | 26.56% -> 25.00% |
| timing | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% |
| duration | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% | 0.00% -> 0.00% |

### Safety, octave, coordinated and failure diagnostics

```json
{
  "before": {
    "clean_octave_edits": 0,
    "clean_octave_rate": 0.0,
    "unnecessary_edits": {
      "pitch": 285,
      "duration_ticks": 20
    },
    "octave": {
      "targets": 60,
      "generated": 0,
      "selected_reference_pitch": 0,
      "exact_notes": 0
    },
    "coordinated": {
      "cases": 120,
      "all_values_generated": 0,
      "entered_search": 0,
      "scored": 0,
      "survived": 0,
      "all_corrupted_notes_recovered": 0
    },
    "clean_cause_tags": {
      "harmony correction": 23,
      "search interaction (overlapping tag)": 8,
      "motif correction": 2,
      "duration logic": 2,
      "register/voice correction": 4
    }
  },
  "after": {
    "clean_octave_edits": 0,
    "clean_octave_rate": 0.0,
    "unnecessary_edits": {
      "pitch": 277,
      "onset_ticks": 9,
      "duration_ticks": 8
    },
    "octave": {
      "targets": 60,
      "generated": 0,
      "selected_reference_pitch": 0,
      "exact_notes": 0
    },
    "coordinated": {
      "cases": 120,
      "all_values_generated": 0,
      "entered_search": 0,
      "scored": 0,
      "survived": 0,
      "all_corrupted_notes_recovered": 0
    },
    "clean_cause_tags": {
      "harmony correction": 21,
      "motif correction": 3,
      "search interaction (overlapping tag)": 8,
      "timing collision logic": 1,
      "duration logic": 1,
      "register/voice correction": 3
    }
  }
}
```

Failure migration:

| Before | After | Fields |
|---|---|---:|
| blocked_by_permissions_or_lock | blocked_by_permissions_or_lock | 180 |
| constraint_or_budget_rejection | constraint_or_budget_rejection | 17 |
| constraint_or_budget_rejection | correct_candidate_never_generated | 1 |
| correct_candidate_never_generated | correct_candidate_never_generated | 661 |
| recovered | recovered | 6 |
| required_combination_not_discovered | correct_candidate_never_generated | 1 |
| required_combination_not_discovered | required_combination_not_discovered | 13 |
| scoring_preferred_another_result | correct_candidate_never_generated | 1 |
| scoring_preferred_another_result | scoring_preferred_another_result | 20 |

Analysis attribution is undetermined; clean-cause tags are hypotheses.
Per-case side-by-side raw and weighted scores and counterfactual explanations are in oracle.json.
