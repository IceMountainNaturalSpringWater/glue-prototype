from __future__ import annotations

from collections import Counter
from pathlib import Path

from glue.io import load_midi
from scripts.generate_fixtures import fixture_clips, generate_fixtures

EXPECTED_FIXTURES = {
    "identical_a",
    "identical_b",
    "c_minor_melody",
    "c_minor_chords",
    "local_harmony_a",
    "local_harmony_b",
    "register_a",
    "register_collision_b",
    "register_separated_b",
    "rhythm_a",
    "rhythm_aligned_b",
    "rhythm_staggered_b",
    "out_of_key_context",
    "out_of_key_melody",
    "octave_original",
    "octave_up",
    "metadata_roundtrip",
}


def _pitch_class_histogram(path: Path) -> Counter[int]:
    return Counter(note.pitch % 12 for note in load_midi(path).clip.notes)


def test_fixture_catalog_covers_required_v01_scenarios() -> None:
    clips = fixture_clips()

    assert EXPECTED_FIXTURES - {"metadata_roundtrip"} == clips.keys()
    assert clips["identical_a"].notes == clips["identical_b"].notes
    assert Counter(note.pitch % 12 for note in clips["local_harmony_a"].notes) == Counter(
        note.pitch % 12 for note in clips["local_harmony_b"].notes
    )
    assert [note.pitch + 12 for note in clips["octave_original"].notes] == [
        note.pitch for note in clips["octave_up"].notes
    ]
    assert 6 in {note.pitch % 12 for note in clips["out_of_key_melody"].notes}


def test_generator_writes_valid_midi_files_to_explicit_directory(tmp_path: Path) -> None:
    target = tmp_path / "generated"

    generated = generate_fixtures(target)

    assert generated.keys() == EXPECTED_FIXTURES
    assert {path.name for path in generated.values()} == {
        f"{name}.mid" for name in EXPECTED_FIXTURES
    }
    for path in generated.values():
        assert path.parent == target
        assert path.is_file()
        load_midi(path)


def test_generator_is_byte_deterministic(tmp_path: Path) -> None:
    first = generate_fixtures(tmp_path / "first")
    second = generate_fixtures(tmp_path / "second")

    assert first.keys() == second.keys()
    for name in first:
        assert first[name].read_bytes() == second[name].read_bytes()


def test_generated_local_conflict_has_same_global_material_in_other_windows(
    tmp_path: Path,
) -> None:
    generated = generate_fixtures(tmp_path)
    left = load_midi(generated["local_harmony_a"]).clip
    right = load_midi(generated["local_harmony_b"]).clip

    assert _pitch_class_histogram(generated["local_harmony_a"]) == _pitch_class_histogram(
        generated["local_harmony_b"]
    )
    left_first_window = {
        note.pitch % 12 for note in left.notes if note.onset_ticks == 0
    }
    right_first_window = {
        note.pitch % 12 for note in right.notes if note.onset_ticks == 0
    }
    assert left_first_window == {0, 4, 7}
    assert right_first_window == {2, 5, 9}


def test_metadata_fixture_exercises_tempo_signatures_tracks_and_channels(
    tmp_path: Path,
) -> None:
    path = generate_fixtures(tmp_path)["metadata_roundtrip"]

    document = load_midi(path)
    clip = document.clip

    assert clip.midi_type == 1
    assert [track.name for track in clip.tracks] == ["Conductor", "Music"]
    assert [(change.tick, change.tempo) for change in clip.tempo_changes] == [
        (0, 500_000),
        (480, 600_000),
    ]
    assert [
        (change.tick, change.numerator, change.denominator)
        for change in clip.time_signature_changes
    ] == [(0, 3, 4), (960, 4, 4)]
    assert {note.channel for note in clip.notes} == {2, 9}
    assert any(note.is_percussion for note in clip.notes)
    assert document.warnings == ()
