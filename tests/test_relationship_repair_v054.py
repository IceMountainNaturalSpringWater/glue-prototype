from dataclasses import replace

from glue.analysis.relationships import performance_relations
from glue.analysis.voices import octave_confidence, octave_supported
from glue.fixes.musical import _options, _rhythmic_bundles, generate_musical_repairs, score_passage
from glue.fixes.musical_config import EditPermissions, MusicalWeights, musical_search_for
from scripts.generate_v05_fixtures import clip


def expressive_line():
    return clip([(60 + i % 4, .13 + i / 4 + (i % 2) * .01, .18, 0) for i in range(9)])


def test_expressive_pulse_alternatives_preserve_nonzero_phase_and_clean_input():
    source = expressive_line()
    assert not performance_relations(source)
    damaged = source.with_notes(replace(n, onset_ticks=n.onset_ticks + 60) if n.id == 4 else n
                                for n in source.notes)
    relations = [r for r in performance_relations(damaged) if r.note_id == 4 and r.field == "onset_ticks"]
    assert relations and source.notes[4].onset_ticks in relations[0].values
    assert any(value % 60 != 0 for value in relations[0].values)
    assert performance_relations(damaged) == performance_relations(damaged)
    assert score_passage((damaged,), MusicalWeights()).cost > score_passage((source,), MusicalWeights()).cost


def test_contextual_articulation_candidates_are_bounded_and_permission_gated():
    source = expressive_line()
    damaged = source.with_notes(replace(n, duration_ticks=n.duration_ticks + 240) if n.id == 4 else n
                                for n in source.notes)
    config = musical_search_for("creative")
    assert any(r.note_id == 4 and r.field == "duration_ticks" for r in performance_relations(damaged))
    off = _options((damaged,), (EditPermissions(False, False, False),), (0,), config, None, frozenset(), {})
    assert not off
    on = _options((damaged,), (EditPermissions(False, False, True),), (0,), config, None, frozenset(), {})
    assert any(o.note_id == 4 and o.value == source.notes[4].duration_ticks for o in on)
    result = generate_musical_repairs(damaged, preset="creative", preservation=(100,),
                                     permissions=(EditPermissions(True, True, True),))
    assert not result.candidates


def test_contextual_octave_can_recover_legato_outlier_without_flattening_intentional_high_note():
    source = clip([(p, i * .6, .7, 0) for i, p in
                   enumerate((59, 62, 61, 66, 62, 61, 73, 66, 68, 66, 64))])
    damaged = source.with_notes(replace(n, pitch=n.pitch + 12) if n.id == 1 else n for n in source.notes)
    assert octave_confidence(damaged, damaged.notes[1], 62) >= .8
    assert octave_supported(damaged, damaged.notes[1], 62)
    assert octave_confidence(source, source.notes[6], 61) == 0
    options = _options((damaged,), (EditPermissions(),), (0,), musical_search_for("creative"),
                       None, frozenset(), {})
    assert any(o.note_id == 1 and o.value == 62 for o in options)
    repaired = generate_musical_repairs(damaged, preset="creative", preservation=(0,))
    assert [(e.note_id, e.after.pitch) for e in repaired.candidates[0].edits] == [(1, 62)]
    assert repaired.candidates[0].clips[0] == source


def test_coherent_onset_bundles_use_only_generated_options_and_fixed_limits():
    source = expressive_line()
    damaged = source.with_notes(replace(n, onset_ticks=n.onset_ticks + 60) if n.id == 4 else n
                                for n in source.notes)
    config = musical_search_for("creative")
    options = _options((damaged,), (EditPermissions(True, True, True),), (0,), config, None, frozenset(), {})
    bundles = _rhythmic_bundles((damaged,), options, config.max_edits)
    assert len(bundles) <= 4
    assert all(o in options for bundle in bundles for o in bundle)
    assert all(2 <= len(bundle) <= config.max_edits for bundle in bundles)


def test_compact_chord_register_is_not_an_octave_error_in_an_uncertain_voice():
    source = clip([(p, i * .5, .2, 0) for i, p in enumerate((73, 58, 71, 73, 71, 69, 71, 73, 74))]
                  + [(52, .49, .2, 0), (56, .5, .2, 0)])
    note = next(n for n in source.notes if n.pitch == 58)
    assert octave_confidence(source, note, 70) == 0


def test_short_articulation_consistent_with_neighbors_is_not_normalized():
    source = clip([(60 + i % 3, i / 2, .45, 0) for i in range(7)]
                  + [(64, 3.5, .1, 0), (62, 4, .15, 0), (60, 4.5, .1, 0)])
    assert not any(r.field == "duration_ticks" and r.note_id == 8 for r in performance_relations(source))
