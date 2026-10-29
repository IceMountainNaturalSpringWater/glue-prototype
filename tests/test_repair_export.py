from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import mido
import pytest

import glue.exporting as exporting_module
from glue.analysis import analyze_pair
from glue.exporting import (
    RepairExportError,
    RepairExportPaths,
    build_change_report,
    export_change_report,
    export_combined_repair_preview,
    export_repair_bundle,
    export_revised_clip,
    serialize_change_report,
)
from glue.fixes import EditingStrategy, PairRepairResult, generate_pair_repair
from glue.io import (
    CombinedPreviewError,
    MidiDocument,
    build_combined_preview,
    load_midi,
    write_combined_preview,
)
from glue.models import MidiClip, MidiNote, TempoChange, TimeSignatureChange
from scripts.generate_fixtures import generate_fixtures


@pytest.fixture(scope="module")
def dual_export_case(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[MidiDocument, MidiDocument, PairRepairResult]:
    fixture_dir = tmp_path_factory.mktemp("dual-export-fixtures")
    generated = generate_fixtures(fixture_dir)
    document_a = load_midi(generated["dual_export_a"])
    document_b = load_midi(generated["dual_export_b"])
    result = generate_pair_repair(
        document_a.clip,
        document_b.clip,
        strategy=EditingStrategy.SHARED,
    )
    assert result.changed_note_count_a == 1
    assert result.changed_note_count_b == 1
    return document_a, document_b, result


def _message_dicts(path: Path) -> tuple[tuple[dict[str, object], ...], ...]:
    midi = mido.MidiFile(filename=path)
    return tuple(tuple(message.dict() for message in track) for track in midi.tracks)


def test_individual_artifact_exports_are_valid_and_source_safe(
    tmp_path: Path,
    dual_export_case: tuple[MidiDocument, MidiDocument, PairRepairResult],
) -> None:
    document_a, document_b, result = dual_export_case
    revised_a = export_revised_clip(
        result,
        document_a,
        document_b,
        "A",
        tmp_path / "A.mid",
    )
    revised_b = export_revised_clip(
        result,
        document_a,
        document_b,
        "B",
        tmp_path / "B.mid",
    )
    preview = export_combined_repair_preview(
        result,
        document_a,
        document_b,
        tmp_path / "combined.mid",
    )
    report = export_change_report(
        result,
        document_a,
        document_b,
        tmp_path / "changes.json",
    )

    assert load_midi(revised_a).clip.notes == result.repaired_clip_a.notes
    assert load_midi(revised_b).clip.notes == result.repaired_clip_b.notes
    assert len(load_midi(preview).clip.tracks) == 2
    assert json.loads(report.read_text(encoding="utf-8"))["strategy"] == "shared"
    with pytest.raises(RepairExportError, match="Refusing to overwrite loaded"):
        export_revised_clip(
            result,
            document_a,
            document_b,
            "A",
            document_b.source_path,
        )


def _assert_template_changed_only_at_edits(
    document: MidiDocument,
    exported: Path,
    edit_ids: set[int],
) -> None:
    changed_references = {
        (reference.track, reference.event_index)
        for note_id in edit_ids
        for reference in (
            document.bindings[note_id].note_on,
            document.bindings[note_id].note_off,
        )
    }
    before = _message_dicts(document.source_path)
    after = _message_dicts(exported)
    for track_index, (before_track, after_track) in enumerate(
        zip(before, after, strict=True)
    ):
        for event_index, (before_message, after_message) in enumerate(
            zip(before_track, after_track, strict=True)
        ):
            changed_fields = {
                field
                for field in before_message.keys() | after_message.keys()
                if before_message.get(field) != after_message.get(field)
            }
            if (track_index, event_index) in changed_references:
                assert changed_fields == {"note"}
            else:
                assert changed_fields == set()


def test_bundle_exports_two_revised_midis_preview_and_traceable_json(
    dual_export_case: tuple[MidiDocument, MidiDocument, PairRepairResult],
    tmp_path: Path,
) -> None:
    document_a, document_b, repair = dual_export_case
    paths = RepairExportPaths.from_base(tmp_path / "candidate.mid")

    exported = export_repair_bundle(repair, document_a, document_b, paths)

    assert exported.paths == paths
    assert all(path.is_file() for path in paths.all_paths)
    with pytest.raises(FrozenInstanceError):
        exported.paths = paths  # type: ignore[misc]

    revised_a = load_midi(paths.revised_a).clip
    revised_b = load_midi(paths.revised_b).clip
    assert revised_a.notes == repair.repaired_clip_a.notes
    assert revised_b.notes == repair.repaired_clip_b.notes
    assert analyze_pair(revised_a, revised_b).overall_score == pytest.approx(
        repair.repaired_score
    )
    _assert_template_changed_only_at_edits(
        document_a,
        paths.revised_a,
        {edit.note_id for edit in repair.edits_a},
    )
    _assert_template_changed_only_at_edits(
        document_b,
        paths.revised_b,
        {edit.note_id for edit in repair.edits_b},
    )

    combined_midi = mido.MidiFile(filename=paths.combined_preview)
    assert len(combined_midi.tracks) == 2
    assert [
        next(message.name for message in track if message.type == "track_name")
        for track in combined_midi.tracks
    ] == ["GLUE Revised A", "GLUE Revised B"]
    combined = load_midi(paths.combined_preview).clip
    assert [note.pitch for note in combined.notes if note.track == 0] == [
        note.pitch for note in repair.repaired_clip_a.notes
    ]
    assert [note.pitch for note in combined.notes if note.track == 1] == [
        note.pitch for note in repair.repaired_clip_b.notes
    ]

    report = json.loads(paths.change_report.read_text(encoding="utf-8"))
    assert report["version"] == "0.5.4"
    assert report["strategy"] == "shared"
    assert report["preset"] == "minimal"
    assert report["before_score"] == pytest.approx(repair.original_score)
    assert report["after_score"] == pytest.approx(repair.repaired_score)
    for label, document, edits in (
        ("a", document_a, repair.edits_a),
        ("b", document_b, repair.edits_b),
    ):
        clip_report = report[f"clip_{label}"]
        assert clip_report["source"] == document.source_path.name
        assert clip_report["preservation"] == pytest.approx(0.85)
        assert clip_report["changed_note_count"] == 1
        changed = clip_report["changed_notes"]
        assert len(changed) == len(edits)
        note = next(item for item in document.clip.notes if item.id == edits[0].note_id)
        assert changed[0] == {
            "clip": label.upper(),
            "note_id": note.id,
            "track": note.track,
            "channel": note.channel,
            "original_pitch": edits[0].original_pitch,
            "revised_pitch": edits[0].repaired_pitch,
            "onset_ticks": note.onset_ticks,
            "duration_ticks": note.duration_ticks,
        }


def test_zero_edit_side_is_semantically_identical_to_its_source(
    dual_export_case: tuple[MidiDocument, MidiDocument, PairRepairResult],
    tmp_path: Path,
) -> None:
    document_a, document_b, _ = dual_export_case
    repair = generate_pair_repair(
        document_a.clip,
        document_b.clip,
        strategy=EditingStrategy.PRESERVE_A,
    )
    paths = RepairExportPaths.from_base(tmp_path / "preserve-a")

    export_repair_bundle(repair, document_a, document_b, paths)

    assert repair.edits_a == ()
    assert _message_dicts(paths.revised_a) == _message_dicts(document_a.source_path)


def test_combined_preview_rescales_different_ppq_exactly_and_coalesces_defaults(
    tmp_path: Path,
) -> None:
    clip_a = MidiClip(
        ticks_per_beat=480,
        notes=(MidiNote(0, 60, 240, 480, 90, 0, 0),),
        length_ticks=960,
    )
    clip_b = MidiClip(
        ticks_per_beat=960,
        notes=(MidiNote(0, 67, 480, 960, 80, 0, 1),),
        tempo_changes=(TempoChange(0, 500_000),),
        time_signature_changes=(TimeSignatureChange(0, 4, 4),),
        length_ticks=1_920,
    )

    preview = build_combined_preview(clip_a, clip_b)

    assert preview.ticks_per_beat == 960
    assert preview.tempo_changes == ()
    assert preview.time_signature_changes == ()
    assert [
        (note.pitch, note.onset_ticks, note.duration_ticks, note.track, note.channel)
        for note in preview.notes
    ] == [
        (60, 480, 960, 0, 0),
        (67, 480, 960, 1, 1),
    ]
    output = write_combined_preview(clip_a, clip_b, tmp_path / "preview.mid")
    reloaded = load_midi(output).clip
    assert reloaded.ticks_per_beat == 960
    assert [(track.index, track.name) for track in reloaded.tracks] == [
        (0, "GLUE Revised A"),
        (1, "GLUE Revised B"),
    ]


def test_combined_preview_rejects_cross_track_note_pairing_ambiguity() -> None:
    clip_a = MidiClip(
        ticks_per_beat=480,
        notes=(
            MidiNote(0, 60, 0, 480, 90, 0, 0),
            MidiNote(1, 60, 120, 120, 80, 1, 0),
        ),
        midi_type=1,
    )
    clip_b = MidiClip(
        ticks_per_beat=480,
        notes=(MidiNote(0, 67, 0, 120, 90, 0, 1),),
        midi_type=0,
    )

    with pytest.raises(
        CombinedPreviewError,
        match=r"Clip A.*channel 1.*source tracks 0 and 1.*note-off identity",
    ):
        build_combined_preview(clip_a, clip_b)


def test_combined_export_validates_reloaded_note_timing_semantics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dual_export_case: tuple[MidiDocument, MidiDocument, PairRepairResult],
) -> None:
    document_a, document_b, repair = dual_export_case
    real_write_midi = exporting_module.write_midi

    def write_with_corrupted_duration(clip: MidiClip, destination: str | Path) -> Path:
        first = clip.notes[0]
        corrupted = clip.with_notes(
            (
                MidiNote(
                    id=first.id,
                    pitch=first.pitch,
                    onset_ticks=first.onset_ticks,
                    duration_ticks=first.duration_ticks + 1,
                    velocity=first.velocity,
                    release_velocity=first.release_velocity,
                    track=first.track,
                    channel=first.channel,
                ),
                *clip.notes[1:],
            )
        )
        return real_write_midi(corrupted, destination)

    monkeypatch.setattr(
        exporting_module,
        "write_midi",
        write_with_corrupted_duration,
    )
    destination = tmp_path / "corrupted-preview.mid"

    with pytest.raises(RepairExportError, match="note timing semantics"):
        exporting_module.export_combined_repair_preview(
            repair,
            document_a,
            document_b,
            destination,
        )

    assert not destination.exists()


