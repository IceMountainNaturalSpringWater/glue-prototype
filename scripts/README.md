# Deterministic MIDI fixtures

Generate the copyright-free regression fixtures and additive V0.2/V0.3 demo
catalog into an explicit directory:

```powershell
python scripts\generate_fixtures.py --output-dir .generated-fixtures
```

The script never writes to `sample_data/` implicitly. Alongside the original
analysis, repair, and metadata fixtures, the catalog includes:

- `demo_same_key_a` + `demo_same_key_clean_b`: compatible C-major control.
- `demo_same_key_a` + `demo_same_key_conflict_b`: locally conflicting E-minor
  and B-diminished windows despite confident shared C major.
- `demo_preset_context` + `demo_preset_source`: calibrated Minimal, Balanced,
  and Creative results with one, two, and three pitch edits.
- `shared_better_a` + `shared_better_b`: one edit in each clip produces the
  dedicated Shared Compromise advantage.
- `preservation_bias_a` + `preservation_bias_b`: symmetric alternatives make
  independent preservation allocation observable.
- `both_locked_a` + `both_locked_b`: both-100% validation.
- `unison_collapse_a` + `unison_collapse_b`: verifies that raw consonance does
  not reward collapsing independent parallel lines into exact unison.
- `coordinated_same_side_a` + `coordinated_same_side_b`: two B-note edits
  improve the complete pair even though neither isolated pitch edit does.
- `dual_export_a` + `dual_export_b`: both clips change and every V0.3 export
  artifact can be reopened.

`DEMO_SCENARIOS` in `generate_fixtures.py` exposes these pairings to tools and
tests without writing any files.
