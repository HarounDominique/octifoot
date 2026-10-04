# Archive: live-expansion-check

Closed 2026-10-04 · Spec: [SPEC-live-expansion-check.md](../specs/SPEC-live-expansion-check.md) · Reflection: [reflection/live-expansion-check.md](../reflection/live-expansion-check.md) · Builds on: [archive/iterative-scan-loop.md](iterative-scan-loop.md)

## What was built

Nothing new in code. A real enrichment of `bugoverflow.com` with `SPIDERFOOT_MAX_DEPTH=1` ran through the
whole stack (OpenCTI, worker, connector, SpiderFoot): work complete, 20/20 objects, no errors, 7 min 4 s,
expansion Note present.

- Verified live: the loop runs, applies the allowlist (a real out-of-scope hostname was refused and never scanned), reports skips, finishes cleanly.
- Not verified live: scanning allowlisted subdomains. Neither authorized test domain discovers any (checked on the events of four real scans).

## Deviations accepted

None. The success path stays unit-tested only; forcing it would have needed authorizing a third-party domain.

## Not done / next

- Enrich a domain the owner controls that has public subdomains with depth 1 (one command, ~10-30 min) to verify merge and dedupe across real scans.
