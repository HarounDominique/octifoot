---
slug: fix-additions-may-be-visibility
spec: SPEC-scan-changes.md
status: approved
---

## Implementation Roadmap

Routing: fix (defect in shipped behaviour, found by two real consecutive scans).

- [x] Phase 1 — Failing tests, `source_gaps` in the snapshot, visibility caveats on hostname and certificate additions (satisfies: SPEC-scan-changes.md#objective)
- [x] Phase 2 — Docs, spec amendment, live replay (satisfies: SPEC-scan-changes.md#test-strategy)

## Execution State

**Build Status**: COMPLETE
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {1: 1, 2: 1}
**Last Block Rule**: none
**Can Resume**: NO

## Deviations

- Amends SPEC-scan-changes.md (a visible note was added there). The defect was in the design, not the code: the spec had covered incomplete scans but not scans that are "complete" while a source silently returned nothing.

**What the real pair showed (bugoverflow.com, two consecutive scans run by the connector itself, 2026-10-04):** run 1 imported 12 objects and no certificates; run 2 imported 45 objects. The second snapshot Note said
`hostnames added: www.bugoverflow.com` and `certificates added: 13 (...)`. Neither is a change in the world: crt.sh answered the second time only, and `sfp_crt` cannot report an outage, so the first scan looked complete.

**Fix:** the snapshot records `source_gaps` (subdomain sources reported errors during that scan; older snapshots read as false). Hostname additions after such a scan carry `(the previous scan's subdomain sources reported errors: this may only be newly visible)`;
certificate additions where the previous scan had none carry `(the previous scan had none: crt.sh may not have answered)`.

**Live check (2026-10-04):** replays of two recorded scans of zonetransfer.me (`A074967B` with source errors and no certificates, then `06410167`): the Note shows both caveats on the two additions. The two replay snapshot Notes were deleted and none remain;
the two real bugoverflow.com snapshots (the real baseline) were kept.
Not seen live: a real comparison between two connector runs with the new caveat text (the pair above predates it).
