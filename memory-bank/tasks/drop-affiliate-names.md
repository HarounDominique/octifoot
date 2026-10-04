---
slug: drop-affiliate-names
spec: SPEC-drop-affiliate-names.md
status: approved
---

## Implementation Roadmap

Routing: standard (one mapper change, tests rewritten where they asserted the old behaviour).

- [x] Phase 1 — Mapper: affiliate names unmapped, guard for IPs from affiliate hosts, tests updated/added (satisfies: SPEC-drop-affiliate-names.md#objective, SPEC-drop-affiliate-names.md#boundaries)
- [x] Phase 2 — Docs + live check: README table, old-vs-new on real events, rebuild, enrich, read back (satisfies: SPEC-drop-affiliate-names.md#test-strategy)

## Execution State

**Build Status**: COMPLETE
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {1: 1, 2: 1}
**Last Block Rule**: none
**Can Resume**: NO

## Deviations

- Reverses a design choice of the original connector spec (affiliate names imported at half score). Decided by the user on 2026-10-04; recorded in the spec.
- An extra change the spec did not predict at first sight but required: IPs whose source host is an affiliate name now skip instead of falling back to the target.
  Found by reading the `domains.get(source_host, target_obj)` fallback, not by a failing test. Real scans had 0 such IPs (0 of 7), so it is defensive.

**Old vs new mapper on recorded real events (5 scans, 3 domains):** nothing added, nothing changed; only `domain-name` objects from `AFFILIATE_INTERNET_NAME` and their
`related-to` relationships disappear. Objects per scan: zonetransfer.me 39 to 5, bugoverflow.com 17 to 7, registrolineas.com 18 to 14.

**Live check (2026-10-04, connector rebuilt from this branch):** enrichment of zonetransfer.me, scan `A074967B`, work complete **8/8** (was 42), no errors.
Note read back from OpenCTI: `Mapped: domain-name=1, ipv4-addr=1`, `Autonomous systems: AS16276 (1 IP)`, the `Infrastructure` line unchanged, and
`AFFILIATE_INTERNET_NAME=22` under "Unmapped". Observables referencing the scan: `Autonomous-System 16276` and `IPv4-Addr 5.196.105.14` (the target carries no reference by design).
Objects imported by earlier scans (Google MX hosts etc.) remain in OpenCTI; they were not deleted.
