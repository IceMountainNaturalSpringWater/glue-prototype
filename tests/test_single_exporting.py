from __future__ import annotations

import json
from pathlib import Path

import mido
import pytest

import glue.fixes.single as single_module
from glue.analysis import (
    KeyEstimate,
    SingleAnalysisConfig,
    SingleClipAnalysis,
    SingleClipSuggestion,
    SingleSuggestionCategory,
)
from glue.fixes import RepairPreset, generate_single_repair
from glue.io import load_midi
from glue.models import MidiClip
from glue.single_exporting import (
    SingleRepairExportError,
    build_single_change_report,
    export_single_change_report,
    export_single_repaired_midi,
    serialize_single_change_report,
)


def _write_source(path: Path) -> Path:
    midi = mido.MidiFile(type=1, ticks_per_beat=480)
    track = mido.MidiTrack()
    midi.tracks.append(track)
    track.append(mido.MetaMessage("track_name", name="Source events", time=0))
    track.append(mido.MetaMessage("set_tempo", tempo=510_000, time=0))
    track.append(
        mido.MetaMessage(
            "time_signature",
            numerator=3,
            denominator=4,
            time=0,
        )
    )
    track.append(mido.Message("program_change", channel=0, program=42, time=0))
    track.append(
        mido.Message(
            "control_change",
            channel=0,
            control=64,
            value=127,
            time=0,
        )
    )
    track.append(mido.Message("note_on", channel=0, note=60, velocity=91, time=0))
    track.append(mido.Message("note_off", channel=0, note=60, velocity=7, time=480))
    track.append(
        mido.Message(
            "control_change",
            channel=0,
            control=64,
            value=0,
            time=0,
        )
    )
    track.append(mido.Message("note_on", channel=0, note=64, velocity=73, time=0))
    track.append(mido.Message("note_off", channel=0, note=64, velocity=3, time=480))
    track.append(mido.MetaMessage("marker", text="keep", time=0))
    track.append(mido.MetaMessage("end_of_track", time=0))
    midi.save(filename=path)
    return path


def _analysis(
    clip: MidiClip,
    score: float,
) -> SingleClipAnalysis:
    note = clip.notes[0]
    suggestion = SingleClipSuggestion(
        suggestion_id="export:test",
        target_note_id=note.id,
        related_note_ids=(),
        original_pitch=note.pitch,
        onset_ticks=note.onset_ticks,
        duration_ticks=note.duration_ticks,
        track=note.track,
        channel=note.channel,
        onset_beats=0.0,
        duration_beats=1.0,
        category=SingleSuggestionCategory.HARMONIC_CONFLICT,
        confidence=0.95,
        explanation="Possible harmonic conflict.",
        alternatives=(note.pitch + 1,),
    )
    return SingleClipAnalysis(
        key=KeyEstimate.unknown(),
        harmonic_score=score,
        melodic_score=score,
        voice_leading_score=score,
        overlap_score=score,
        register_score=score,
        bass_score=score,
        motif_score=score,
        internal_consistency_score=score,
        suggestions=(suggestion,),
    )


def _repair(
    monkeypatch: pytest.MonkeyPatch,
    clip: MidiClip,
) -> object:
    before = _analysis(clip, 50.0)

    def scorer(
        candidate: MidiClip,
        *,
        config: SingleAnalysisConfig,
    ) -> SingleClipAnalysis:
        del config
        return _analysis(
            clip,
            80.0 if candidate.notes[0].pitch == 61 else 50.0,
        )

    monkeypatch.setattr(single_module, "analyze_single_clip", scorer)
    return generate_single_repair(
        clip,
        analysis=before,
        preset=RepairPreset.MINIMAL,
        preservation=0,
    )


def _message_dicts(path: Path) -> tuple[tuple[dict[str, object], ...], ...]:
    midi = mido.MidiFile(filename=path)
    return tuple(
        tuple(message.dict() for message in track) for track in midi.tracks
    )


