You are implementing GLUE V0.3.0 inside the currently open repository.

GLUE is a deterministic, preservation-first MIDI compatibility tool. V0.2 analyzes two MIDI clips, explains conflicts, and repairs one editable clip while preserving the other. V0.3 must generalize that system so both clips can be edited through a controlled Shared Compromise strategy.

Do not implement single-file Polish mode in this release. Do not add audio, live MIDI, DAW integration, plugins, cloud services, LLM APIs, accounts, telemetry, or network dependencies.

## 1. Repository and Git safety

Before changing anything:

1. Read these files completely:

   * `AGENTS.md`
   * `README.md`
   * `docs/PRODUCT_SPEC.md`
   * `docs/ROADMAP.md`
   * `pyproject.toml`

2. Inspect:

   * the current Git branch,
   * `git status`,
   * the recent Git log,
   * the existing V0.2 architecture,
   * the current repair presets and candidate model.

3. Confirm that the working tree is clean.

4. Confirm that the V0.2 baseline passes:

   * `python -m pytest`
   * `python -m ruff check .`
   * `python -m glue --smoke-test`

The expected V0.2 baseline is approximately:

* 114 tests passing,
* Ruff clean,
* application version `0.2.0`.

If the working tree contains unrelated uncommitted changes, do not overwrite or discard them. Stop and report the issue.

If the current branch is `master` and the working tree is clean, create and switch to:

```text
feature/v0.3
```

If an appropriate V0.3 feature branch already exists, continue on it.

Do not commit, merge, tag, or push anything. Leave all final changes uncommitted for human review.

Create `docs/CODEX_THIRD_PROMPT.md` and save this complete specification there for project history.

## 2. V0.3 product objective

V0.3 must support four two-clip editing strategies:

1. **Preserve A**

   * Clip A receives zero edits.
   * Clip B may be repaired.

2. **Preserve B**

   * Clip B receives zero edits.
   * Clip A may be repaired.

3. **Shared Compromise**

   * Both A and B may be edited.
   * The optimizer should search for a solution that improves compatibility while minimizing total disruption across both clips.
   * Shared mode should prefer one small edit in each clip when that is more preservation-efficient than forcing several edits into one clip.

4. **Custom Preservation**

   * The user independently controls preservation strength for A and B.
   * Higher preservation makes edits to that clip more expensive.
   * A clip at 100% preservation must receive zero edits.
   * The repair process must respond predictably when one clip has a lower preservation value than the other.

The key V0.3 question is:

> Can GLUE improve compatibility by making the smallest reasonable shared changes to both musical ideas while preserving each idea’s identity?

## 3. Architecture requirements

Preserve the existing architectural separation:

```text
models
  immutable domain data

io
  MIDI parsing and preservation-first export

analysis
  deterministic scoring and explanations

fixes
  candidate generation, optimization, and repair strategies

ui
  orchestration and visualization only
```

The GUI must not contain music-theory, scoring, or optimization logic.

Generalize the repair engine rather than creating unrelated one-off functions for every strategy.

Introduce a clear constraint model similar in purpose to:

```python
@dataclass(frozen=True)
class ClipRepairConstraints:
    preservation: float
    allow_pitch_edits: bool
    allow_octave_edits: bool
    allow_rhythm_edits: bool
    max_note_changes: int
```

The exact names and implementation may differ, but the architecture must support independent constraints for Clip A and Clip B.

For V0.3:

* Pitch edits are allowed according to the selected preset and constraints.
* Octave edits may remain supported if they already exist.
* Rhythm edits remain disabled.
* Onsets, durations, velocities, channels, tempo events, controllers, and unrelated MIDI events must remain preserved.
* The repair system must remain deterministic.
* Existing V0.2 public APIs should remain compatible unless a change is clearly necessary and documented.

## 4. Repair strategy behavior

### Preserve A

* A must remain unchanged.
* Only B candidates may be generated.
* Existing V0.2 behavior should remain compatible.
* Existing V0.2 tests must continue to pass unless exact score values were intentionally recalibrated and covered by updated assertions.

### Preserve B

* Mirror Preserve A cleanly.
* Do not duplicate the entire repair implementation.
* Use the same generalized constraint/search system.

### Shared Compromise

The system must jointly evaluate edits to A and B.

Do not implement Shared mode as:

```text
repair A first
then repair B against repaired A
```

That ordering can create biased and unstable results.

