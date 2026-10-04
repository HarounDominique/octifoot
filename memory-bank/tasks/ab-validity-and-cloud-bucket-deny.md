---
slug: ab-validity-and-cloud-bucket-deny
spec: SPEC-ab-validity-and-cloud-bucket-deny.md
status: approved
---

## Implementation Roadmap

Routing: standard (small pure code, then a measurement).

- [x] Phase 1 — Validity + deny-list: `invalid_reasons`, `valid`/`invalid_reasons` in the harness report, `IMPORTED_EVENTS`, four cloud-bucket modules denied, list regenerated, coverage tests (satisfies: SPEC-ab-validity-and-cloud-bucket-deny.md#objective)
- [ ] Phase 2 — Valid A/B re-run on both domains, record results (satisfies: SPEC-ab-validity-and-cloud-bucket-deny.md#test-strategy)

## Execution State

**Build Status**: RUNNING
**Current Phase**: 2
**Current Step**: live A/B
**Step Attempts**: {2: 0}
**Last Block Rule**: none
**Can Resume**: YES

## Deviations

[none yet]