def test_single_midi_export_reopens_and_preserves_every_unrelated_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _write_source(tmp_path / "source.mid")
    source_bytes = source.read_bytes()
    document = load_midi(source)
    repair = _repair(monkeypatch, document.clip)
    output = tmp_path / "repaired.mid"

    exported = export_single_repaired_midi(repair, document, output)

    assert exported == output
    assert source.read_bytes() == source_bytes
    reloaded = load_midi(output)
    assert [note.pitch for note in reloaded.clip.notes] == [61, 64]
    assert [
        (
            note.onset_ticks,
            note.duration_ticks,
            note.velocity,
            note.release_velocity,
            note.track,
            note.channel,
        )
        for note in reloaded.clip.notes
    ] == [
        (
            note.onset_ticks,
            note.duration_ticks,
            note.velocity,
            note.release_velocity,
            note.track,
            note.channel,
        )
        for note in document.clip.notes
    ]

    changed_references = {
        (reference.track, reference.event_index)
        for reference in (
            document.bindings[0].note_on,
            document.bindings[0].note_off,
        )
    }
    before = _message_dicts(source)
    after = _message_dicts(output)
    for track_index, (source_track, repaired_track) in enumerate(
        zip(before, after, strict=True)
    ):
        for event_index, (source_message, repaired_message) in enumerate(
            zip(source_track, repaired_track, strict=True)
        ):
            changed = {
                field
                for field in source_message.keys() | repaired_message.keys()
                if source_message.get(field) != repaired_message.get(field)
            }
            assert changed == (
                {"note"}
                if (track_index, event_index) in changed_references
                else set()
            )


def test_single_advanced_json_is_deterministic_traceable_and_source_safe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = load_midi(_write_source(tmp_path / "source.mid"))
    repair = _repair(monkeypatch, document.clip)
    report = build_single_change_report(repair, document)
    expected = serialize_single_change_report(report)
    output = tmp_path / "advanced.json"

    exported = export_single_change_report(repair, document, output)

    assert exported.read_bytes() == expected
    assert serialize_single_change_report(
        build_single_change_report(repair, document)
    ) == expected
    parsed = json.loads(output.read_text(encoding="utf-8"))
    assert parsed["workflow"] == "polish-one-clip"
    assert parsed["preset"] == "minimal"
    assert parsed["changed_note_count"] == 1
    assert parsed["enabled_suggestion_ids"] == ["export:test"]
    assert parsed["changed_notes"] == [
        {
            "note_id": 0,
            "track": 0,
            "channel": 0,
            "original_pitch": 60,
            "revised_pitch": 61,
            "onset_ticks": 0,
            "duration_ticks": 480,
            "suggestion_ids": ["export:test"],
            "suggestion_categories": ["harmonic-conflict"],
        }
    ]

    with pytest.raises(
        SingleRepairExportError,
        match="Refusing to overwrite the loaded source",
    ):
        export_single_change_report(
            repair,
            document,
            document.source_path,
        )


def test_single_export_protects_source_existing_outputs_and_no_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = load_midi(_write_source(tmp_path / "source.mid"))
    repair = _repair(monkeypatch, document.clip)
    existing = tmp_path / "existing.mid"
    existing.write_bytes(b"keep")

    with pytest.raises(
        SingleRepairExportError,
        match="Refusing to overwrite the loaded source",
    ):
        export_single_repaired_midi(
            repair,
            document,
            document.source_path,
        )
    with pytest.raises(
        SingleRepairExportError,
        match="existing export",
    ):
        export_single_repaired_midi(repair, document, existing)
    assert existing.read_bytes() == b"keep"

    export_single_repaired_midi(
        repair,
        document,
        existing,
        overwrite=True,
    )
    assert load_midi(existing).clip.notes[0].pitch == 61

    locked = generate_single_repair(
        document.clip,
        analysis=_analysis(document.clip, 50.0),
        preservation=100,
    )
    with pytest.raises(
        SingleRepairExportError,
        match="No improving repair",
    ):
        export_single_repaired_midi(
            locked,
            document,
            tmp_path / "unchanged.mid",
        )
