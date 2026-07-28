# GLUE V0.2 Prototype

GLUE is a preservation-first MIDI compatibility tool. It compares two Standard
MIDI Files, explains where their harmony, bass, register, or attacks may
compete, and proposes deterministic pitch-only repairs without changing the
loaded source files.

V0.2 is a standalone desktop prototype. It has no cloud services, accounts,
telemetry, AI calls, or network features.

## What works

- Load type-0 and type-1 Standard MIDI Files while preserving their source
  event streams for export.
- Estimate duration-weighted major/minor keys and expose ambiguity confidence.
- Analyze true simultaneous activity in one-beat windows, including local
  diatonic triad/seventh interpretations even when both clips share a global
  key.
- Score harmonic, bass/root, register, and attack-rhythm compatibility with
  centralized, testable weights.
- Explain conflicts with beat ranges, clip ownership, pitch classes, candidate
  chord names, and strong semitone/tritone relationships.
- Lock MIDI A or B and generate Minimal, Balanced, or Creative repairs. All
  presets keep rhythm, velocity, note identity, tracks, channels, and metadata
  unchanged.
- Adjust preservation from 0 to 100; higher values increase the edit penalty.
- Retain and select generated candidates, compare before/after notes in the
  piano roll, and compare aligned before/after timeline rows.
- Export the selected result as valid MIDI. GLUE refuses to overwrite either
  loaded source file.
- Report malformed, truncated, empty, and incomplete-note MIDI clearly while
  surfacing nonfatal parser warnings.

Scores and chord labels are transparent heuristics, not objective musical
diagnoses. The UI reports uncertainty or unresolved harmony where evidence is
insufficient.

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
python -m ruff check .
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

## Desktop workflow

1. Load MIDI A and MIDI B, then choose which clip to lock.
2. Select **Analyze compatibility** and inspect the component scores, timeline,
   and qualified reasons.
3. Choose Minimal, Balanced, or Creative and set the preservation slider.
4. Generate one or more candidates. Selecting a candidate restores its exact
   preset, score comparison, note ghosts/highlights, and edit list.
5. Export to a new `.mid` or `.midi` path.

Minimal searches nearby pitches and uses octave moves only for register
conflicts. Balanced searches a wider neighborhood and always considers octave
moves. Creative searches still wider and adds pitches implied by the locked
clip's local harmony. Every mode is deterministic and pitch-only.

## Generate the safe demo catalog

The fixture generator writes only to the directory explicitly supplied; it
never changes `sample_data/`:

```powershell
python scripts\generate_fixtures.py --output-dir .generated-fixtures
```

The V0.2 demonstrations are:

| Purpose | MIDI A | MIDI B |
|---|---|---|
| Same-key compatible control | `demo_same_key_a.mid` | `demo_same_key_clean_b.mid` |
| Same-key local conflict | `demo_same_key_a.mid` | `demo_same_key_conflict_b.mid` |
| Progressive 1/2/3-edit presets | `demo_preset_context.mid` | `demo_preset_source.mid` |

For the preset demo, lock A and generate all three modes at preservation 50.
Minimal, Balanced, and Creative produce one, two, and three edits respectively
with the current calibrated heuristics.

## Automated GUI smoke test

This command constructs and paints the real Qt window on the offscreen
platform, loads both files, analyzes them, generates the backward-compatible
Minimal candidate, exports it, and exits:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
$env:QT_OPENGL = "software"
python -m glue --smoke-test `
  --file-a .generated-fixtures\demo_preset_context.mid `
  --file-b .generated-fixtures\demo_preset_source.mid `
  --export .generated-fixtures\minimal-repaired.mid
Remove-Item Env:QT_QPA_PLATFORM, Env:QT_OPENGL
```

## Architecture

```text
src/glue/models/    immutable MIDI domain models
src/glue/io/        permissive parsing, analysis validation, safe template export
src/glue/analysis/  key/local-harmony inference, component scoring, explanations
src/glue/fixes/     deterministic preset repair search and preservation penalties
src/glue/ui/        PySide6 workflow and native before/after visualizations
scripts/            deterministic, copyright-free MIDI fixture generation
tests/              unit, regression, integration, GUI, and end-to-end coverage
```

The analysis and repair layers do not import the GUI. Raw files in
`sample_data/` are never changed.

## Known limitations

- MIDI only: no audio audition, WAV analysis, live MIDI ports, DAW control, or
  VST/AU plugin formats.
- Key estimation models one global major or natural-minor center; it does not
  detect modulation or distinguish harmonic/melodic minor.
- Local harmony is limited to diatonic triad and seventh candidates under the
  estimated key. Chromatic, modal, extended, and deliberately ambiguous music
  may be unresolved or misranked.
- Clips are compared at their existing beat-zero alignment; there is no loop
  offset detection, warping, or automatic quantization.
- All three repair modes use greedy pitch-only search. Creative does not alter
  rhythm, generate new notes, or guarantee a producer's preferred voicing.
- Sustain-pedal and other controller semantics are preserved on export but are
  not modeled in analysis.
- Compatibility thresholds and edit penalties are calibrated synthetic
  heuristics and still need validation with real producer material.
