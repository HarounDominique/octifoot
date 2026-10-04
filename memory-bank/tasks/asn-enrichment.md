---
slug: asn-enrichment
spec: SPEC-asn-enrichment.md
status: approved
---

## Implementation Roadmap

Routing: standard (one file extended, design fixed in spec).

- [ ] Phase 1 — ASN mapping: `parse_asn`, IP→netblock→AS chain, `autonomous-system` + `belongs-to`, Note line (satisfies: SPEC-asn-enrichment.md#objective, SPEC-asn-enrichment.md#style)
- [ ] Phase 2 — Docs + live round-trip: README table; replay real events into OpenCTI and read relationships back; one real connector scan (satisfies: SPEC-asn-enrichment.md#test-strategy)

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
