# GLUE Prototype

GLUE is a preservation-first MIDI compatibility tool. It compares two MIDI ideas, explains where they clash, and suggests minimal edits that make them work together while preserving the user's original material.

## Prototype scope

The first working prototype is intentionally MIDI-only and standalone. It should:

1. Load two MIDI files (A and B).
2. Parse notes with pitch, onset, duration, velocity, track, and channel.
3. Estimate a global key/mode for each clip and a combined key/mode.
4. Divide the timeline into beat/bar windows.
5. Compute per-window compatibility metrics:
   - pitch-class / scale compatibility
   - local harmonic compatibility
   - bass/root conflict
   - register overlap
   - rhythmic density/attack overlap
6. Produce an overall 0-100 compatibility score and a per-window heatmap.
7. Let the user lock A or B.
8. Generate three MIDI repair candidates for the unlocked clip:
   - Minimal
   - Balanced
   - Creative
9. Export the repaired MIDI.
10. Show a simple piano-roll visualization and textual diagnosis.

## Non-goals for V0.1

- No audio/WAV analysis.
- No AI/LLM generation inside the product.
- No VST/AU plugin yet.
- No DAW automation or screen control.
- No accounts, cloud backend, or payments.
- No attempt to replace Scaler or generate entire songs.

## Recommended stack

- Python 3.11+
- PySide6 for desktop UI
- mido + python-rtmidi for MIDI I/O/parsing
- numpy for numerical work
- matplotlib for prototype visualization
- pytest for tests

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .[dev]
pytest
python -m glue
```

## Product principle

> Keep your ideas. Make them work together.

The algorithm should prefer the smallest musical change that creates a meaningful compatibility improvement.
