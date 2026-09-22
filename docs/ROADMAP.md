# GLUE roadmap

## V0.1 - Working standalone prototype
MIDI A/B import, diagnostics, compatibility heatmap, Minimal repair, MIDI export.

## V0.2 - Demo quality (complete)
Simultaneous-note and local-harmony inference, preservation control, three
deterministic pitch-repair modes, specific explanations, before/after
visualization, hardened MIDI errors, and generated demo scenarios.

## V0.3 - Controlled two-clip repair (complete)
Independent A/B preservation constraints, bounded full-pair optimization,
unison/line-independence safeguards, dual-clip visualization, revised A/B
exports, separate-track preview, JSON report, and joint-optimization fixtures.

## V0.4 - Single MIDI Repair (retained baseline)
Persistent top-level **Combine Two Clips** and **Polish One Clip** switching,
conservative single-clip suggestions, suggestion-level opt-in controls,
preservation-aware Minimal/Balanced/Creative pitch repair, before/after
inspection, and source-preserving MIDI plus optional JSON export. Combine mode
is the initial workspace and retains its established behavior.

## V0.5 - Advanced Musical Repair (current prototype)

Cached sequence harmony and phrase/motif/rhythmic evidence; shared complete-
passage beam repair; independent pitch/timing/duration permissions; bounded
timing and sustain edits; diverse alternatives; expandable rationale; faithful
event-rescheduling export; reproducible fixtures and calibration reports.
Existing V0.4 public APIs remain available for comparison and regressions.

## V0.5.x - Producer validation
Test both workflows with real producer material, collect false-positive and
missed-repair cases, calibrate confidence and objective weights, and improve
bounded-search progress/cancellation.

## Future - Plugin architecture experiment
Only after standalone producer value is validated, evaluate exposing the
analysis core through a suitable native plugin/standalone architecture.

## V1
Commercial-quality VST3/AU + standalone application, licensing/storefront only after producer demand is validated.
