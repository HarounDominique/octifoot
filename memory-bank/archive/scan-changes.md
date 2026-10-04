# Archive: scan-changes

Closed 2026-10-04 · Spec: [SPEC-scan-changes.md](../specs/SPEC-scan-changes.md) · Reflection: [reflection/scan-changes.md](../reflection/scan-changes.md) · Builds on: [archive/opencti-knowledge.md](opencti-knowledge.md)

## What was built

Each enrichment of a root target writes a Note `octifoot snapshot for <target>: <summary>` that lists what was added and not seen since the previous scan (hostnames, IPs, emails, AS numbers, name servers, mail hosts; certificate additions; registrar and hosting changes; SPF/DMARC state)
and ends with a machine-readable snapshot line. The state lives in OpenCTI, read back by the Note's abstract prefix. Disappearances are reported only when both scans were complete; caveats cover failing subdomain sources, incomplete previous scans and an unreadable previous snapshot;
an incomplete comparison with nothing added says "no additions ... disappearances are not assessed", never "no changes".

- `changes.py`, connector wiring, README section; 365 tests, `ruff` clean
- Verified live with six replays of two recorded real scans (additions, no-change, removal with caveat, incomplete cases); the six replay Notes were deleted afterwards

## Deviations accepted

None from the spec; wording defect found live and fixed test-first.

## Not done / next

- IPs, emails, AS, infrastructure and SPF/DMARC state changes were not seen on real data (unit-tested).
- Re-scans must be triggered; scheduling or alerting from changes is "ask first".
