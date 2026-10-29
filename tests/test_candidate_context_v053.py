from dataclasses import replace

from glue.analysis.voices import octave_supported, pitch_supported, voice_identities, voice_paths
from glue.fixes.context_candidates import _templates, context_options
from glue.fixes.musical import generate_musical_repairs
from glue.fixes.musical_config import EditPermissions, musical_search_for
from glue.fixes.search_trace import SearchTrace
from scripts.generate_v05_fixtures import clip, musical_fixtures


def test_spread_chord_attacks_keep_three_register_lines():
    source = clip([(p + step, step + offset, 0.8, 0)
                   for step in range(4) for p, offset in ((48, 0), (60, 0.01), (72, 0.02))])
    paths = voice_paths(source)
    assert len(paths) == 3
    assert all(len(line) == 4 for line in paths)
    identities = voice_identities(source)
    assert {i.role for i in identities} == {"bass", "inner", "upper"}
    assert len({i.note_id for i in identities}) == len(source.notes)
    assert not pitch_supported(source, source.notes[0], 73)


def test_polyphonic_leap_needs_more_than_a_lower_neighbor_for_octave_move():
    source = clip([(60, 0, 1.5, 0), (74, 1, 0.5, 0), (64, 2, 1, 0)])
    assert not octave_supported(source, next(n for n in source.notes if n.pitch == 74), 62)
    mono = clip([(60, 0, 1, 0), (74, 1, 1, 0), (64, 2, 1, 0)])
    assert octave_supported(mono, mono.notes[1], 62)


def test_template_aligns_transposed_phrases_and_multiple_corrupted_fields():
    source = clip([(p, i + 0.375, 0.75, 0)
                   for i, p in enumerate((60, 62, 64, 67, 62, 64, 66, 69))])
    changed = source.with_notes(replace(n, pitch=65, onset_ticks=n.onset_ticks + 60,
                                       duration_ticks=600) if n.id == 5 else n for n in source.notes)
    proposals = _templates(tuple(changed.notes), 5, 480)
    values = {(o.field, o.value) for o in proposals}
    assert {("pitch", 64), ("onset_ticks", 2580), ("duration_ticks", 360)} <= values
    assert all(o.strength == 5 for o in proposals)


def test_context_permissions_bounds_and_microtiming_protection():
    clean = clip([(p, i + 0.375, 0.75, 0) for i, p in enumerate((60, 62, 64, 65, 67, 69, 71))])
    micro = clean.with_notes(replace(n, onset_ticks=n.onset_ticks + 8) if n.id == 3 else n
                            for n in clean.notes)
    config = musical_search_for("creative")
    options = context_options(micro, EditPermissions(True, True, True), config)
    assert not any(o.field != "pitch" for o in options)
    changed = clean.with_notes(replace(n, onset_ticks=n.onset_ticks + 60, duration_ticks=600)
                              if n.id == 3 else n for n in clean.notes)
    options = context_options(changed, EditPermissions(False, True, True), config)
    assert {o.field for o in options} == {"onset_ticks", "duration_ticks"}
    lookup = {n.id: n for n in changed.notes}
    for option in options:
        note = lookup[option.note_id]
        limit = config.onset_beats * 480 if option.field == "onset_ticks" else min(
            config.duration_beats * 480, config.duration_fraction * note.duration_ticks)
        assert abs(option.value - getattr(note, option.field)) <= limit
    assert not context_options(changed, EditPermissions(False, False, False), config)


def test_trace_exposes_voice_original_value_and_candidate_provenance():
    source = musical_fixtures()["pitch_only"]
    observer = SearchTrace()
    result = generate_musical_repairs(source, preservation=(0,), preset="creative", trace=observer)
    assert result.candidates and observer.options
    assert all(o["provenance"] for o in observer.options)
    identities = {n["note_id"]: n for n in observer.note_contexts}
    for edit in result.candidates[0].edits:
        assert identities[edit.note_id]["original_pitch"] == edit.before.pitch
        assert identities[edit.note_id]["role"] in {"single", "bass", "inner", "upper"}


def test_intentional_rhythmic_doubling_alone_generates_no_timing_candidates():
    a = clip([(60, i, 0.5, 0) for i in range(4)])
    b = clip([(67, i, 0.5, 0) for i in range(4)])
    observer = SearchTrace()
    generate_musical_repairs(a, b, preservation=(0, 0), preset="creative",
                             permissions=(EditPermissions(False, True, False),) * 2, trace=observer)
    assert not any(o["field"] == "onset_ticks" for o in observer.options)


