# Archive: source-health-note

Closed 2026-10-04 · Spec: [SPEC-source-health-note.md](../specs/SPEC-source-health-note.md) · Reflection: [reflection/source-health-note.md](../reflection/source-health-note.md) · Builds on: [archive/live-expansion-check.md](live-expansion-check.md)

## What was built

After each scan the connector reads SpiderFoot's scan log (`SpiderFootClient.fetch_errors`, ERROR rows, entities decoded) and the scan Note gets one line
naming the modules that failed: most errors first then by name, first message cut at 80 characters, eight modules then "and N more", and an explicit
statement that outages reported as "no information" are not detectable. No errors, no line; objects unchanged; a failing log read only logs a warning.

- `client.py`, `mapper.py` (`source_errors`), `connector.py` (one call per scan), README section; 184 tests, `ruff` clean
- Verified live: enrichment of zonetransfer.me (scan `8A4139B8`), work 42/42 no errors, the line read back from OpenCTI (13 modules, `sflib` 46 connection failures first)

## Deviations accepted

Ordering changed from alphabetical to most-errors-first after rendering on a real log; spec amended.

## Not done / next

- crt.sh outages remain invisible (`sfp_crt` logs them like "no certificates"). A direct probe of key sources from the connector is "ask first" in the spec.
- The failing-log-read path and multi-scan reading were not seen live.
