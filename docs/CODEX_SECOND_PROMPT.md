# Second prompt after V0.1 works

Review the current implementation against `docs/PRODUCT_SPEC.md`. Do not rewrite working modules gratuitously.

Now harden GLUE V0.1 into a demo-ready prototype:

1. Find weak or under-tested analysis assumptions and add focused regression tests.
2. Improve local harmony inference so two clips in the same global key can still be identified as locally conflicting.
3. Add three repair presets:
   - Minimal: pitch changes only, rhythm completely locked, high edit penalty.
   - Balanced: pitch + octave changes, moderate edit penalty.
   - Creative: wider pitch search and reharmonization candidates, but still no destructive source-file edits.
4. Add a user-adjustable preservation slider that changes the edit penalty.
5. Make conflict explanations human-readable and specific, e.g. identify the window and which pitch classes/root implications drive the low score.
6. Add before/after comparison in the piano roll and timeline.
7. Improve error handling for malformed/empty MIDI files.
8. Add `ruff`-clean code and keep all tests passing.
9. Create a polished demo fixture set generated entirely by code.
10. Do a final end-to-end test and document limitations honestly.

Do not add audio support, VST support, accounts, or AI generation yet.
