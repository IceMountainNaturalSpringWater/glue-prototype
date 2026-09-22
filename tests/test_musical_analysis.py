from glue.analysis.musical import analyze_musical, infer_harmony, metric_strength
from scripts.generate_v05_fixtures import musical_fixtures


def test_harmony_sequence_and_context_are_deterministic_and_bounded():
    clip = musical_fixtures()["secondary_dominant"]
    result = analyze_musical(clip)
    assert result == analyze_musical(clip)
    assert len(result.frames) == 4
    assert any(
        f.harmony.root == 2 and f.harmony.quality == "dominant seventh" and f.tonicization
        for f in result.frames
    )
    assert all(0 <= f.confidence <= 1 and len(f.alternatives) <= 8 for f in result.frames)
    assert infer_harmony(clip) == result.frames
    assert infer_harmony.cache_info().hits > 0


def test_passing_suspension_and_syncopation_are_contextual():
    fixtures = musical_fixtures()
    passing = analyze_musical(fixtures["chromatic_passing"])
    assert any(n.function == "passing tone" and n.protected for n in passing.notes)
    suspended = analyze_musical(fixtures["suspension"])
    assert any(
        n.function == "suspension" and n.resolution_note is not None for n in suspended.notes
    )
    sync = analyze_musical(fixtures["intentional_syncopation"])
    assert sync.syncopation == 1
    assert sync.motifs and sync.motifs[0].rhythmic_match
    assert metric_strength(fixtures["suspension"], 0) > metric_strength(fixtures["suspension"], 240)


def test_inversion_neighbor_anticipation_and_phrase_evidence():
    from scripts.generate_v05_fixtures import clip

    inverted = clip([(p, 0, 2, 0) for p in (52, 55, 60)])
    assert analyze_musical(inverted).frames[0].harmony.label == "C major/E"
    neighbor = clip(
        [(p, 0, 4, 0) for p in (48, 52, 55)] + [(60, 0, 0.5, 1), (62, 0.5, 0.5, 1), (60, 1, 1, 1)]
    )
    assert any(
        n.function == "neighbor tone" and n.protected for n in analyze_musical(neighbor).notes
    )
    anticipation = clip([(62, 0, 0.5, 0), (64, 0.5, 0.5, 0), (64, 1, 1, 0)])
    assert any(n.function == "anticipation" for n in analyze_musical(anticipation).notes)
    phrase = clip([(60, 0, 0.5, 0), (62, 2, 0.5, 0), (64, 3, 0.5, 0)])
    model = analyze_musical(phrase)
    assert model.phrase_boundaries == (0, 2)
    assert model.notes[0].phrase == 0 and model.notes[-1].phrase == 1


def test_voice_motion_rhythmic_motifs_and_overlap_evidence():
    from scripts.generate_v05_fixtures import clip

    chords = clip([(48, 0, 1, 0), (55, 0, 1, 0), (50, 1, 1, 0), (57, 1, 1, 0)])
    model = analyze_musical(chords)
    assert model.parallel_motion == 1
    assert model.voice_leading == model.bass_motion == 2
    assert len(model.overlaps) == 2 and not model.collisions
    rhythm = clip([(p, i + 0.5, 0.25, 0) for i, p in enumerate((60, 61, 62, 63, 64, 67, 69, 71))])
    model = analyze_musical(rhythm)
    assert model.rhythmic_motifs and not model.motifs
    assert model.syncopation == 1


def test_sequence_is_bounded_and_weak_evidence_stays_ambiguous():
    from glue.models import MidiClip
    from scripts.generate_v05_fixtures import clip

    sustained = clip([(60, 0, 300, 0)])
    frames = infer_harmony(sustained)
    assert len(frames) <= 128 and frames[-1].end == 300
    silence = MidiClip(480, length_ticks=1920)
    frames = infer_harmony(silence)
    assert frames and all(f.confidence < 0.5 for f in frames)
