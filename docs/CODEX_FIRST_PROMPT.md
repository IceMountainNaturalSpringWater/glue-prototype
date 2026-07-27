# First prompt to paste into Codex

Read `AGENTS.md`, `README.md`, and `docs/PRODUCT_SPEC.md` completely before editing anything.

Your task is to build the first working GLUE prototype in this repository.

Work autonomously inside this repository. You may create/edit files, run Python commands, run tests, and iteratively debug failures. Do not access or modify files outside this repository. Do not add cloud services, LLM/API calls, analytics, accounts, or network-dependent features. Do not install additional dependencies unless the existing declared stack is genuinely insufficient; explain why before doing so.

## Required V0.1 behavior
1. `python -m glue` launches a desktop GUI.
2. The GUI can load two Standard MIDI Files.
3. The parser extracts note pitch, onset, duration, velocity, track/channel, tempo, and time signature where available.
4. Implement deterministic duration-weighted major/minor key estimation and show the top estimate plus confidence.
5. Analyze the pair in musical-time windows and calculate:
   - harmonic compatibility
   - bass/root compatibility
   - register overlap compatibility
   - rhythm/attack compatibility
   - overall weighted compatibility from 0-100
6. Display the component scores, an overall score, a basic overlay piano roll, and a per-window compatibility heatmap/timeline.
7. Allow the user to lock MIDI A or B.
8. Implement a functional Minimal repair mode for the unlocked clip. It must preserve note onset and duration and search for a small number of nearby pitch changes and/or octave moves that improve the compatibility score while penalizing edits.
9. Show the original score, repaired score, and changed-note count.
10. Export the repaired clip as a valid MIDI file while preserving timing as faithfully as practical.
11. Add synthetic MIDI-fixture generation under `scripts/` so the program can be tested without copyrighted music files.
12. Add meaningful pytest coverage for parsing, key estimation, compatibility components, and repair behavior.
13. Ensure `pytest` passes and perform one end-to-end smoke test using generated fixture MIDI files.
14. Update README with exact Windows/VS Code setup and run instructions.

## Architecture requirements
- Put domain models in `src/glue/models/`.
- MIDI reading/writing in `src/glue/io/`.
- Music analysis algorithms in `src/glue/analysis/`.
- Repair/optimization algorithms in `src/glue/fixes/`.
- PySide6 UI in `src/glue/ui/`.
- GUI must call the analysis API; do not embed theory/math logic directly in widgets.
- Use Python type hints and docstrings for public functions.
- Keep scoring weights centralized/configurable.

## Important engineering behavior
Do not start by polishing the GUI. Build and test in this order:
A. domain models + MIDI parser/writer
B. synthetic fixture generator
C. key estimation
D. compatibility component scoring
E. combined pair analysis
F. Minimal repair optimizer
G. GUI
H. end-to-end test and cleanup

After each stage, run the relevant tests and fix failures before advancing. If a design choice is musically ambiguous, implement a reasonable transparent heuristic and document it rather than inventing certainty.

When complete, give me:
- exact commands to set up/run the project
- tests executed and their results
- architecture summary
- known limitations
- the next 5 highest-value improvements
- a concise list of every file you created or materially changed
