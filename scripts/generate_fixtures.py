"""Generate deterministic, copyright-free MIDI fixtures for GLUE.

The script intentionally requires an output directory so it never changes
``sample_data`` merely by being imported or run without an explicit target.

Example:
    python scripts/generate_fixtures.py --output-dir .generated-fixtures
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

import mido

from glue.io import write_midi
from glue.models import MidiClip, MidiNote, TempoChange, TimeSignatureChange, TrackInfo

TICKS_PER_BEAT = 480
NoteSpec = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class DemoScenario:
    """One discoverable pair in the generated demo catalog."""

    title: str
    fixture_a: str
    fixture_b: str
    purpose: str


DEMO_SCENARIOS: Mapping[str, DemoScenario] = MappingProxyType(
    {
        "same_key_clean": DemoScenario(
            title="Same-key compatible control",
            fixture_a="demo_same_key_a",
            fixture_b="demo_same_key_clean_b",
            purpose="Confident C-major layers with compatible local harmony.",
        ),
        "same_key_conflict": DemoScenario(
            title="Same-key local conflict",
            fixture_a="demo_same_key_a",
            fixture_b="demo_same_key_conflict_b",
            purpose=(
                "Confident C-major layers whose E-minor and B-diminished "
                "windows conflict."
            ),
        ),
        "preset_repair": DemoScenario(
            title="Progressive preset repair",
            fixture_a="demo_preset_context",
            fixture_b="demo_preset_source",
            purpose="Minimal, Balanced, and Creative produce one, two, and three edits.",
        ),
        "shared_compromise": DemoScenario(
            title="Shared Compromise advantage",
            fixture_a="shared_better_a",
            fixture_b="shared_better_b",
            purpose="One small pitch edit in each clip beats a forced one-sided repair.",
        ),
        "preservation_bias": DemoScenario(
            title="Independent preservation bias",
            fixture_a="preservation_bias_a",
            fixture_b="preservation_bias_b",
            purpose="Changing A/B preservation moves the preferred edit between clips.",
        ),
        "unison_collapse": DemoScenario(
            title="Unison-collapse safeguard",
            fixture_a="unison_collapse_a",
            fixture_b="unison_collapse_b",
            purpose="Parallel semitone lines exercise the line-independence penalty.",
        ),
    }
)


def _clip(name: str, specs: Iterable[NoteSpec], *, channel: int = 0) -> MidiClip:
    notes = tuple(
        MidiNote(
            id=note_id,
            pitch=pitch,
            onset_ticks=onset,
            duration_ticks=duration,
            velocity=88,
            track=0,
            channel=channel,
        )
        for note_id, (pitch, onset, duration) in enumerate(specs)
    )
    length_ticks = max((note.end_ticks for note in notes), default=4 * TICKS_PER_BEAT)
    return MidiClip(
        ticks_per_beat=TICKS_PER_BEAT,
        notes=notes,
        tempo_changes=(TempoChange(0, 500_000),),
        time_signature_changes=(TimeSignatureChange(0, 4, 4),),
        tracks=(TrackInfo(0, "GLUE deterministic fixture", length_ticks),),
        length_ticks=length_ticks,
        name=name,
        midi_type=0,
    )


def _melody(pitches: Sequence[int], *, step: int = TICKS_PER_BEAT) -> list[NoteSpec]:
    return [(pitch, index * step, step) for index, pitch in enumerate(pitches)]


def _chord(pitches: Sequence[int], onset: int, duration: int) -> list[NoteSpec]:
    return [(pitch, onset, duration) for pitch in pitches]


_DEMO_CHORDS: Mapping[str, tuple[int, ...]] = MappingProxyType(
    {
        "C": (48, 60, 64, 67),
        "Am": (45, 60, 64),
        "F": (41, 57, 60),
        "Em": (40, 55, 59),
        "Bdim": (47, 62, 65),
        "G": (43, 59, 62),
    }
)


def _progression(
    chord_names: Sequence[str],
    *,
    pitch_shift: int = 0,
    onset_offset: int = 0,
    duration: int = TICKS_PER_BEAT,
) -> list[NoteSpec]:
    return [
        (
            pitch + pitch_shift,
            beat * TICKS_PER_BEAT + onset_offset,
            duration,
        )
        for beat, chord_name in enumerate(chord_names)
        for pitch in _DEMO_CHORDS[chord_name]
    ]


def fixture_clips() -> dict[str, MidiClip]:
    """Return deterministic fixtures through the V0.3 joint-repair scenarios."""

    identical = _melody((60, 62, 64, 67))
    c_minor_melody = _melody((60, 63, 67, 65))
    c_minor_chords = [
        *_chord((48, 51, 55), 0, 2 * TICKS_PER_BEAT),
        *_chord((53, 56, 60), 2 * TICKS_PER_BEAT, 2 * TICKS_PER_BEAT),
    ]

    # These clips have identical aggregate pitch-class histograms but put
    # C-major and D-minor sonorities in opposite local windows.
    local_a = [
        *_chord((60, 64, 67), 0, TICKS_PER_BEAT),
        *_chord((62, 65, 69), TICKS_PER_BEAT, TICKS_PER_BEAT),
    ]
    local_b = [
        *_chord((62, 65, 69), 0, TICKS_PER_BEAT),
        *_chord((60, 64, 67), TICKS_PER_BEAT, TICKS_PER_BEAT),
    ]

    register_a = _chord((60, 64, 67), 0, 2 * TICKS_PER_BEAT)
    register_collision = _chord((60, 64, 67), 0, 2 * TICKS_PER_BEAT)
    register_separated = _chord((84, 88, 91), 0, 2 * TICKS_PER_BEAT)

    dense_onsets = range(0, 2 * TICKS_PER_BEAT, TICKS_PER_BEAT // 4)
    rhythm_a = [(60, onset, TICKS_PER_BEAT // 8) for onset in dense_onsets]
    rhythm_aligned = [(67, onset, TICKS_PER_BEAT // 8) for onset in dense_onsets]
    rhythm_staggered = [
        (67, onset + TICKS_PER_BEAT // 8, TICKS_PER_BEAT // 8)
        for onset in dense_onsets
    ]

    out_of_key_context = _chord((48, 52, 55), 0, 4 * TICKS_PER_BEAT)
    out_of_key_melody = _melody((60, 62, 66, 67))

    # Repair-search regressions.  The one-note source doubles the context's E3
    # in the same register, so Minimal should consider an octave alternative.
    # The two-note source places A3 against C major twice; Balanced can improve
    # both notes with the symmetric +3-semitone alternatives in its vocabulary.
    repair_one_note_context = _chord((48, 52, 55), 0, TICKS_PER_BEAT)
    repair_one_note_source = _chord((52,), 0, TICKS_PER_BEAT)
    repair_two_note_context = _chord(
        (48, 52, 55),
        0,
        4 * TICKS_PER_BEAT,
    )
    repair_two_note_source = _melody((57, 60, 57, 60))
    # Creative same-side coordination regression.  Neither of the final two
    # Clip B edits improves the complete pair by itself; their combination
    # does.  Keep these notes simultaneous so the fixture isolates coupled
    # pitch search rather than timing or rhythmic changes.
    coordinated_same_side_a = _chord((45, 46, 51), 0, TICKS_PER_BEAT)
    coordinated_same_side_b = _chord((54, 66), 0, TICKS_PER_BEAT)
    octave_original = _melody((60, 62, 64, 67))
    octave_up = _melody((72, 74, 76, 79))

    same_key_sequence = ("C", "C", "Am", "F", "Em", "Bdim", "G", "C")
    same_key_conflict_sequence = (
        "C",
        "C",
        "Am",
        "F",
        "Bdim",
        "Em",
        "G",
        "C",
    )
    demo_same_key_a = _progression(same_key_sequence)
    demo_same_key_clean_b = _progression(
        same_key_sequence,
        pitch_shift=36,
        onset_offset=TICKS_PER_BEAT // 8,
        duration=7 * TICKS_PER_BEAT // 8,
    )
    demo_same_key_conflict_b = _progression(
        same_key_conflict_sequence,
        pitch_shift=36,
        onset_offset=TICKS_PER_BEAT // 8,
        duration=7 * TICKS_PER_BEAT // 8,
    )

    demo_preset_context = [
        *_chord((48, 52, 55), 0, TICKS_PER_BEAT),
        *_chord((57, 60, 64), TICKS_PER_BEAT, TICKS_PER_BEAT),
        *_chord((53, 57, 60), 2 * TICKS_PER_BEAT, TICKS_PER_BEAT),
        *_chord((55, 59, 62), 3 * TICKS_PER_BEAT, TICKS_PER_BEAT),
    ]
    demo_preset_source = _melody((60, 66, 61, 66))

    # The crossed conflict places one F# against C major in each timeline
    # half. A one-sided repair can address only its editable F#, while Shared
    # Compromise can change one F# in each clip for a stronger two-edit result.
    shared_better_a = [
        *_chord((48, 52, 55), 0, TICKS_PER_BEAT),
        (66, TICKS_PER_BEAT, TICKS_PER_BEAT),
    ]
    shared_better_b = [
        (66, 0, TICKS_PER_BEAT),
        *_chord((48, 52, 55), TICKS_PER_BEAT, TICKS_PER_BEAT),
    ]
    preservation_bias_a = _melody((60, 60, 60, 60))
    preservation_bias_b = _melody((66, 66, 66, 66))
    unison_collapse_a = _melody((60, 62, 64, 65))
    unison_collapse_b = _melody((61, 63, 65, 66))

    return {
        "identical_a": _clip("identical_a", identical),
        "identical_b": _clip("identical_b", identical),
        "c_minor_melody": _clip("c_minor_melody", c_minor_melody),
        "c_minor_chords": _clip("c_minor_chords", c_minor_chords),
        "local_harmony_a": _clip("local_harmony_a", local_a),
        "local_harmony_b": _clip("local_harmony_b", local_b),
        "register_a": _clip("register_a", register_a),
        "register_collision_b": _clip("register_collision_b", register_collision),
        "register_separated_b": _clip("register_separated_b", register_separated),
        "rhythm_a": _clip("rhythm_a", rhythm_a),
        "rhythm_aligned_b": _clip("rhythm_aligned_b", rhythm_aligned),
        "rhythm_staggered_b": _clip("rhythm_staggered_b", rhythm_staggered),
        "out_of_key_context": _clip("out_of_key_context", out_of_key_context),
        "out_of_key_melody": _clip("out_of_key_melody", out_of_key_melody),
        "repair_one_note_context": _clip(
            "repair_one_note_context",
            repair_one_note_context,
        ),
        "repair_one_note_source": _clip(
            "repair_one_note_source",
            repair_one_note_source,
        ),
        "repair_two_note_context": _clip(
            "repair_two_note_context",
            repair_two_note_context,
        ),
        "repair_two_note_source": _clip(
            "repair_two_note_source",
            repair_two_note_source,
        ),
        "coordinated_same_side_a": _clip(
            "coordinated_same_side_a",
            coordinated_same_side_a,
        ),
        "coordinated_same_side_b": _clip(
            "coordinated_same_side_b",
            coordinated_same_side_b,
        ),
        "octave_original": _clip("octave_original", octave_original),
        "octave_up": _clip("octave_up", octave_up),
        "demo_same_key_a": _clip("demo_same_key_a", demo_same_key_a),
        "demo_same_key_clean_b": _clip(
            "demo_same_key_clean_b",
            demo_same_key_clean_b,
        ),
        "demo_same_key_conflict_b": _clip(
            "demo_same_key_conflict_b",
            demo_same_key_conflict_b,
        ),
        "demo_preset_context": _clip(
            "demo_preset_context",
            demo_preset_context,
        ),
        "demo_preset_source": _clip(
            "demo_preset_source",
            demo_preset_source,
        ),
        "shared_better_a": _clip("shared_better_a", shared_better_a),
        "shared_better_b": _clip("shared_better_b", shared_better_b),
        "preservation_bias_a": _clip(
            "preservation_bias_a",
            preservation_bias_a,
        ),
        "preservation_bias_b": _clip(
            "preservation_bias_b",
            preservation_bias_b,
        ),
        "both_locked_a": _clip("both_locked_a", preservation_bias_a),
        "both_locked_b": _clip("both_locked_b", preservation_bias_b),
        "unison_collapse_a": _clip("unison_collapse_a", unison_collapse_a),
        "unison_collapse_b": _clip("unison_collapse_b", unison_collapse_b),
        "dual_export_a": _clip("dual_export_a", shared_better_a),
        "dual_export_b": _clip("dual_export_b", shared_better_b),
    }


def _write_metadata_fixture(path: Path) -> None:
    midi = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)

    conductor = mido.MidiTrack()
    midi.tracks.append(conductor)
    conductor.extend(
        (
            mido.MetaMessage("track_name", name="Conductor", time=0),
            mido.MetaMessage(
                "time_signature",
                numerator=3,
                denominator=4,
                clocks_per_click=24,
                notated_32nd_notes_per_beat=8,
                time=0,
            ),
            mido.MetaMessage("set_tempo", tempo=500_000, time=0),
            mido.MetaMessage("marker", text="tempo change follows", time=TICKS_PER_BEAT),
            mido.MetaMessage("set_tempo", tempo=600_000, time=0),
            mido.MetaMessage(
                "time_signature",
                numerator=4,
                denominator=4,
                clocks_per_click=24,
                notated_32nd_notes_per_beat=8,
                time=TICKS_PER_BEAT,
            ),
            mido.MetaMessage("end_of_track", time=2 * TICKS_PER_BEAT),
        )
    )

    music = mido.MidiTrack()
    midi.tracks.append(music)
    music.extend(
        (
            mido.MetaMessage("track_name", name="Music", time=0),
            mido.Message("program_change", channel=2, program=40, time=0),
            mido.Message("control_change", channel=2, control=1, value=32, time=0),
            mido.Message("note_on", channel=2, note=60, velocity=96, time=0),
            mido.Message(
                "control_change",
                channel=2,
                control=64,
                value=127,
                time=TICKS_PER_BEAT // 2,
            ),
            mido.Message(
                "note_off",
                channel=2,
                note=60,
                velocity=17,
                time=TICKS_PER_BEAT // 2,
            ),
            mido.Message("note_on", channel=2, note=64, velocity=80, time=0),
            mido.Message(
                "note_on",
                channel=2,
                note=64,
                velocity=0,
                time=TICKS_PER_BEAT,
            ),
            mido.Message("note_on", channel=9, note=36, velocity=100, time=0),
            mido.Message(
                "note_off",
                channel=9,
                note=36,
                velocity=0,
                time=TICKS_PER_BEAT // 4,
            ),
            mido.Message("sysex", data=(1, 2, 3), time=0),
            mido.MetaMessage("end_of_track", time=TICKS_PER_BEAT // 4),
        )
    )
    midi.save(filename=path)


def generate_fixtures(output_dir: str | Path) -> dict[str, Path]:
    """Write all fixtures below ``output_dir`` and return their paths."""

    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    generated: dict[str, Path] = {}
    for name, clip in fixture_clips().items():
        path = target / f"{name}.mid"
        write_midi(clip, path)
        generated[name] = path

    metadata_path = target / "metadata_roundtrip.mid"
    _write_metadata_fixture(metadata_path)
    generated["metadata_roundtrip"] = metadata_path
    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Explicit directory in which generated .mid files will be written",
    )
    args = parser.parse_args()
    generated = generate_fixtures(args.output_dir)
    print(f"Generated {len(generated)} MIDI fixtures in {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
