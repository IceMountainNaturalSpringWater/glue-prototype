# GLUE Prototype

GLUE is a preservation-first MIDI compatibility tool. It compares two Standard
MIDI Files, explains where they may compete, and proposes a small pitch-only
repair while retaining the user's timing and source metadata.

V0.1 is a standalone desktop prototype. It has no cloud services, accounts,
telemetry, AI calls, or network features.

## What works

- Load two type-0 or type-1 Standard MIDI Files.
- Parse notes, tracks/channels, tempo changes, and time signatures.
- Estimate duration-weighted major/minor keys with ambiguity confidence.
- Score harmonic, bass/root, register, and attack-rhythm compatibility in beat
  windows using centralized 50/20/15/15 weights.
- Inspect an overlay piano roll, compatibility timeline, and qualified conflict
  reasons.
- Lock A or B and generate one deterministic Minimal repair candidate for the
  other clip.
- Inspect every pitch edit, its before/after score, and changed-note count.
- Export a valid MIDI file while preserving the source event stream and timing.

Scores are transparent heuristics, not objective musical diagnoses. Register
and rhythm warnings describe possible arrangement competition, not errors.

## Windows and VS Code setup

Requirements:

- Windows 10 or 11
- 64-bit Python 3.11 or newer from [python.org](https://www.python.org/downloads/)
- VS Code with the Microsoft Python extension (optional)

Open this repository as the VS Code folder, then run these commands in a
PowerShell terminal:

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
python -m glue
```

In VS Code, use **Python: Select Interpreter** from the Command Palette and
choose `.venv\Scripts\python.exe`. If `python` is not on `PATH`, use the Python
launcher for the first command, for example `py -3.11 -m venv .venv`.

The included setup script performs the environment, install, and test steps:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\start_windows.ps1
.\.venv\Scripts\python.exe -m glue
```

## Generate safe test MIDI

The fixture generator writes only to the directory explicitly supplied:

```powershell
python scripts\generate_fixtures.py --output-dir .generated-fixtures
```

For a quick demonstration, load
`.generated-fixtures\out_of_key_context.mid` as A and
`.generated-fixtures\out_of_key_melody.mid` as B, keep A locked, and select
**Generate Minimal repair**.

## Automated workflow smoke test

This command creates and shows the real window on Qt's offscreen platform,
loads both files, analyzes them, generates a Minimal repair, exports it, and
exits:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
$env:QT_OPENGL = "software"
python -m glue --smoke-test `
  --file-a .generated-fixtures\out_of_key_context.mid `
  --file-b .generated-fixtures\out_of_key_melody.mid `
  --export .generated-fixtures\minimal-repaired.mid
Remove-Item Env:QT_QPA_PLATFORM, Env:QT_OPENGL
```

## Architecture

```text
src/glue/models/    immutable MIDI domain models
src/glue/io/        Standard MIDI File parsing and preservation-first export
src/glue/analysis/  key estimation, component scoring, and window aggregation
src/glue/fixes/     deterministic Minimal repair optimization
src/glue/ui/        PySide6 desktop workflow and native visualizations
scripts/            deterministic, copyright-free MIDI fixture generation
tests/              unit, integration, GUI-launch, and end-to-end coverage
```

The analysis and repair layers do not import the GUI. Raw files in
`sample_data/` are never changed.

## V0.1 limitations

- MIDI only; no WAV/audio, live MIDI ports, DAW control, or plugin formats.
- One global major/natural-minor estimate; no modulation, harmonic-minor, or
  melodic-minor inference.
- Beat-zero alignment only; no loop-offset detection or automatic quantization.
- Sustain-pedal semantics are preserved on export but not modeled in analysis.
- Minimal mode changes pitch only. Balanced and Creative modes are deferred.
