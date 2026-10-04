---
slug: iterative-scan-loop
spec: SPEC-iterative-scan-loop.md
status: approved
---

## Implementation Roadmap

Routing: standard (4 source files, design fixed in spec).

- [x] Phase 1 — Config + discovery + planner: `max_depth`/`max_scans` in config, `MapResult.discovered_domains`, pure `expansion.plan_next` (satisfies: SPEC-iterative-scan-loop.md#objective, SPEC-iterative-scan-loop.md#style)
- [x] Phase 2 — Connector loop: breadth-first scans, merged bundle, failure tolerance, summary (satisfies: SPEC-iterative-scan-loop.md#objective, SPEC-iterative-scan-loop.md#boundaries)
- [x] Phase 3 — Deploy + docs: compose/.env variables, README section (satisfies: SPEC-iterative-scan-loop.md#commands)

## Execution State

**Build Status**: DONE
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {2: 0, 3: 0, 4: 0}
**Last Block Rule**: none
**Can Resume**: YES

## Deviations

[Anything a build phase did differently from what the spec/plan predicted, and whether
it was accepted, and by whom.]
- Live check (2026-10-04) of this and the previous iteration found a bug in `risk-signal-mapping`, already merged: per-feed external references (`source_name` = feed, `description` only) were silently dropped by OpenCTI, which requires `external_id` or `url`. The label `spiderfoot:malicious` did arrive. Fixed on this branch by adding `external_id=scan_id` to feed references, with a regression test (`test_feed_references_carry_external_id_so_opencti_keeps_them`). Unit tests could not catch it because they assert the generated object, not what OpenCTI accepts.
- Live run with `SPIDERFOOT_MAX_DEPTH=1` on `registrolineas.com`: one scan, no subdomains discovered (domain is behind Cloudflare), expansion Note present with "scans run: 1". The multi-scan expansion path is covered by unit tests with a fake client only; no live domain with allowlisted subdomains was available.
