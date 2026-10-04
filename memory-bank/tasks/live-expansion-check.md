---
slug: live-expansion-check
spec: SPEC-live-expansion-check.md
status: approved
---

## Implementation Roadmap

Routing: verification only.

- [x] Phase 1 — Live run: enrich bugoverflow.com with depth 1, read work, Note and discovered list back (satisfies: SPEC-live-expansion-check.md#objective)

## Execution State

**Build Status**: COMPLETE
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {1: 1}
**Last Block Rule**: none
**Can Resume**: NO

## Deviations

**Result (2026-10-04, OpenCTI 7.261002.0, connector with `SPIDERFOOT_MAX_DEPTH=1`, `SPIDERFOOT_MAX_SCANS=5`, profile `lean`)**

- Work `work_68301203-..._2026-10-04T11:49:41.455Z` for observable bugoverflow.com: `complete`, 20 of 20 objects processed, no errors, 7 min 4 s, one SpiderFoot scan `E1E0F7E5`.
- Expansion Note present: "scans run: 1, max depth reached: 0. Failed sub-scans: none. Skipped, outside the allowlist (never scanned): redirecciones.dinaserver.com. Skipped, over the scan budget: none."
- **Verified live:** the loop runs, reads the scan's events, applies the allowlist (a real discovered hostname outside it was refused and never scanned), reports skips, and finishes cleanly.
- **Not verified live:** the success path (scanning allowlisted subdomains). Recomputing the discovered list from the exported events of all four scans on the two test domains gives no allowlisted subdomain (`registrolineas.com`: none, behind Cloudflare; `bugoverflow.com`: only `redirecciones.dinaserver.com`). Forcing it would mean authorizing a third-party domain, which was not done.
- To close it: allowlist a domain you own that has public subdomains and enrich it with depth 1.
