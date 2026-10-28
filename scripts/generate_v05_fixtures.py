"""Deterministic musical-context fixtures; writes only to an explicit directory."""

from __future__ import annotations

import argparse
from pathlib import Path

from glue.io import write_midi
from glue.models import MidiClip, MidiNote, TempoChange, TrackInfo
from scripts.generate_fixtures import fixture_clips


def clip(specs: list[tuple[int, float, float, int]], name: str = "musical") -> MidiClip:
    notes = tuple(
        MidiNote(i, p, round(t * 480), round(d * 480), 90, v, v)
        for i, (p, t, d, v) in enumerate(specs)
    )
    length = max(1920, max((n.end_ticks for n in notes), default=0))
    return MidiClip(
        480,
        notes,
        tempo_changes=(TempoChange(0, 500_000),),
        tracks=tuple(TrackInfo(v, f"Voice {v}", length) for v in sorted({n.track for n in notes})),
        length_ticks=length,
        name=name,
    )


def musical_fixtures() -> dict[str, MidiClip]:
    old = fixture_clips()
    suspension = clip(
        [(p, 0, 1, 0) for p in (48, 53, 57)]
        + [(p, 1, 2, 0) for p in (48, 52, 55)]
        + [(65, 0, 1, 1), (65, 1, 0.5, 1), (64, 1.5, 1, 1)]
    )
    secondary = clip(
        [
            (p, beat, 1, 0)
            for beat, chord in enumerate(
                ((48, 52, 55), (50, 54, 57, 60), (43, 47, 50), (48, 52, 55))
            )
            for p in chord
        ]
    )
    attack_a = clip([(60, 0, 0.5, 0), (64, 1, 0.5, 0), (67, 2, 0.5, 0)], "attacks-a")
    attack_b = clip([(62, 0, 0.5, 0), (65, 1, 0.5, 0), (69, 2, 0.5, 0)], "attacks-b")
    sustain_a = clip([(60, 0, 1, 0), (62, 1, 1, 0)], "sustain-a")
    sustain_b = clip([(61, 0.5, 1, 0)], "sustain-b")
    sync = clip([(p, i + 0.375, 0.25, 0) for i, p in enumerate((60, 64, 67, 64) * 2)])
    mixed = clip([(66, 0, 0.5, 0), (64, 1, 0.5, 0)], "mixed-b")
    mixed_a = clip([(60, 0, 3, 0), (64, 1, 0.5, 1)], "mixed-a")
    return {
        "pitch_only": old["single_obvious_accidental"],
        "chromatic_passing": old["single_intentional_chromatic"],
        "suspension": suspension,
        "secondary_dominant": secondary,
        "motif_accidental": old["single_motif_inconsistency"],
        "rhythmic_collision_a": attack_a,
        "rhythmic_collision_b": attack_b,
        "call_response_a": attack_a,
        "call_response_b": attack_b,
        "timing_over_pitch_a": attack_a,
        "timing_over_pitch_b": attack_b,
        "sustain_conflict_a": sustain_a,
        "sustain_conflict_b": sustain_b,
        "pitch_timing_a": mixed_a,
        "pitch_timing_b": mixed,
        "pitch_duration_a": sustain_a,
        "pitch_duration_b": sustain_b,
        "intentional_syncopation": sync,
        "budget_a": clip([(p, i, 0.8, 0) for i in range(7) for p in (48, 52, 55)]),
        "budget_b": clip([(p, i, 0.7, 0) for i, p in enumerate((61, 66, 68, 63, 70, 73, 78))]),
        "legato_gap": clip(
            [(p, i, 0.875 if i == 1 else 1, 0) for i, p in enumerate((60, 62, 64, 65, 67))]
        ),
    }


def generate(output: Path) -> dict[str, Path]:
    output.mkdir(parents=True, exist_ok=True)
    return {
        name: write_midi(value, output / f"{name}.mid")
        for name, value in musical_fixtures().items()
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(f"Generated {len(generate(args.output_dir))} V0.5 fixtures")
