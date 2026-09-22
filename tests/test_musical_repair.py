from dataclasses import replace

import pytest

from glue.fixes.musical import generate_musical_repairs, score_passage
from glue.fixes.musical_config import EditPermissions, MusicalWeights, musical_search_for
from glue.io import load_midi
from glue.io.edited import note_semantics
from glue.musical_exporting import export_musical_candidate
from scripts.generate_v05_fixtures import generate, musical_fixtures


@pytest.mark.parametrize(
    "kind,a,b,permissions",
    [
        (0, "pitch_only", None, EditPermissions()),
        (1, "rhythmic_collision_a", "rhythmic_collision_b", EditPermissions(False, True, False)),
        (2, "sustain_conflict_a", "sustain_conflict_b", EditPermissions(False, False, True)),
    ],
)
def test_independent_edit_types_improve_and_export(kind, a, b, permissions, tmp_path):
    paths = generate(tmp_path)
    docs = tuple(load_midi(paths[name]) for name in (a, b) if name)
    params = {
        "permissions": (EditPermissions(False, False, False), permissions) if b else (permissions,),
        "preservation": (100, 0) if b else (0,),
        "preset": "creative",
    }
    result = generate_musical_repairs(*(d.clip for d in docs), **params)
    assert result == generate_musical_repairs(*(d.clip for d in docs), **params)
    assert result.candidates
    candidate = result.candidates[0]
    assert candidate.score.estimate > result.before.estimate
    assert candidate.counts[kind] > 0
    assert all(not count for index, count in enumerate(candidate.counts) if index != kind)
    slot = len(docs) - 1
    output = export_musical_candidate(result, candidate, docs, tmp_path / "repaired.mid", slot=slot)
    assert note_semantics(load_midi(output).clip) == note_semantics(candidate.clips[slot])
    report = export_musical_candidate(
        result, candidate, docs, tmp_path / "report.json", report=True
    )
    assert "reasons" in report.read_text()
    for edit in candidate.edits:
        assert edit.reasons
        assert (
            abs(edit.after.onset_ticks - edit.before.onset_ticks) / 480 <= result.config.onset_beats
        )
        assert (
            abs(edit.after.duration_ticks - edit.before.duration_ticks) / 480
            <= result.config.duration_beats
        )
        assert edit.after.duration_ticks > 0
    with pytest.raises(ValueError, match="source"):
        export_musical_candidate(result, candidate, docs, docs[0].source_path, overwrite=True)


def test_permissions_hard_locks_and_distinct_bounds():
    clip = musical_fixtures()["pitch_only"]
    for preset in ("minimal", "balanced", "creative"):
        assert not generate_musical_repairs(clip, preset=preset).candidates
        assert not generate_musical_repairs(
            clip,
            preservation=(0,),
            preset=preset,
            permissions=(EditPermissions(False, False, False),),
        ).candidates
    configs = [musical_search_for(p) for p in ("minimal", "balanced", "creative")]
    for name in ("max_edits", "note_pool", "pitch_range", "beam", "depth", "evaluations"):
        assert getattr(configs[0], name) < getattr(configs[1], name) < getattr(configs[2], name)


def test_intentional_material_is_preserved():
    fixtures = musical_fixtures()
    for name in (
        "chromatic_passing",
        "suspension",
        "secondary_dominant",
        "intentional_syncopation",
    ):
        result = generate_musical_repairs(
            fixtures[name],
            preservation=(0,),
            preset="creative",
            permissions=(EditPermissions(True, True, True),),
        )
        assert not result.candidates, (name, result.candidates)


def test_coordinated_and_diverse_candidates():
    fixtures = musical_fixtures()
    result = generate_musical_repairs(
        fixtures["pitch_timing_a"],
        fixtures["pitch_timing_b"],
        preservation=(100, 0),
        permissions=(EditPermissions(False, False, False), EditPermissions(True, True, True)),
        preset="creative",
    )
    assert any(sum(count > 0 for count in c.counts) >= 2 for c in result.candidates)
    assert 1 < len(result.candidates) <= 3
    assert len(
        {tuple((e.slot, e.note_id, e.kinds) for e in c.edits) for c in result.candidates}
    ) == len(result.candidates)
    for candidate in result.candidates:
        assert candidate.score == score_passage(candidate.clips, result.config.weights)
        assert candidate.clips[0] == result.originals[0]


