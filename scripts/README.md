# Deterministic MIDI fixtures

Generate the copyright-free V0.1 regression fixtures and additive V0.2 demo
catalog into an explicit directory:

```powershell
python scripts\generate_fixtures.py --output-dir .generated-fixtures
```

The script never writes to `sample_data/` implicitly. Alongside the original
analysis, repair, and metadata fixtures, V0.2 includes three discoverable demos:

- `demo_same_key_a` + `demo_same_key_clean_b`: compatible C-major control.
- `demo_same_key_a` + `demo_same_key_conflict_b`: locally conflicting E-minor
  and B-diminished windows despite confident shared C major.
- `demo_preset_context` + `demo_preset_source`: calibrated Minimal, Balanced,
  and Creative results with one, two, and three pitch edits.

`DEMO_SCENARIOS` in `generate_fixtures.py` exposes these pairings to tools and
tests without writing any files.
