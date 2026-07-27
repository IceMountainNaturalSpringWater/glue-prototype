# Codex instructions for GLUE

## Mission
Build GLUE as a testable MIDI-analysis application. Prioritize correctness, interpretability, and minimal edits over flashy generative features.

## Working rules
- Read `docs/PRODUCT_SPEC.md` before making architectural decisions.
- Keep music-analysis logic independent from the GUI.
- Add or update tests for every analysis/fix module.
- Run the relevant tests after each meaningful change and the full suite before declaring a task complete.
- Never silently change raw files in `sample_data/`.
- Do not add cloud APIs, LLM calls, telemetry, accounts, or network dependencies.
- Do not install new dependencies unless they are clearly necessary; prefer the dependencies already declared in `pyproject.toml`.
- Keep functions small and typed.
- Prefer deterministic algorithms for the prototype.
- Document assumptions in code when music theory is ambiguous.
- Do not claim a musical diagnosis is objectively correct. Return scores/reasons and allow ambiguity.

## Definition of done for V0.1
A user can run `python -m glue`, load two MIDI files, see a compatibility score and timeline diagnosis, lock one clip, generate at least one minimal repair candidate for the other, audition/inspect the result, and export it as MIDI. `pytest` passes.
