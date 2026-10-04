---
slug: source-health-note
spec: SPEC-source-health-note.md
status: approved
---

## Implementation Roadmap

Routing: standard.

- [x] Phase 1 — Client `fetch_errors`, mapper Note line, connector wiring, tests (satisfies: SPEC-source-health-note.md#objective, SPEC-source-health-note.md#boundaries)
- [x] Phase 2 — Docs + live check: README, rebuild connector, enrich a real domain, read the Note back (satisfies: SPEC-source-health-note.md#test-strategy)

## Execution State

**Build Status**: COMPLETE
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {1: 1, 2: 1}
**Last Block Rule**: none
**Can Resume**: NO

## Deviations

- Spec correction during build: the line was first sorted alphabetically by module. Rendered against the real log of scan `0115B5B0` it put Sublist3r behind
  "and 5 more" and spent slots on configuration noise (`sfp_customfeed`, `sfp_flickr`). Order changed to most errors first, then name; spec and tests updated. Accepted.
- Scripted edit slip: a constant was inserted between `@dataclass` and its class; `ruff` flagged it immediately and it was fixed before any commit.

**Live check (2026-10-04, connector rebuilt from this branch):** enrichment of zonetransfer.me, work complete 42/42, no errors, scan `8A4139B8`.
The Note read back from OpenCTI contains `Sources that reported errors (13 modules; an outage that a module reports as 'no information' is not detectable here): sflib: Failed to connect to https://api.bgpview.io/asn/16276 (46); sfp_commoncrawl: ... (2); sfp_sublist3r: Bad response code "None" from Sublist3r API (2); ...`.
At that moment crt.sh did not answer at all (curl timeout), and the line, as specified, does not mention it: `sfp_crt` logs the outage as "no information".
Not exercised live: the case where reading the log fails (unit-tested only).