def test_motif_damage_is_not_erased_at_zero_preservation():
    from glue.fixes.musical import _retention

    clip = musical_fixtures()["intentional_syncopation"]
    changed = clip.with_notes(replace(n, pitch=n.pitch + 1) if n.id < 3 else n for n in clip.notes)
    assert _retention((clip,), (changed,), MusicalWeights()) == float("inf")


def test_presets_and_preservation_allow_progressively_broader_passages():
    f = musical_fixtures()
    results = [
        generate_musical_repairs(f["budget_a"], f["budget_b"], preservation=(100, 0), preset=p)
        for p in ("minimal", "balanced", "creative")
    ]
    counts = [len(r.candidates[0].edits) for r in results]
    assert counts[0] < counts[1] < counts[2]
    assert all(r.candidates[0].edit_cost == 0 for r in results)
    high = generate_musical_repairs(
        f["budget_a"], f["budget_b"], preservation=(100, 90), preset="creative"
    )
    high_count = len(high.candidates[0].edits) if high.candidates else 0
    assert high_count < counts[-1]
    assert all(r.evaluations <= r.config.evaluations for r in (*results, high))


@pytest.mark.parametrize(
    "left,right,kinds",
    [
        ("pitch_timing_a", "pitch_timing_b", (True, True, False)),
        ("pitch_duration_a", "pitch_duration_b", (True, False, True)),
    ],
)
def test_best_coordinated_repairs_beat_each_restricted_search(left, right, kinds):
    f = musical_fixtures()

    def run(allow):
        return generate_musical_repairs(
            f[left],
            f[right],
            preservation=(100, 0),
            permissions=(EditPermissions(), allow),
            preset="creative",
        )

    coordinated = run(EditPermissions(*kinds))
    best = coordinated.candidates[0]
    assert tuple(c > 0 for c in best.counts) == kinds
    for i, enabled in enumerate(kinds):
        if enabled:
            restricted = list(kinds)
            restricted[i] = False
            result = run(EditPermissions(*restricted))
            score = (
                result.candidates[0].score.estimate if result.candidates else result.before.estimate
            )
            assert best.score.estimate > score


def test_timing_can_win_without_pitch_changes_and_preserve_call_response_order():
    f = musical_fixtures()
    result = generate_musical_repairs(
        f["timing_over_pitch_a"],
        f["timing_over_pitch_b"],
        preservation=(100, 0),
        preset="creative",
        permissions=(EditPermissions(), EditPermissions(True, True, True)),
    )
    best = result.candidates[0]
    assert best.counts == (0, 3, 0)
    before = dict(result.before.components)["Rhythm complementarity"]
    assert dict(best.score.components)["Rhythm complementarity"] < before
    assert all(e.after.onset_ticks > e.before.onset_ticks for e in best.edits)
    assert [n.pitch for n in best.clips[1].notes] == [n.pitch for n in f["call_response_b"].notes]


def test_search_keeps_non_improving_intermediates(monkeypatch):
    """A deliberate objective barrier verifies coordinated search, not greed."""
    import glue.fixes.musical as engine

    f = musical_fixtures()
    target = f["pitch_timing_b"]

    def barrier(clips, weights):
        moved = sum(
            a.onset_ticks != b.onset_ticks
            for a, b in zip(target.notes, clips[1].notes, strict=True)
        )
        return engine.MusicalScore(
            (("test barrier", float(moved)),), 10 if moved == 0 else 11 if moved == 1 else 0
        )

    monkeypatch.setattr(engine, "score_passage", barrier)
    result = engine.generate_musical_repairs(
        f["pitch_timing_a"],
        target,
        permissions=(EditPermissions(), EditPermissions(False, True, False)),
        preservation=(100, 0),
        preset="creative",
    )
    assert result.candidates[0].counts == (0, 2, 0)
    assert result.candidates[0].score.cost == 0


def test_minimal_timing_and_duration_require_explicit_technical_repair_permission():
    from scripts.generate_v05_fixtures import clip

    source = clip([(60, 0, 1, 0), (60, 0.875, 0.5, 0)])
    for permission, field in (
        (EditPermissions(False, True, False), 1),
        (EditPermissions(False, False, True), 2),
    ):
        result = generate_musical_repairs(
            source, preservation=(0,), preset="minimal", permissions=(permission,)
        )
        assert result.candidates[0].counts[field] == 1
        assert dict(result.candidates[0].score.components)["Collisions"] == 0


