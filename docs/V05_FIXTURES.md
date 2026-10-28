# V0.5 musical regression fixtures

Generate 21 deterministic MIDI files without altering `sample_data/`:

```powershell
python -m scripts.generate_v05_fixtures --output-dir .test-tmp\musical-fixtures
```

The generator reuses selected original V0.4 scenarios and adds focused
passage cases. Names sharing attack material intentionally test different
permissions/objectives on the same musical evidence.

| Fixture name(s), `.mid` omitted | Evidence / expected assertion |
|---|---|
| `pitch_only` | One F#5 → G5 correction; exact non-pitch event preservation |
| `chromatic_passing` | Short resolving chromatic motion is retained |
| `suspension` | Prepared F resolving to E is protected |
| `secondary_dominant` | C → D7 → G → C; dominant-resolution sequence evidence, no forced correction |
| `motif_accidental` | Four-note repetition with one F4 instead of E4; qualified note-6 correction |
| `rhythmic_collision_a/b` | Timing-only separation of three close-register attacks |
| `call_response_a/b` | Same phrase; delayed replies preserve note order and pitches |
| `timing_over_pitch_a/b` | Same phrase; timing wins when all edit types are permitted |
| `sustain_conflict_a/b` | B's C# sustain overlaps C then D; bounded duration reduction helps |
| `pitch_timing_a/b` | Sustained C and a competing E attack require pitch plus onset adjustments |
| `pitch_duration_a/b` | Sustained clash rewards coordinated pitch plus duration more than either alone |
| `intentional_syncopation` | Repeated 0.375-beat offsets are preserved, even with all permissions at 0% preservation |
| `budget_a/b` | Seven conflict locations; progressively broader preset repairs |
| `legato_gap` | One 0.125-beat gap in an otherwise legato line; only that duration extends |

Additional in-memory tests exercise inversion, neighbor/anticipation context,
phrase rests, parallel motion, ambiguous harmony, independent rhythmic motifs,
onset/duration technical collisions, PPQ/tempo invariance, an explicit multi-
step objective barrier, MIDI event preservation and forbidden edits.

Run GUI buttons, export/reload, source-preserving combined/bundle export,
intentional-material controls, screenshots and profiling with a fresh directory:

```powershell
python -m scripts.validate_v05 --output-dir .test-tmp\musical-smoke --profile
```

Artifacts include `validation.json`, per-case MIDI/JSON/PNG, a four-file bundle,
`search.prof` and `profile.txt`. Existing exported files are not silently
overwritten; choose a fresh directory for another run. Windows' offscreen Qt
plugin has no enumerated fonts in this environment, so the validator reads the
existing Segoe UI font for screenshot QA. It installs nothing and does not
change normal desktop fonts.

These are deterministic engineering fixtures, not evidence of producer
preference or a claim that a score of 100 means objectively perfect music.