Instead, implement a bounded joint search or iterative candidate search that evaluates the pair as a combined candidate.

A valid approach may use:

* bounded beam search,
* best-first search,
* alternating optimization with full pair rescoring,
* carefully bounded combinational search,
* or another deterministic method appropriate to the current codebase.

The search must remain fast enough for the current prototype and test fixtures.

Every joint candidate must be evaluated using the full resulting pair:

```text
candidate A + candidate B
          ↓
complete compatibility analysis
          ↓
objective score
```

### Objective function

The ranking objective should account for:

* compatibility improvement,
* number of edits to A,
* number of edits to B,
* preservation setting for A,
* preservation setting for B,
* total semitone displacement,
* octave displacement,
* disruption of melodic contour,
* disruption of repeated motifs where practical,
* creation of note collisions,
* unnecessary unison doubling,
* excessive convergence of A and B into the same line,
* loss of contrapuntal independence.

The objective must not reward GLUE for making the two clips identical.

Conceptually:

```text
cost =
    remaining musical conflict
  + weighted disruption to A
  + weighted disruption to B
  + pitch displacement
  + motif/contour disruption
  + collision penalties
  + excessive-unison penalties
```

The exact coefficients belong in centralized configuration, not scattered magic numbers.

Document the coefficients and their intended effect.

## 5. Presets

Retain:

* Minimal
* Balanced
* Creative

Extend them to work under all four editing strategies.

Expected behavior:

### Minimal

* Very small edit budget.
* Strong preservation.
* Prefer the fewest possible changes.
* Rhythm remains unchanged.
* Avoid octave changes unless clearly beneficial and already allowed by existing behavior.

### Balanced

* Moderate edit budget.
* May distribute edits across both clips.
* Should noticeably improve compatibility while retaining musical identity.

### Creative

* Larger but still bounded pitch-edit budget.
* May consider broader pitch alternatives.
* Must remain deterministic.
* Must not rewrite most of either clip.
* Must still report preservation and exact edits transparently.

Do not fake preset differences by only changing a label. Tests must demonstrate meaningful differences in edit budgets or search behavior.

## 6. User interface

Update the two-clip GUI to provide an Editing Strategy control:

```text
Preserve A
Preserve B
Shared Compromise
Custom Preservation
```

### Preserve A UI

* Show A as locked.
* Show B as editable.
* A preservation should effectively be 100%.

### Preserve B UI

* Show B as locked.
* Show A as editable.
* B preservation should effectively be 100%.

### Shared Compromise UI

* Both clips are editable.
* Use sensible high-preservation defaults for both.
* The default should be cautious rather than destructive.

### Custom Preservation UI

Show two independent controls:

```text
Preserve A: 0–100%
Preserve B: 0–100%
```

Requirements:

* The values must affect optimization.
* 100% means no edits to that clip.
* Changing the controls must invalidate stale repair candidates.
* The current values must be visible in the candidate summary.
* The GUI must prevent nonsensical states where both clips are fully locked and repair is requested. Show a clear explanatory message instead of crashing.

## 7. Candidate comparison

For each preset, GLUE should be able to retain and compare candidates from different strategies.

At minimum, present the best candidate for:

* Preserve A,
* Preserve B,
* Shared Compromise.

Show:

```text
Original compatibility
Repaired compatibility
Compatibility improvement

A notes changed
B notes changed
Total notes changed

A preservation/retention
B preservation/retention

Total pitch displacement
Preset
Editing strategy
```

The user must be able to inspect exact edits separately for A and B.

Example:

```text
Shared Minimal

Compatibility:
67.4 → 88.2

Clip A:
1 of 41 notes changed
Preservation: 97.6%

Clip B:
1 of 28 notes changed
Preservation: 96.4%

A, bar 3 beat 2:
B♭4 → C5

B, bar 3 beat 2:
G4 → A♭4
```

Do not present compatibility as proof that a candidate is objectively musically correct. Use neutral wording such as “estimated compatibility.”

## 8. Visualization

Extend the existing piano-roll and timeline visualization.

Requirements:

* Original notes remain visible.
* Changed A notes are distinguishable from unchanged A notes.
* Changed B notes are distinguishable from unchanged B notes.
* Before/after note ghosts remain aligned.
* The visualization must clearly indicate which file each change belongs to.
* Do not hard-code theory logic into drawing code.
* Avoid excessive visual complexity.

