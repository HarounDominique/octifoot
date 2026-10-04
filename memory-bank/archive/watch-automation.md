# Archive: watch-automation

Closed 2026-10-04 · Spec: [SPEC-watch-automation.md](../specs/SPEC-watch-automation.md) · Reflection: [reflection/watch-automation.md](../reflection/watch-automation.md) · Builds on: [archive/scan-changes.md](scan-changes.md)

## What was built

Automatic re-analysis, off by default. With `SPIDERFOOT_WATCH_INTERVAL_MINUTES` (5 to 10080) a daemon thread in the connector reads the `Domain-Name` observables labelled `octifoot:watch` and, for each one that is on the allowlist and due (newest snapshot older than the interval, not requested within it),
asks OpenCTI to run the connector's own enrichment, oldest first, at most `SPIDERFOOT_WATCH_MAX_PER_CYCLE` per cycle. Failures never stop the loop; removing the label stops the runs; `CONNECTOR_AUTO` stays `false`.

- `watch.py`, config, `main()` wiring, Compose and `.env.example`, README; 408 tests, `ruff` clean
- Verified live on a real domain with a 5-minute interval: automatic request, scan started with no click, no early repeat, second request when due, `no changes` between the two runs, no request after the label was removed; label and setting restored

## Deviations accepted

None.

## Not done / next

- The allowlist skip, the per-cycle cap and failure paths were not provoked live (unit-tested).
- Alerting on change is "ask first". A least-privilege connector user (instead of the admin token of this development stack) is recommended.
