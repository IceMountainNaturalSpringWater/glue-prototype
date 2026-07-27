# GLUE V0.1 Product Specification

## Problem
Producers often have two MIDI ideas that sound good separately and are technically in the same key, yet clash when layered. Existing composition tools often generate new material. GLUE should diagnose the relationship between existing material and preserve as much as possible.

## Primary workflow
1. Import MIDI A and MIDI B.
2. Normalize both to a shared timeline without destructively editing source files.
3. Analyze each clip and the pair.
4. Show:
   - estimated key/mode
   - overall compatibility score (0-100)
   - per-window compatibility timeline
   - top conflict reasons
5. User locks A or B.
6. User selects repair strength:
   - Minimal: preserve rhythm; change as few pitches as possible, mostly +/- 1-2 scale steps or octave shifts.
   - Balanced: may change more pitches and limited octave/register placement; keep motif/rhythm recognizable.
   - Creative: broader reharmonization/transposition options, but still preserve contour/motif where possible.
7. Generate repair candidates and score before/after compatibility.
8. Export selected candidate to MIDI.

## Analysis model
Use transparent heuristic scores initially. Keep each component independently testable.

### A. Key estimation
- Build duration-weighted pitch-class histogram.
- Compare against standard major/minor key profiles (e.g. Krumhansl-style profiles).
- Return top candidates with confidence rather than pretending ambiguity does not exist.

### B. Windowing
- Convert MIDI ticks to musical time using tempo/time-signature data where available.
- Default analysis window: 1 beat.
- Aggregate bar-level summaries for UI.

### C. Local harmonic compatibility
For each time window:
- collect active/attacked pitch classes from A and B
- weight accented/long notes more strongly
- test candidate triads/seventh chords in the estimated key
- derive an implied harmony distribution for each clip
- score similarity/compatibility between the distributions

### D. Bass/root conflict
- identify the lowest sustained note in each clip/window
- estimate likely root support
- penalize strong contradictory roots, but do not penalize legitimate chord inversions blindly

### E. Register overlap
- compare pitch ranges and simultaneous note density
- penalize heavy overlap only when both parts are active in the same register; this is an arrangement-conflict score, not a music-theory error

### F. Rhythm/attack overlap
- compare note-onset density by window/subdivision
- detect excessive simultaneous attacks or dense competition
- treat this as an optional conflict signal, not inherently bad music

## Overall compatibility
Start with a weighted combination, configurable in one place:
- 50% harmonic
- 20% bass/root
- 15% register
- 15% rhythm

Expose component scores in the UI so the number is interpretable.

## Minimal repair algorithm
The first repair engine may operate on pitch only.

Goal:
maximize compatibility improvement - edit penalty

Edit penalty should include:
- number of changed notes
- semitone distance from original
- contour/motif disruption
- octave displacement

For each note in the unlocked clip that contributes to a low-scoring window:
1. consider keeping it unchanged
2. consider nearby candidate pitches within a small semitone radius
3. consider octave displacement if register overlap is the main problem
4. evaluate pair compatibility after the candidate change
5. use greedy search or beam search to find a low-edit-cost improvement

The Minimal mode must not change note onset or duration.

## UI V0.1
Single main window:
- top: file A and file B selectors
- key estimates and lengths
- lock toggle for A/B
- overall compatibility score
- component score cards
- center: simple overlay piano roll
- below: per-bar or per-beat heatmap/timeline
- right/bottom: diagnosis list
- repair buttons: Minimal / Balanced / Creative
- candidate list showing score before -> after and number of notes changed
- Export MIDI button

Do not spend excessive time on styling before analysis + export work.

## Validation
Create synthetic MIDI fixtures for:
- identical compatible melodies
- C-minor melody + compatible chord tones
- same global key but locally conflicting harmony
- strong register collision
- rhythmic collision
- obvious out-of-key notes
- transposed octave equivalent

Expected behavior must be encoded in pytest assertions with ranges, not brittle exact floating-point scores.
