# Reflection: scan-changes

Date: 2026-10-04 · Spec: SPEC-scan-changes.md (approved) · Plan: 2 phases DONE · Live check: six replays of two recorded real scans through the real helper, Notes read back from OpenCTI, then removed

## Implementation vs spec

| Spec requirement | Result |
|---|---|
| State kept in OpenCTI as a snapshot Note read back by abstract prefix | Met; `starts_with` on `attribute_abstract` works, free-text search does not (fuzzy) |
| Added / not seen this time per category; first snapshot; no change | Met live for hostnames and certificates; other categories unit-tested |
| Disappearances only when both scans were complete; caveats for failing subdomain sources and incomplete previous scans | Met live (cases 2, 3, 6) |
| Certificates additions only; SPF/DMARC state changes only when both known | Met (tests; certificates live) |
| Unreadable previous snapshot: still write the new one; never fatal | Met (tests) |

Deviations: wording fix for incomplete comparisons found live (spec said "report no change" only for complete comparisons by implication; made explicit).

## What it adds, and its limit

For the first time the platform can answer "what is new on this domain since last time" without an analyst diffing two Notes by hand: a new host, a new IP, a new certificate, a changed mail setup. That is monitoring-grade information neither tool offers alone.
The limit is that comparisons are only as reliable as the scans: with sources failing and scans being cut by the timeout (both seen today), many comparisons are caveated. The Notes say so instead of asserting. Re-scans still have to be triggered; OpenCTI does not schedule enrichments.

## Workflow evaluation

- Replaying two real recorded scans gave a deterministic way to exercise every comparison branch against real data, including one ABORTED scan, which a live scan could not have produced on demand.
- The live replay exposed the misleading "no changes" wording, which no unit test had asserted against because the spec had not distinguished it; stating each comparison case explicitly in the spec was the fix.
- The replay override (an aborted scan marked FINISHED) is artificial and is documented as such; its results were deleted so no baseline is polluted.
- Scripted patches broke twice on ruff's reformatting; reading the current code before patching removed the problem.

## Rules extracted

- New `patch-from-the-current-text-never-from-memory` (code-editing).
- Reinforced: `after-cleaning-test-data-query-to-prove-it-is-gone` (evidence 2), `replay-recorded-events-when-upstream-is-nondeterministic` (evidence 5).

## Follow-ups (not blocking)

- Scheduling or alerting from changes needs its own spec (ask first).
- A real comparison between two scans run by the connector (not replays) once a domain is scanned twice.
