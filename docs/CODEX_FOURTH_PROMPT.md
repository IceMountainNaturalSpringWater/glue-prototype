Implement GLUE V0.4.0: **Single MIDI Repair**.

Keep the existing two-file workflow as **Combine Two Clips** and add a separate **Polish One Clip** workflow.

Do not add audio, live MIDI, DAW/plugin integration, cloud services, accounts, telemetry, or LLM APIs.

## Preparation

* Read `AGENTS.md`, README, current analysis/repair/MIDI/UI code, and tests.
* Run the current test suite, Ruff, smoke test, and `git diff --check`.
* Work on `feature/v0.4`.
* Do not commit or push.
* Save this specification as `docs/CODEX_FOURTH_PROMPT.md`.

## Single-file workflow

```text
Load MIDI
→ review suggestions
→ set preservation
→ choose preset
→ generate repair
→ compare changes
→ export repaired MIDI
```

Controls:

* Preservation: 0–100%
* Minimal / Balanced / Creative
* Enable or disable individual suggestions

At 100% preservation, no edits are allowed.

## Analysis

Create a deterministic single-clip analysis API that detects possible:

* out-of-key or local-harmony conflicts,
* awkward melodic leaps or resolutions,
* weak chord voice leading,
* duplicate/overlapping notes,
* chord or register crowding,
* bass conflicts,
* inconsistent notes in repeated motifs.

Each suggestion must include:

* affected note/location,
* category,
* confidence,
* short explanation,
* possible alternatives.

Use neutral language such as “Possible harmonic conflict.” Do not automatically remove chromatic notes, passing tones, suspensions, or intentional tension.

## Repair

Reuse the existing repair infrastructure instead of duplicating it.

Repairs remain pitch-only and must preserve:

* onset,
* duration,
* velocity,
* channel,
* tempo,
* controllers,
* program changes,
* sustain,
* unrelated MIDI events.

Presets must differ meaningfully:

* **Minimal:** few high-confidence edits.
* **Balanced:** moderate coordinated edits.
* **Creative:** broader but bounded multi-note search.

The objective should balance consistency improvement against edit count, preservation, pitch displacement, contour, motif retention, voice leading, and collision avoidance.

Do not present unchanged MIDI as a successful repair. Explain when no improving candidate is found.

## Suggestions UI

Allow users to:

* inspect suggestions,
* enable or disable each one,
* select all or clear all,
* view proposed alternatives,
* repair only enabled suggestions.

Keep low-confidence suggestions in a collapsed secondary section.

## GUI

Opening screen:

* Polish One Clip
* Combine Two Clips

Single-file mode should show:

* Load MIDI
* estimated key/mode
* preservation slider
* preset
* suggestions
* Generate Repair
* before/after piano roll
* exact edits
* estimated internal consistency before/after
* stop reason
* Export Repaired MIDI

Keep detailed analysis collapsible. Maintain readable, aligned piano-roll pitch labels.

The GUI must contain no theory or optimization logic.

## Export

Primary export:

* Repaired MIDI

Place JSON under **Advanced Export** only.

Use overwrite protection. Exported MIDI must reopen successfully and preserve unrelated events.

## Fixtures and tests

Add fixtures for:

* obvious accidental,
* intentional chromatic note,
* awkward leap,
* poor voice leading,
* duplicate overlap,
* bass conflict,
* inconsistent repeated motif,
* register crowding,
* coordinated multi-note repair,
* no-improvement material.

Tests must verify:

* deterministic analysis and repair,
* suggestions contain location/category/confidence/explanation,
* disabled suggestions are not repaired,
* intentional chromatic notes remain unchanged,
* 100% preservation prevents edits,
* lower preservation allows broader repair,
* presets behave differently,
* coordinated repairs work,
* no-improvement cases are explained,
* MIDI structure and unrelated events are preserved,
* repaired MIDI and JSON export correctly,
* source overwrite protection works,
* the two-file workflow has no regressions.

Add GUI smoke tests for loading, suggestions, preservation, presets, repair, export, and switching workflows.

## Performance

* Cache analysis for unchanged MIDI.
* Avoid recalculation from unrelated GUI events.
* Centralize search limits.
* Show a busy indicator during repair.
* Keep searches bounded and deterministic.

## Version and validation

Update the version to `0.4.0` and update README, product specification, roadmap, and fixture documentation.

Before completion, run:

```text
python -m pytest
python -m ruff check .
python -m glue --smoke-test
git diff --check
```

Also run single-file and two-file GUI smoke tests plus export/reload validation.

## Final report

Report:

* initial and final test counts,
* validation results,
* new features,
* example accidental/chromatic/multi-note/no-improvement results,
* architecture changes,
* two-file regression status,
* known limitations,
* materially changed files.

Leave all changes uncommitted.