def test_combined_preview_rejects_incompatible_metadata_before_writing(
    tmp_path: Path,
) -> None:
    clip_a = MidiClip(ticks_per_beat=480)
    incompatible_tempo = MidiClip(
        ticks_per_beat=480,
        tempo_changes=(TempoChange(0, 600_000),),
    )
    tempo_path = tmp_path / "tempo.mid"
    with pytest.raises(CombinedPreviewError, match="incompatible tempo maps"):
        write_combined_preview(clip_a, incompatible_tempo, tempo_path)
    assert not tempo_path.exists()

    incompatible_signature = MidiClip(
        ticks_per_beat=480,
        time_signature_changes=(TimeSignatureChange(0, 3, 4),),
    )
    signature_path = tmp_path / "signature.mid"
    with pytest.raises(CombinedPreviewError, match="incompatible time-signature maps"):
        write_combined_preview(clip_a, incompatible_signature, signature_path)
    assert not signature_path.exists()

    with pytest.raises(CombinedPreviewError, match="above the Standard MIDI File limit"):
        build_combined_preview(
            MidiClip(ticks_per_beat=480),
            MidiClip(ticks_per_beat=481),
        )


def test_bundle_preflight_protects_both_sources_and_all_destinations_atomically(
    dual_export_case: tuple[MidiDocument, MidiDocument, PairRepairResult],
    tmp_path: Path,
) -> None:
    document_a, document_b, repair = dual_export_case
    before_a = document_a.source_path.read_bytes()
    before_b = document_b.source_path.read_bytes()
    paths = RepairExportPaths(
        revised_a=tmp_path / "safe-a.mid",
        revised_b=tmp_path / "safe-b.mid",
        combined_preview=tmp_path / "safe-combined.mid",
        change_report=document_b.source_path,
    )

    with pytest.raises(RepairExportError, match="Refusing to overwrite loaded MIDI"):
        export_repair_bundle(repair, document_a, document_b, paths)

    assert document_a.source_path.read_bytes() == before_a
    assert document_b.source_path.read_bytes() == before_b
    assert not paths.revised_a.exists()
    assert not paths.revised_b.exists()
    assert not paths.combined_preview.exists()

    duplicate = tmp_path / "duplicate.mid"
    duplicate_paths = RepairExportPaths(
        revised_a=duplicate,
        revised_b=duplicate,
        combined_preview=tmp_path / "other.mid",
        change_report=tmp_path / "other.json",
    )
    with pytest.raises(RepairExportError, match="distinct path"):
        export_repair_bundle(repair, document_a, document_b, duplicate_paths)
    assert not duplicate.exists()


def test_existing_output_requires_explicit_overwrite_and_reports_are_deterministic(
    dual_export_case: tuple[MidiDocument, MidiDocument, PairRepairResult],
    tmp_path: Path,
) -> None:
    document_a, document_b, repair = dual_export_case
    paths = RepairExportPaths.from_base(tmp_path / "existing")
    paths.revised_a.write_bytes(b"keep me")

    with pytest.raises(RepairExportError, match="existing export"):
        export_repair_bundle(repair, document_a, document_b, paths)
    assert paths.revised_a.read_bytes() == b"keep me"
    assert not paths.revised_b.exists()

    export_repair_bundle(
        repair,
        document_a,
        document_b,
        paths,
        overwrite=True,
    )
    load_midi(paths.revised_a)
    expected = serialize_change_report(
        build_change_report(repair, document_a, document_b)
    )
    assert paths.change_report.read_bytes() == expected
    assert serialize_change_report(
        build_change_report(repair, document_a, document_b)
    ) == expected
