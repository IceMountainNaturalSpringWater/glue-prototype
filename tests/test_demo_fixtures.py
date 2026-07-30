from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from glue.analysis import analyze_pair
from glue.fixes import RepairPreset, generate_repair, repair_config_for
from glue.io import load_midi
from glue.models import MidiClip
from scripts.generate_fixtures import (
    DEMO_SCENARIOS,
    DemoScenario,
    fixture_clips,
    generate_fixtures,
)

TICKS_PER_BEAT = 480


def _pitches_by_onset(clip: MidiClip) -> list[tuple[int, ...]]:
    return [
        tuple(note.pitch for note in clip.notes if note.onset_ticks == onset)
        for onset in sorted({note.onset_ticks for note in clip.notes})
    ]


def test_demo_catalog_is_discoverable_immutable_and_exact() -> None:
    clips = fixture_clips()

    assert DEMO_SCENARIOS == {
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
    with pytest.raises(TypeError):
        DEMO_SCENARIOS["other"] = DEMO_SCENARIOS["same_key_clean"]  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        DEMO_SCENARIOS["same_key_clean"].title = "changed"  # type: ignore[misc]

    assert _pitches_by_onset(clips["demo_same_key_a"]) == [
        (48, 60, 64, 67),
        (48, 60, 64, 67),
        (45, 60, 64),
        (41, 57, 60),
        (40, 55, 59),
        (47, 62, 65),
        (43, 59, 62),
        (48, 60, 64, 67),
    ]
    assert _pitches_by_onset(clips["demo_same_key_clean_b"]) == [
        (84, 96, 100, 103),
        (84, 96, 100, 103),
        (81, 96, 100),
        (77, 93, 96),
        (76, 91, 95),
        (83, 98, 101),
        (79, 95, 98),
        (84, 96, 100, 103),
    ]
    assert _pitches_by_onset(clips["demo_same_key_conflict_b"])[4:6] == [
        (83, 98, 101),
        (76, 91, 95),
    ]
    assert {
        note.duration_ticks for note in clips["demo_same_key_a"].notes
    } == {TICKS_PER_BEAT}
    assert {
        note.duration_ticks for note in clips["demo_same_key_clean_b"].notes
    } == {7 * TICKS_PER_BEAT // 8}
    assert _pitches_by_onset(clips["demo_preset_context"]) == [
        (48, 52, 55),
        (57, 60, 64),
        (53, 57, 60),
        (55, 59, 62),
    ]
    assert [note.pitch for note in clips["demo_preset_source"].notes] == [
        60,
        66,
        61,
        66,
    ]


def test_generated_same_key_demo_isolates_local_harmony_conflict(
    tmp_path: Path,
) -> None:
    generated = generate_fixtures(tmp_path)
    clip_a = load_midi(generated["demo_same_key_a"]).clip
    clean_b = load_midi(generated["demo_same_key_clean_b"]).clip
    conflict_b = load_midi(generated["demo_same_key_conflict_b"]).clip

    clean = analyze_pair(clip_a, clean_b)
    conflict = analyze_pair(clip_a, conflict_b)

    for result in (clean, conflict):
        assert result.key_a.label == "C major"
        assert result.key_b.label == "C major"
        assert result.combined_key.label == "C major"
        assert result.key_a.confidence > 0.95
        assert result.key_b.confidence > 0.95
        assert result.combined_key.confidence > 0.95

    assert 95 <= clean.harmonic_score <= 97
    assert 95 <= clean.bass_score <= 97
    assert clean.register_score == 100
    assert clean.rhythm_score == 100
    assert 96 <= clean.overall_score <= 98
    assert clean.reasons == ()

    assert 87 <= conflict.harmonic_score <= 90
    assert 92 <= conflict.bass_score <= 95
    assert conflict.register_score > 99
    assert conflict.rhythm_score == 100
    assert 92 <= conflict.overall_score <= 94
    assert all(window.overall_score > 97 for window in conflict.windows[:4])
    assert all(window.overall_score > 97 for window in conflict.windows[6:])

    conflict_windows = conflict.windows[4:6]
    assert all(63 <= window.harmonic_score < 65 for window in conflict_windows)
    assert all(78 <= window.overall_score <= 81 for window in conflict_windows)
    assert [window.local_harmony_a[0].label for window in conflict_windows] == [
        "E minor",
        "B diminished",
    ]
    assert [window.local_harmony_b[0].label for window in conflict_windows] == [
        "B diminished",
        "E minor",
    ]
    for window in conflict_windows:
        reason = next(
            item for item in window.reasons if item.component == "harmonic"
        )
        assert "E minor" in reason.message
        assert "B diminished" in reason.message
        assert "E-F forms a semitone" in reason.message
        assert "B-F forms a tritone" in reason.message


def test_generated_preset_demo_repairs_progressively_and_preserves_timing(
    tmp_path: Path,
) -> None:
    generated = generate_fixtures(tmp_path)
    context = load_midi(generated["demo_preset_context"]).clip
    source = load_midi(generated["demo_preset_source"]).clip

    results = {
        preset: generate_repair(
            context,
            source,
            repair_config=repair_config_for(preset),
        )
        for preset in RepairPreset
    }

    minimal = results[RepairPreset.MINIMAL]
    balanced = results[RepairPreset.BALANCED]
    creative = results[RepairPreset.CREATIVE]
    assert 70 <= minimal.original_score <= 73
    assert [result.changed_note_count for result in results.values()] == [1, 2, 3]
    assert [
        minimal.original_score,
        minimal.repaired_score,
        balanced.repaired_score,
        creative.repaired_score,
    ] == sorted(
        (
            minimal.original_score,
            minimal.repaired_score,
            balanced.repaired_score,
            creative.repaired_score,
        )
    )
    assert 76 <= minimal.repaired_score <= 79
    assert 81 <= balanced.repaired_score <= 84
    assert 86 <= creative.repaired_score <= 89
    assert [
        (edit.note_id, edit.original_pitch, edit.repaired_pitch)
        for edit in minimal.edits
    ] == [(3, 66, 67)]
    assert [
        (edit.note_id, edit.original_pitch, edit.repaired_pitch)
        for edit in balanced.edits
    ] == [(3, 66, 67), (1, 66, 69)]
    assert [
        (edit.note_id, edit.original_pitch, edit.repaired_pitch)
        for edit in creative.edits
    ] == [(3, 66, 67), (1, 66, 69), (2, 61, 65)]
    assert [note.pitch for note in minimal.repaired_clip.notes] == [60, 66, 61, 67]
    assert [note.pitch for note in balanced.repaired_clip.notes] == [60, 69, 61, 67]
    assert [note.pitch for note in creative.repaired_clip.notes] == [60, 69, 65, 67]

    source_timing = [
        (note.id, note.onset_ticks, note.duration_ticks) for note in source.notes
    ]
    for result in results.values():
        assert [
            (note.id, note.onset_ticks, note.duration_ticks)
            for note in result.repaired_clip.notes
        ] == source_timing
        assert result.repaired_score >= result.original_score
