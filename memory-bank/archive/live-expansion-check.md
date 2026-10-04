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

## Second attempt

On `zonetransfer.me` (published by its owner for security training): work complete 42/42, no errors, one scan. Still no subdomains to expand:
`crt.sh` returned HTTP 502 for 6+ minutes and Sublist3r, CommonCrawl and Crobat also failed; the zone's subdomains are only reachable by active
modules, which stay out of `lean`. The success path remains unit-tested only.

## Not done / next

- Retry the expansion when `crt.sh` is back, or on a domain whose subdomains have public certificates (3-5 min per scan).
- Surface failed sources in the scan Note (modules that logged ERROR, and upstream HTTP errors) so a scan with zero subdomains because `crt.sh` was down is distinguishable from a domain with none. Needs its own spec.
