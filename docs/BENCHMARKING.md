# GLUE V0.5.1: offline benchmarking and calibration

The production V0.5 repair, analysis, GUI and objective weights are unchanged.
`glue.benchmark` is a separate, GUI-independent package using only the existing
dependencies and Python standard library. It never downloads datasets.

## Quick start (PowerShell, repository root)

```powershell
# Use the existing environment; no new dependencies are needed.
.venv\Scripts\python.exe -m glue.benchmark --help
.venv\Scripts\python.exe -m glue.benchmark synthetic --output-dir .test-tmp/benchmark-demo
.venv\Scripts\python.exe -m glue.benchmark run .test-tmp/benchmark-demo/manifest.json --output-dir .test-tmp/benchmark-demo/run1 --seeds 17 --pair-preservation 100:0 0:100
```

Output directories must be new: existing reports and references are never
overwritten. Sources are read-only. Corrupted copies exist in immutable domain
objects, not edited source files. JSON records enough source hashes, stable note
IDs, note-on/off event indices and exact field values to reproduce each case.

## Import local material

Use only material you are authorized to access. Dataset availability, license
and musical coherence are the operator's responsibility. No commercial MIDI is
bundled. All generated demonstration notes are self-authored CC0 material.

```powershell
# Generic local reference folder
.venv\Scripts\python.exe -m glue.benchmark manifest ./my-references --dataset reference --seed 42 --output .test-tmp/reference-manifest.json

# POP909-style directory: MIDI track names MELODY, BRIDGE and PIANO
.venv\Scripts\python.exe -m glue.benchmark manifest ./local-pop909 --dataset pop909 --pop-pairs --window-beats 16 --windows-per-piece 4 --output .test-tmp/pop-manifest.json

# MAESTRO-style metadata: record-array / column-oriented JSON, or CSV
.venv\Scripts\python.exe -m glue.benchmark manifest ./local-maestro --dataset maestro --metadata ./local-maestro/maestro.csv --window-beats 16 --output .test-tmp/piano-manifest.json
```

POP track names are retained as roles. `--pop-pairs` splits MELODY from
BRIDGE/PIANO/ACCOMPANIMENT, retaining original note/event identities. Chord/beat/key
sidecar files (`chord_midi.txt`, `beat_midi.txt`, `chord_audio.txt`, `key_audio.txt`)
are inventoried and hash-verified. Their raw timestamp/chord dialects are not
silently interpreted as beat-based ground truth. The current harmony metric is
an explicitly labeled interval proxy, **not annotated chord-inference accuracy**.

MAESTRO rows require `midi_filename`, `canonical_composer`, `canonical_title`;
optional `split` maps train/validation to calibration and test to evaluation.
Composer/title groups may not cross splits, even if performances differ. Conflicts
fail inventory generation; review/normalize metadata rather than silently moving
examples. Reference folders group files by relative parent directory, or stem for
flat folders. Hashed group names assign approximately 20% to evaluation when no
official split exists. Very small inventories may have an empty split.

Review manifests before use: group alternate arrangements/performances of the
same composition together. Exact file hashes and explicit piece groups cannot
detect all near-duplicates or mislabeled compositions. Relative source paths must
stay under the dataset root, including resolved symlinks. A manifest's `root` may
be absolute or relative to the manifest file.

Long files need an explicit window policy. `--window-beats` chooses evenly spaced
windows without consulting GLUE results. Each window retains notes whose onsets
are inside, including complete note tails; earlier sustained notes are excluded.
Onsets are translated to zero-based window time and effective tempo/meter retained.
This loses boundary context, and windows in changing meter need extra review.
Empty windows and passages above `--max-notes` (default 256 total notes) are reported
as skipped, not successful recovery. No hidden truncation or outcome-based sampling.

To define a local two-file case manually, use one manifest entry with two sources:

```json
{
  "id": "piece-01-pair", "group": "piece-01", "split": "calibration",
  "sources": [
    {"path": "piece-01/a.mid", "sha256": "SHA256_OF_A"},
    {"path": "piece-01/b.mid", "sha256": "SHA256_OF_B"}
  ]
}
```

Sources may optionally select `tracks: [0, 1]`. Both files must already share a
beat timeline; the benchmark never aligns performances using the original.

## Experiments and corruption

Defaults: all three presets; preservation 0, 50, 90, 100; seed 0; one changed note;
severity 1; calibration split; all three edit permissions enabled explicitly.
This is an experiment profile, **not a change to GUI permission defaults**.
Every setting includes a clean control, once rather than repeated per seed.
Minimal retains its existing conservative technical-only timing/duration rules.

```powershell
# Example default pitch-only user workflow and asymmetric pair controls
.venv\Scripts\python.exe -m glue.benchmark run .test-tmp/reference-manifest.json --output-dir .test-tmp/pitch-baseline --permissions pitch --preservation 0 50 90 100 --pair-preservation 100:0 0:100 --seeds 1 2 3

# Clean controls only (no corruption kinds after --kinds)
.venv\Scripts\python.exe -m glue.benchmark run .test-tmp/reference-manifest.json --output-dir .test-tmp/clean-baseline --kinds
```

Supported kinds:

| Group | CLI names | Operational definition |
|---|---|---|
| Pitch | accidental, wrong_diatonic, wrong_chord_tone, octave, bass_pitch, motif | Semitone; another reference-scale pitch; another observed chord pitch class; octave; lowest-pitch accidental; alteration in an exact repeated four-note motif |
| Timing | early, late, attack_collision, call_response, groove | Bounded onset displacement; coincident attack; collapse cross-clip spacing; small displacement without quantizing the source |
| Duration | sustain, short, harmony_overlap, bass_lead_collision | Extend; shorten; sustain into a different observed three-tone sonority; overlap a different-register attack |
| Combined | pitch_timing, pitch_duration, timing_duration, coordinated | Combined fields on one note; coordinated changes on at least two notes within four beats |

`--severity` is finite in (0, 4], scaling onset/duration shifts and diatonic rank.
Accidentals remain exactly one semitone; octave displacement is one or two octaves.
`--count` controls the number of corrupted notes. The default onset shift is 1/8
quarter-note beat, sustain extension 1/2 beat, and shortening halves duration.
Attack/spacing collisions search within severity beats. All choices use a stable
SHA-256-derived case seed plus a private RNG, not Python's process-randomized hash.

Reference-scale and chord hypotheses come only from the reference in the corruptor,
not the repair engine. They are ambiguous: another diatonic/chord tone can be valid
music. Recovery measures the chosen reference, not whether every variant sounds bad.
Positive durations, pitch range, track endpoints and unambiguous same-pitch note
pairing constrain injected errors. Inapplicable types are skipped with reasons.

## Blind repair and metrics

The runner passes **only corrupted clips**, preset, permissions and preservation
to `generate_musical_repairs`. No original MIDI, corruption IDs, annotations,
original pitches, or ground-truth scoring enters repair. It always evaluates the
first candidate (or unchanged input if none), not the alternative closest to truth.
Retained alternatives are evaluated post-hoc solely as ranking diagnostics.

Notes match by source clip slot + note ID, never nearest pitch/onset. Do not reload
repaired MIDI and match parser-assigned IDs, which can change after event reordering.

- Pitch and pitch-class recovery: fraction of pitch-corrupted notes restored.
  Octave errors can have perfect pitch-class recovery but zero pitch recovery.
- Exact-note recovery: all note attributes restored on a corrupted note.
- Onset/duration absolute errors: means and totals, before/after, in quarter-note beats.
- Motif similarity: fraction of repeated four-note reference patterns with preserved
  pitch intervals, relative onsets and durations. Contour compares successive pitch
  directions within source track/channel, excluding simultaneous reference attacks.
  Polyphonic track/channel order is only a proxy, not true voice separation.
- Harmony: overlap-duration-weighted interval-consonance proxy (semitone/tritone
  tension, smaller whole-tone tension). Pair reports add cross-clip harmony,
  mean register distance of overlapping notes, simultaneous-attack fraction over
  all cross-note pairs (within 1/64 beat), and one minus that fraction as a simple
  rhythmic-complementarity proxy. These are not independent musical-quality ratings.
- Untouched preservation: unchanged notes outside the corruption ledger.
  Unnecessary field edits additionally count edits to clean fields of corrupted notes.
- Distance: sum of absolute pitch semitones + onset beats + duration beats.
  Components remain available. An ancillary distance + **10 per unnecessary field
  edit** highlights collateral damage; it never replaces the component report.
- Clean false positives: edited notes / all clean reference notes. A coherent
  reference need not maximize GLUE's fit score. Clean controls are equally important.

No applicable observations means JSON `null`, not a perfect score. Aggregate recovery
and false-positive rates are note-weighted; reports separately identify presets,
preservation, workflow, corruption type, engine errors, and skipped cases. Locked
100% controls naturally have zero recovery and must not be confused with search bugs.

## Reports, reproducibility, and calibration

Every run writes `results.json`, `results.csv`, `summary.json`, `summary.md`.
JSON includes the manifest, source/event ledger, experiment settings, search config,
algorithm and benchmark code fingerprints, repair edits, component metrics, failures,
worst/made-worse examples, and runtime vs note count. Runtime measures the repair
invocation only, excluding I/O, corruption and metrics. Top-level analysis caches
are cleared per invocation; pure transition memoization remains. Timings vary by
machine/process and are excluded from the reproducibility digest, as is environment
metadata. Results and errors are not excluded.

Failure attribution explicitly distinguishes observations from hypotheses:
unavailable exact pitch/onset/duration options, hard locks, disabled permissions,
exhausted budgets, low-confidence harmony, collateral edits, and lower-ranked
alternatives closer to truth. Analysis, harmony inference, candidate generation,
search, scoring, preservation penalties, timing and duration are all represented.
The framework cannot prove every upstream cause without a future engine trace API.

No production algorithm/weight tuning was made for V0.5.1. First retain a baseline,
then use calibration-only evidence to propose an isolated change. Rerun the exact
same manifest, seeds and settings. Compare recovery, clean false positives,
unnecessary edits, runtime, errors and skipped coverage separately:

```powershell
.venv\Scripts\python.exe -m glue.benchmark compare baseline/results.json proposed/results.json --output .test-tmp/comparison.json
```

Different manifest/settings/benchmark implementations are rejected as unmatched
comparisons. Freeze changes before running `--split evaluation`; never tune directly
against evaluation failures. Keep real producer ratings and broader genre coverage
as the next calibration step. Synthetic results are not a final quality benchmark.