A user should be able to look at the repaired result and immediately understand:

```text
A changed here
B changed here
everything else remained intact
```

## 9. Export behavior

When a candidate edits both clips, support exporting:

1. Revised Clip A
2. Revised Clip B
3. A combined-preview MIDI
4. A machine-readable change report

### Revised Clip A

* Preserve Clip A’s original MIDI structure and unrelated events.
* Change only the intended paired note pitches.
* If A has zero edits, export should remain semantically identical to the source.

### Revised Clip B

* Same requirements as A.

### Combined preview

Create a standard MIDI file containing:

* revised A on its own track,
* revised B on its own track,
* clear track names,
* appropriate shared timing/tempo metadata,
* no destructive flattening of the two clips into one note stream.

If the clips have incompatible timing metadata that prevents a reliable combined preview, fail clearly and explain the limitation.

### Change report

Export a JSON report containing at least:

```json
{
  "version": "0.3.0",
  "strategy": "shared",
  "preset": "minimal",
  "before_score": 67.4,
  "after_score": 88.2,
  "clip_a": {
    "source": "A.mid",
    "preservation": 0.85,
    "changed_notes": []
  },
  "clip_b": {
    "source": "B.mid",
    "preservation": 0.85,
    "changed_notes": []
  }
}
```

Each changed note should identify enough information to trace the edit, such as:

* clip,
* track/channel where available,
* original pitch,
* revised pitch,
* onset,
* duration,
* note index or stable note identifier.

Use safe overwrite protection. Do not overwrite source MIDI files without explicit user selection and warning.

## 10. Synthetic fixtures

Add V0.3 fixtures designed to test joint optimization.

Include at least:

### Shared-better-than-one-sided

Construct a pair where:

* Preserve A requires several edits to B,
* Preserve B requires several edits to A,
* Shared Compromise can achieve equal or better compatibility with fewer total or lower-weighted edits.

### Preservation-bias

Construct a pair where:

* A and B both contain plausible editable conflict notes,
* lowering A preservation causes the optimizer to favor editing A,
* lowering B preservation causes it to favor editing B.

### Both-locked

A fixture suitable for verifying that:

* A preservation 100%,
* B preservation 100%,
* repair is rejected gracefully.

### Unison-collapse risk

Construct a case where naively changing both lines toward identical notes would increase simplistic consonance, but the optimizer should penalize unnecessary unison convergence.

### Dual-export

A fixture where both A and B receive at least one change, and all exported files can be reopened successfully.

Update fixture documentation and generator tests.

## 11. Required tests

Add focused unit, integration, and GUI tests.

The final suite must cover at least:

### Baseline preservation

* All existing V0.2 tests still pass.
* Preserve A produces zero A edits.
* Preserve B produces zero B edits.
* Existing default repair behavior remains compatible.

### Shared repair

* Shared mode can edit both clips.
* Shared mode is deterministic.
* Shared candidates are rescored using the complete repaired pair.
* Shared mode can outperform or more efficiently solve the dedicated shared fixture.
* Minimal, Balanced, and Creative use meaningfully different edit budgets.

### Preservation controls

* 100% preservation results in zero edits for that clip.
* Lowering A preservation can shift edits toward A.
* Lowering B preservation can shift edits toward B.
* Both clips at 100% produces a clear no-edit result or user-facing validation error.
* Values outside the valid range are rejected or safely clamped at the appropriate boundary.

### Musical and structural safeguards

* No invalid note values below 0 or above 127.
* No negative durations.
* No new unintended same-clip note collisions.
* Onsets remain unchanged.
* Durations remain unchanged.
* Velocities remain unchanged.
* Channels remain unchanged.
* Tempo and unrelated MIDI events remain preserved.
* Shared repair does not collapse both clips into unnecessary identical unisons in the dedicated fixture.
* Repair candidates remain deterministic across repeated runs.

### Export

* Revised A reopens successfully.
* Revised B reopens successfully.
* Combined preview reopens successfully.
* Combined preview contains separate A and B tracks.
* JSON change report is valid and complete.
* Source overwrite protection remains effective.
* Malformed, truncated, empty, and unsupported MIDI behavior remains clear and non-destructive.

### GUI

Automated smoke coverage should verify:

* strategy selection,
* Custom Preservation controls,
* both-clips-locked validation,
* generating a Shared candidate,
* displaying A and B edit counts,
* comparing retained candidates,
* exporting A, B, combined preview, and JSON report.