def test_timing_limits_are_beat_based_at_different_ppq_and_tempo():
    from glue.models import TempoChange

    f = musical_fixtures()
    clips = (f["rhythmic_collision_a"], f["rhythmic_collision_b"])
    scaled = tuple(
        replace(
            c,
            ticks_per_beat=960,
            length_ticks=c.length_ticks * 2,
            notes=tuple(
                replace(n, onset_ticks=n.onset_ticks * 2, duration_ticks=n.duration_ticks * 2)
                for n in c.notes
            ),
            tracks=tuple(replace(t, length_ticks=t.length_ticks * 2) for t in c.tracks),
            tempo_changes=(TempoChange(0, 750_000),),
        )
        for c in clips
    )
    results = [
        generate_musical_repairs(
            *pair,
            preservation=(100, 0),
            preset="balanced",
            permissions=(EditPermissions(), EditPermissions(False, True, False)),
        )
        for pair in (clips, scaled)
    ]
    movements = [
        tuple(
            (e.after.onset_ticks - e.before.onset_ticks) / r.originals[e.slot].ticks_per_beat
            for e in r.candidates[0].edits
        )
        for r in results
    ]
    assert movements[0] == movements[1]
    assert all(abs(d) <= 0.25 for d in movements[0])


def test_duration_can_extend_an_isolated_gap_without_normalizing_a_line():
    source = musical_fixtures()["legato_gap"]
    result = generate_musical_repairs(
        source,
        preservation=(0,),
        preset="balanced",
        permissions=(EditPermissions(False, False, True),),
    )
    best = result.candidates[0]
    assert best.counts == (0, 0, 1)
    edit = best.edits[0]
    assert edit.note_id == 1 and edit.after.duration_ticks - edit.before.duration_ticks == 60
    assert best.score.estimate > result.before.estimate
    assert edit.after.onset_ticks == edit.before.onset_ticks


def test_repeated_motif_accidental_has_contextual_repair_and_qualified_reason():
    source = musical_fixtures()["motif_accidental"]
    result = generate_musical_repairs(source, preservation=(0,), preset="creative")
    best = result.candidates[0]
    assert [(e.note_id, e.before.pitch, e.after.pitch) for e in best.edits] == [(6, 65, 64)]
    assert best.score.estimate > result.before.estimate
    assert "variation may be intentional" in " ".join(best.edits[0].reasons)


def test_complete_contour_destruction_and_new_line_collapse_are_rejected():
    from glue.fixes.musical import _retention
    from scripts.generate_v05_fixtures import clip

    a = clip([(p, i, 0.5, 0) for i, p in enumerate((60, 62, 64, 67))])
    b = a.with_notes(replace(n, pitch=n.pitch + 2) for n in a.notes)
    flat = a.with_notes(replace(n, pitch=60) for n in a.notes)
    assert _retention((a,), (flat,), MusicalWeights()) == float("inf")
    assert _retention((a, b), (a, a), MusicalWeights()) == float("inf")
    shortened = a.with_notes(replace(n, duration_ticks=n.duration_ticks // 2) for n in a.notes)
    assert _retention((a, b), (a, shortened), MusicalWeights()) == float("inf")
    assert _retention((a, a), (a, a), MusicalWeights()) == 0  # Existing doubling is retained.


def test_seventh_chord_split_across_two_files_is_not_a_pitch_or_timing_mistake():
    from scripts.generate_v05_fixtures import clip

    bass = clip([(60, 0, 2, 0)])
    upper = clip([(p, 0, 2, 0) for p in (64, 67, 71)])
    result = generate_musical_repairs(
        bass,
        upper,
        preservation=(100, 0),
        preset="creative",
        permissions=(EditPermissions(), EditPermissions(True, True, True)),
    )
    assert not result.candidates
    assert dict(result.before.components)["Rhythm complementarity"] == 0


def test_single_suggestion_pitch_choices_are_constraints_not_just_note_selection():
    source = musical_fixtures()["pitch_only"]
    ident = next(n.id for n in source.notes if n.pitch == 78)
    result = generate_musical_repairs(
        source, preservation=(0,), preset="creative", pitch_choices={ident: frozenset({76})}
    )
    assert result.candidates
    assert all(e.after.pitch == 76 for c in result.candidates for e in c.edits)
    assert not generate_musical_repairs(
        source, preservation=(0,), preset="creative", pitch_choices={ident: frozenset()}
    ).candidates
