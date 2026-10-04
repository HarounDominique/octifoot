---
slug: run-control
spec: SPEC-run-control.md
status: draft
---

## Implementation Roadmap

Routing: standard (several modules, a new threading concern).

- [ ] Phase 1 — Run registry (`runs.py`) and `should_stop` in the client (satisfies: SPEC-run-control.md#objective)
- [ ] Phase 2 — Connector loop: register the run, stop handling, skipped targets, notes, snapshot, work message (satisfies: SPEC-run-control.md#objective)
- [ ] Phase 3 — Panel: status block with refresh, `/stop`, strings en/es, audit (satisfies: SPEC-run-control.md#objective)
- [ ] Phase 4 — Panel: `/run`, launcher (observable find/create + ask enrichment), duplicate guard (satisfies: SPEC-run-control.md#objective, SPEC-run-control.md#boundaries)
- [ ] Phase 5 — Docs, live check (start, stop, start again), reflect, archive, merge (satisfies: SPEC-run-control.md#test-strategy)

## Execution State

**Build Status**: NOT_STARTED
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
**Last Block Rule**: none
**Can Resume**: YES

## Deviations

[none yet]
