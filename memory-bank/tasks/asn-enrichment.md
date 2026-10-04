---
slug: asn-enrichment
spec: SPEC-asn-enrichment.md
status: approved
---

## Implementation Roadmap

Routing: standard (one file extended, design fixed in spec).

- [x] Phase 1 — ASN mapping: `parse_asn`, IP→netblock→AS chain, `autonomous-system` + `belongs-to`, Note line (satisfies: SPEC-asn-enrichment.md#objective, SPEC-asn-enrichment.md#style)
- [x] Phase 2 — Docs + live round-trip: README table; replay real events into OpenCTI and read relationships back; one real connector scan (satisfies: SPEC-asn-enrichment.md#test-strategy)

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
- Live round-trip (2026-10-04): real events of an earlier scan (`DF50665A`) were replayed through the new mapper and imported into the running OpenCTI. Read back: `Autonomous-System 13335` created by SpiderFoot with external reference (scan id), and `belongs-to` from all 4 imported IPs (2 IPv4, 2 IPv6). A fresh end-to-end scan through the connector was run afterwards (see below).
- Phase 2 closed after the fact: the roadmap box and Build Status were left at RUNNING when the branch merged; fixed on main. The end-to-end scan result was: 20 objects processed, no errors, one AS13335 with 4 links and merged provenance.
