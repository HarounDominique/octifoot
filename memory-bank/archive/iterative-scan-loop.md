# Archive: iterative-scan-loop

Closed 2026-10-04 · Spec: [SPEC-iterative-scan-loop.md](../specs/SPEC-iterative-scan-loop.md) · Reflection: [reflection/iterative-scan-loop.md](../reflection/iterative-scan-loop.md) · Builds on: [archive/risk-signal-mapping.md](risk-signal-mapping.md)

## What was built

Opt-in iterative investigation: with `SPIDERFOOT_MAX_DEPTH` 1-3, one enrichment request also scans the
allowlisted subdomains it discovers (`INTERNET_NAME` only), breadth-first, each once, capped by
`SPIDERFOOT_MAX_SCANS` (1-20, root included). One merged bundle, plus an "expansion" Note and message
listing scans run, depth, failed sub-scans and what was skipped (out of scope, over budget).

- `expansion.py`: pure planner; `mapper.py`: `discovered_domains`; `connector.py`: loop; config, compose, README
- Safe by construction: every scan passes the allowlist check; expansion cannot widen scope; off by default
- 95 tests, `ruff` clean

Also fixed (defect from the previous iteration): feed external references lacked `external_id` and were
silently dropped by OpenCTI. Verified live by replaying real events into OpenCTI.

## Deviations accepted

- Bug fix for already-merged `risk-signal-mapping` shipped inside this task.
- Multi-scan expansion not exercised live (no domain with subdomains available); unit tests only.

## Not done / next

- Live test of a real expansion on an owned domain that has allowlisted subdomains.
- Expansion from other types (IPs, emails) or parallel scans: "ask first" in the spec.
- Ports/banners/technologies; `Indicator` objects with CDN-aware filtering; non-CTI entities.
