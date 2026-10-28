"""Reproducible offscreen V0.5 GUI, export, example and profiling validation.

Run as a module from the repository; all generated artifacts stay in --output-dir.
No audio/listening judgment is claimed by these deterministic demonstrations.
"""

from __future__ import annotations

import argparse
import cProfile
import json
import os
import pstats
from dataclasses import asdict, replace
from pathlib import Path
from time import perf_counter

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication, QMessageBox

from glue.analysis.musical import analyze_musical, infer_harmony
from glue.fixes.musical import generate_musical_repairs
from glue.fixes.musical_config import EditPermissions
from glue.io import load_midi
from glue.io.edited import note_semantics
from glue.ui import MainWindow
from scripts.generate_v05_fixtures import generate


def validate(output: Path, *, profile: bool = False) -> list[dict]:
    paths = generate(output / "fixtures")
    app = QApplication.instance() or QApplication([])
    # Windows' offscreen plugin cannot enumerate installed fonts. Load an
    # existing OS font for screenshot QA only; the normal desktop is unchanged.
    if not QFontDatabase.families():
        font_path = Path("C:/Windows/Fonts/segoeui.ttf")
        if font_path.is_file():
            ident = QFontDatabase.addApplicationFont(str(font_path))
            families = QFontDatabase.applicationFontFamilies(ident)
            if families:
                app.setFont(QFont(families[0], 9))
    window = MainWindow()
    window.resize(1200, 850)
    window.show()
    records = []

    def fail_dialog(_parent, _title, message, *args):
        raise RuntimeError(message)

    QMessageBox.critical = fail_dialog
    try:
        for label, left, right, permissions, expected in (
            ("pitch-only", "pitch_only", None, EditPermissions(), (True, False, False)),
            (
                "timing-only",
                "rhythmic_collision_a",
                "rhythmic_collision_b",
                EditPermissions(False, True, False),
                (False, True, False),
            ),
            (
                "duration-only",
                "sustain_conflict_a",
                "sustain_conflict_b",
                EditPermissions(False, False, True),
                (False, False, True),
            ),
            (
                "pitch-timing",
                "pitch_timing_a",
                "pitch_timing_b",
                EditPermissions(True, True, False),
                (True, True, False),
            ),
            (
                "pitch-duration",
                "pitch_duration_a",
                "pitch_duration_b",
                EditPermissions(True, False, True),
                (True, False, True),
            ),
        ):
            if right:
                window.select_combine_workflow()
                window.load_clip("A", paths[left])
                window.load_clip("B", paths[right])
                window.set_preservation_values(100, 0)
                host, panel, button, slot = window, window.musical_controls, window.repair_button, 1
            else:
                window.load_single_clip(paths[left])
                host = window.polish_page
                host.set_preservation(0)
                panel, button, slot = host.musical_controls, host.generate_button, 0
            host.preset_combo.setCurrentIndex(2)
            for check, allowed in zip(
                panel.checks[slot], asdict(permissions).values(), strict=True
            ):
                check.setChecked(allowed)
            started = perf_counter()
            button.click()
            elapsed = perf_counter() - started
            result, candidate = panel.result, panel.candidate
            assert result and candidate, label
            assert tuple(c > 0 for c in candidate.counts) == expected, label
            assert candidate.score.estimate > result.before.estimate
            output_file = panel.export(output / f"{label}.mid", slot=slot)
            assert note_semantics(load_midi(output_file).clip) == note_semantics(
                candidate.clips[slot]
            )
            panel.export(output / f"{label}.json", report=True)
            records.append(
                {
                    "case": label,
                    "before": result.before.estimate,
                    "after": candidate.score.estimate,
                    "counts": candidate.counts,
                    "evaluations": result.evaluations,
                    "seconds": elapsed,
                    "edits": [asdict(e) for e in candidate.edits],
                }
            )
            panel.rationale_toggle.setChecked(True)
            app.processEvents()
            window.grab().save(str(output / f"{label}.png"))
        panel.export(output / "pair-bundle", bundle=True)
        for name in ("chromatic_passing", "suspension", "intentional_syncopation"):
            window.load_single_clip(paths[name])
            page = window.polish_page
            page.set_preservation(0)
            page.preset_combo.setCurrentIndex(2)
            for check in page.musical_controls.checks[0]:
                check.setChecked(True)
            result = page.repair_musical()
            assert not result.candidates, name
            records.append({"case": name, "edits": [], "explanation": result.stop_reason})
        app.processEvents()
        window.grab().save(str(output / "intentional-material.png"))
        if profile:
            clips = tuple(load_midi(paths[n]).clip for n in ("budget_a", "budget_b"))
            analyze_musical.cache_clear()
            infer_harmony.cache_clear()
            profiler = cProfile.Profile()
            profiler.enable()
            result = generate_musical_repairs(*clips, preservation=(100, 0), preset="creative")
            profiler.disable()
            profiler.dump_stats(output / "search.prof")
            with (output / "profile.txt").open("w", encoding="utf-8") as stream:
                pstats.Stats(profiler, stream=stream).strip_dirs().sort_stats(
                    "cumtime"
                ).print_stats(20)
            started = perf_counter()
            warm = generate_musical_repairs(*clips, preservation=(100, 0), preset="creative")
            records.append(
                {
                    "case": "warm-search",
                    "notes": [len(c.notes) for c in clips],
                    "seconds": perf_counter() - started,
                    "evaluations": warm.evaluations,
                    "deterministic": warm == result,
                }
            )
            dense = tuple(
                replace(
                    c,
                    length_ticks=32 * c.ticks_per_beat,
                    tracks=tuple(replace(t, length_ticks=32 * c.ticks_per_beat) for t in c.tracks),
                    notes=tuple(
                        replace(
                            n,
                            id=i * len(c.notes) + j,
                            onset_ticks=n.onset_ticks + i * 8 * c.ticks_per_beat,
                        )
                        for i in range(4)
                        for j, n in enumerate(c.notes)
                    ),
                )
                for c in clips
            )
            started = perf_counter()
            larger = generate_musical_repairs(*dense, preservation=(100, 0), preset="creative")
            records.append(
                {
                    "case": "larger-search",
                    "notes": [len(c.notes) for c in dense],
                    "seconds": perf_counter() - started,
                    "evaluations": larger.evaluations,
                    "candidates": len(larger.candidates),
                    "stop_reason": larger.stop_reason,
                }
            )
        (output / "validation.json").write_text(
            json.dumps(records, indent=2) + "\n", encoding="utf-8"
        )
        print("GLUE_V05_SINGLE_PAIR_EXPORT_SMOKE_OK")
        for record in records:
            print({k: v for k, v in record.items() if k != "edits"})
        return records
    finally:
        window.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(".test-tmp/v05-validation"))
    parser.add_argument("--profile", action="store_true")
    args = parser.parse_args()
    validate(args.output_dir, profile=args.profile)
