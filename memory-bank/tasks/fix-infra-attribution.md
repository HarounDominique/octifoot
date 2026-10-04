---
slug: fix-infra-attribution
spec: SPEC-fix-infra-attribution.md
status: approved
---

## Implementation Roadmap

Routing: fix (defect in shipped behaviour).

- [x] Phase 1 — Failing tests, source filter for registrar/DNS/mail, hosting by imported IP (satisfies: SPEC-fix-infra-attribution.md#objective)
- [x] Phase 2 — Docs, corrections to earlier notes, live check against ground truth (satisfies: SPEC-fix-infra-attribution.md#test-strategy)

## Execution State

**Build Status**: COMPLETE
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {1: 1, 2: 1}
**Last Block Rule**: none
**Can Resume**: NO

## Deviations

- This is a defect in two earlier, already archived tasks (`reputation-and-infra-notes`, `key-findings`), both of which I had "verified live". Their live checks confirmed that the lines appeared and the work completed; neither compared the
  *values* with the target's real records. Corrections were added to those tasks' notes and archives.
- Hosting needed a different rule from the others: its `source_data` is an IP, not a domain. Real data: Cloudflare's IPs for registrolineas.com and OVH's for zonetransfer.me were imported IPs of the target and kept; a foreign IP is excluded.

**Real data after the fix (newest finished scan per domain vs `dig`):**
- bugoverflow.com: `Infrastructure` has registrar, hosting and the four name servers; the provider's MX, 4 name servers and registrar events are excluded and counted as "not the target's"; no mail finding. `dig MX` returns nothing: consistent.
- zonetransfer.me: keeps mail hosts and the mail-without-SPF finding. `dig MX` returns seven Google hosts: consistent.
- registrolineas.com: unchanged (no foreign events); no MX: consistent.

**Live check (2026-10-04, connector rebuilt from this branch):** re-enrichment of bugoverflow.com, scan `B3A1775D`, work complete 10/10, no errors. The Note read back from OpenCTI has no `mail:` entry and no mail finding.