Do not delete, weaken, or broadly loosen existing tests just to make the suite pass.

## 12. Performance and bounded search

The shared search space can grow quickly.

Implement explicit bounds such as:

* candidate pitches per note,
* number of editable notes considered,
* beam width or retained candidate count,
* maximum iterations,
* maximum total edits per preset.

Centralize these values in configuration.

The GUI must not freeze indefinitely.

If the existing synchronous workflow remains acceptable for small clips, document the current limitation. If shared search makes noticeable pauses likely, move repair execution into a cancellable worker without mixing algorithm logic into the UI.

Do not introduce concurrency unless it is needed and properly tested.

## 13. Documentation and versioning

Update:

* `README.md`
* `docs/PRODUCT_SPEC.md`
* `docs/ROADMAP.md`
* relevant script documentation
* package version to `0.3.0`

Document:

* the four editing strategies,
* how preservation works,
* what 100% preservation means,
* how Shared Compromise differs from sequential one-sided repair,
* what each export file contains,
* current limitations,
* exact run/test commands.

Explicitly state that V0.3 is still:

* MIDI only,
* pitch-repair only,
* deterministic,
* global major/natural-minor focused,
* limited in local harmony vocabulary,
* not a DAW plugin,
* not an AI music generator.

Single-file Polish mode should be listed as deferred future work, not silently implemented.

## 14. Implementation order

Use this order unless repository inspection reveals a strong reason to adjust it:

1. Run and record V0.2 baseline validation.
2. Understand existing repair and candidate APIs.
3. Design generalized clip constraints and strategy models.
4. Refactor one-sided repair through the generalized API while preserving behavior.
5. Implement Preserve B.
6. Implement bounded Shared Compromise search.
7. Add independent preservation weighting.
8. Add objective penalties for collisions and excessive unison convergence.
9. Add V0.3 fixtures and unit tests.
10. Add dual-file export and JSON report.
11. Update UI strategy controls and candidate comparison.
12. Add GUI smoke tests.
13. Update documentation and version.
14. Run the complete final validation.
15. Review the diff for accidental complexity or duplicated logic.

After every major stage:

* run relevant tests,
* fix regressions before continuing,
* keep the implementation deterministic,
* avoid unrelated refactoring.

## 15. Acceptance criteria

Do not declare V0.3 complete until all of the following are true:

1. The original V0.2 baseline was recorded before implementation.
2. The full final test suite passes.
3. Ruff passes.
4. `git diff --check` passes.
5. `python -m glue --smoke-test` passes.
6. `python -m glue` launches normally.
7. Preserve A guarantees zero edits to A.
8. Preserve B guarantees zero edits to B.
9. Shared Compromise can produce a candidate containing edits to both A and B.
10. Custom Preservation materially affects edit allocation.
11. Both clips at 100% preservation are handled safely.
12. Minimal, Balanced, and Creative remain meaningfully distinct.
13. Revised A exports and reopens.
14. Revised B exports and reopens.
15. Combined-preview MIDI exports and reopens with separate tracks.
16. JSON change report exports and validates.
17. Note timing, duration, velocity, channel, and unrelated MIDI events remain preserved.
18. The dedicated shared fixture demonstrates a valid advantage for Shared Compromise.
19. The dedicated unison fixture demonstrates that unnecessary line collapse is penalized.
20. No known V0.2 functional regression remains undisclosed.

## 16. Final report

When finished, provide a concise but complete report containing:

### Validation

* initial V0.2 test count,
* final test count,
* coverage if available,
* Ruff result,
* smoke-test result,
* GUI end-to-end result,
* fixture count,
* `git diff --check` result.

### Strategy demonstration

For at least one generated fixture, report:

```text
Original score
Preserve A score and edit counts
Preserve B score and edit counts
Shared score and edit counts
```

Also demonstrate that changing preservation weights changes which clip receives edits.

### New features

List the user-visible V0.3 functionality.

### Architecture

Explain:

* generalized constraints,
* shared optimizer,
* scoring objective,
* export system,
* GUI separation.

### Known limitations

Be explicit and honest.

### Regression review

State whether any V0.2 behavior changed and why.

### Materially changed files

List all materially changed files grouped by:

* models/configuration,
* analysis,
* repair,
* MIDI I/O/export,
* UI,
* fixtures/scripts,
* tests,
* documentation.

Do not commit or push the changes.