def test_comparison_reports_all_unlocked_and_each_preservation_without_pooling():
    from glue.benchmark.corrupt import corrupt
    from glue.benchmark.runner import run_case
    from scripts.compare_candidate_baselines import compare, markdown

    source = musical_fixtures()["pitch_only"]
    corruption = corrupt((source,), "clean")
    rows = []
    for preservation in (0, 100):
        row = run_case((source,), corruption, preset="minimal", preservation=(preservation,),
                       permissions=EditPermissions(), tracing=True)
        row.update(entry="unit", kind="clean", seed=0, corruption_ledger=[])
        rows.append(row)
    result = compare(rows, rows)
    assert result["groups"]["all"]["before"] == result["groups"]["all"]["after"]
    assert result["groups"]["unlocked"]["after"]["runs"] == 1
    assert result["groups"]["preservation_100"]["after"]["clean_false_positive_rate"] == 0
    assert result["groups"]["preservation_0"]["after"]["unnecessary_edits_by_field"]["pitch"] > 0
    assert "unlocked" in markdown({"unit": {"calibration": result}})


def test_linked_bundles_are_bounded_and_join_distinct_fields():
    from glue.fixes.musical import _linked_options, _Option

    options = tuple(_Option(0, note_id, field, value, "proposal", ("motif correspondence",))
                    for note_id in range(20) for field, value in
                    (("pitch", 64), ("pitch", 65), ("onset_ticks", 480), ("duration_ticks", 240)))
    bundles = _linked_options(options)
    assert len(bundles) == 8
    assert all(len({o.field for o in bundle}) == len(bundle) == 3 for bundle in bundles)
    assert bundles == _linked_options(options)


def test_longer_note_before_longer_gap_is_not_articulation_error():
    source = clip([(p, t, d, 0) for p, t, d in
                   ((60, 0, 1), (62, 1, 1), (64, 2, 2), (65, 4, 1),
                    (67, 5, 1), (69, 6, 1), (71, 7, 1))])
    options = context_options(source, EditPermissions(False, False, True), musical_search_for("creative"))
    assert not options


def test_sustain_proposals_include_musical_units_not_only_percentage_endpoints():
    from glue.fixes.musical import _options

    a = clip([(60, 0, 1, 0), (62, 1, 1, 0)])
    b = clip([(61, 0.5, 1.25, 0)])
    options = _options((a, b), (EditPermissions(), EditPermissions(False, False, True)),
                       (100, 0), musical_search_for("creative"), None, frozenset(), {})
    assert any(o.slot == 1 and o.field == "duration_ticks" and o.value == 360 for o in options)


def test_repeated_short_voice_neighbors_are_protected_without_protecting_isolated_errors():
    from glue.analysis.voices import voice_ornaments

    source = clip([(p, i / 2, 0.2, 0) for i, p in enumerate((67, 68, 67, 68, 67, 69, 67))])
    protected = voice_ornaments(source)
    assert {1, 3} <= protected
    assert 5 not in protected
    assert not any(o.field == "pitch" and o.note_id in protected for o in
                   context_options(source, EditPermissions(), musical_search_for("creative")))


def test_coherent_voice_direction_does_not_become_register_excursion():
    source = clip([(p, i, 0.8, 0) for i, p in enumerate((63, 61, 60))])
    assert not pitch_supported(source, source.notes[1], 67)
    assert pitch_supported(source, source.notes[1], 62)


def test_stable_voice_register_is_protected_at_phrase_endpoints():
    source = clip([(p, i, 0.8, 0) for i, p in enumerate((72, 73, 75, 72, 73, 75, 72))])
    assert not pitch_supported(source, source.notes[-1], 67)
    assert not pitch_supported(source, source.notes[1], 79)
    assert pitch_supported(source, source.notes[1], 74)


def test_candidate_order_is_stable_across_python_hash_seeds():
    import os
    import subprocess
    import sys

    program = """
from dataclasses import asdict, replace
import json
from scripts.generate_v05_fixtures import clip
from glue.fixes.context_candidates import context_options
from glue.fixes.musical_config import EditPermissions, musical_search_for
source = clip([(p, i + 0.375, 0.75, 0) for i, p in enumerate((60,62,64,65,67,69,71))])
source = source.with_notes(replace(n, onset_ticks=n.onset_ticks + 60) if n.id == 3 else n
                          for n in source.notes)
print(json.dumps([asdict(o) for o in context_options(source, EditPermissions(True, True, True),
                                                   musical_search_for('creative'))], sort_keys=True))
"""
    outputs = [subprocess.check_output([sys.executable, "-c", program],
               env={**os.environ, "PYTHONHASHSEED": str(seed)}, text=True) for seed in (1, 2, 3)]
    assert len(set(outputs)) == 1
