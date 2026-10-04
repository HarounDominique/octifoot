---
slug: iterative-scan-loop
spec: SPEC-iterative-scan-loop.md
status: approved
---

## Implementation Roadmap

Routing: standard (4 source files, design fixed in spec).

- [ ] Phase 1 — Config + discovery + planner: `max_depth`/`max_scans` in config, `MapResult.discovered_domains`, pure `expansion.plan_next` (satisfies: SPEC-iterative-scan-loop.md#objective, SPEC-iterative-scan-loop.md#style)
- [ ] Phase 2 — Connector loop: breadth-first scans, merged bundle, failure tolerance, summary (satisfies: SPEC-iterative-scan-loop.md#objective, SPEC-iterative-scan-loop.md#boundaries)
- [ ] Phase 3 — Deploy + docs: compose/.env variables, README section (satisfies: SPEC-iterative-scan-loop.md#commands)

## Execution State

**Build Status**: NOT_STARTED
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {2: 0, 3: 0, 4: 0}
**Last Block Rule**: none
**Can Resume**: YES

## Deviations

[Anything a build phase did differently from what the spec/plan predicted, and whether
it was accepted, and by whom.]
