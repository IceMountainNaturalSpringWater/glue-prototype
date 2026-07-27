# Deterministic MIDI fixtures

Generate the copyright-free V0.1 fixture catalog into an explicit directory:

```powershell
python scripts\generate_fixtures.py --output-dir .generated-fixtures
```

The script never writes to `sample_data/` implicitly. It includes compatible
major/minor pairs, local harmonic conflict, register and rhythm comparisons,
an out-of-key repair target, octave equivalence, and a metadata round-trip file.
