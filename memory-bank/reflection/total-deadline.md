# Reflection: total-deadline

Spec: [SPEC-total-deadline.md](../specs/SPEC-total-deadline.md) · Date: 2026-10-04

## Implementation vs spec

All criteria met: `SPIDERFOOT_MAX_TOTAL_SECONDS` (60-86400, default 3600); each scan gets `min(per-scan, time left)`; no scan starts under 60 s left; skipped targets named in the expansion Note and as `deadline_skipped=N`; snapshot incomplete on skips; early bundle after each non-last scan (new objects only), final bundle complete; applied time reported; panel `/total` (60-14400, audited); single-scan runs send one bundle.
Live (zonetransfer.me, total 150 s): the root scan was given 150 s, `www.zonetransfer.me` was named `Skipped, total time limit reached (150 s)`, work completed in about 155 s, early bundle arrived about 1 s before the final one.

## Deviations

- Spec said "more scans queued"; one test written from memory expected 4 sends for 3 scans (early after the last too). The test was wrong, not the spec: fixed to 3.
- Two sloppy test lines (`... or True`, a stray assignment) written during the previous context were found by lint and removed.

## Workflow

- Routing "standard" fit. Spec/tests-first worked: 16 failing tests guided the loop change; the only surprise was an old test asserting one send.
- Weakness: the live check did not exercise the early bundle across a long run (a root-only run under a tight total); the unit tests with a fake clock cover the ordering.

## Rules extracted

- inject-the-clock-for-deadlines (code-editing)
- a-test-written-from-memory-can-be-the-wrong-one (code-editing)
