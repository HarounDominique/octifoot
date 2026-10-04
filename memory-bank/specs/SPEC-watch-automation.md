# SPEC: watch-automation

Status: approved
Extends: [SPEC-scan-changes.md](SPEC-scan-changes.md) (the comparison only has value if scans recur), [SPEC-spiderfoot-connector.md](SPEC-spiderfoot-connector.md) (authorization model)

## Objective

Re-analyse chosen domains automatically so the change detection works without anyone remembering to click. The owner approved automation on 2026-10-04. Safety model unchanged: nothing is scanned unless an analyst opted the domain in AND it is on the allowlist.

Design: an analyst puts the label `octifoot:watch` on a `Domain-Name` observable in OpenCTI. A background loop in the connector reads the watched domains, and for each one that is **due** asks OpenCTI to run this connector's own enrichment on it (the same request an analyst's click makes),
so every automated run is an ordinary, auditable work item with the normal Notes, snapshot and comparison.

Success:
- Off by default. `SPIDERFOOT_WATCH_INTERVAL_MINUTES` = 0 (unset) means no loop; otherwise 5..10080 and the loop runs. `SPIDERFOOT_WATCH_MAX_PER_CYCLE` (1..20, default 3) caps how many scans one cycle may start.
- A watched domain is asked only if it passes the same allowlist check as a manual request; others are skipped and logged, never asked.
- A domain is due when its newest snapshot Note is at least the interval old, or it has none; it is not asked again within the interval after being asked, even before its scan finishes.
- Due domains are taken oldest first (never scanned first); the cap applies per cycle.
- A failing cycle (platform unreachable, one request refused) never stops the loop or the connector; failures are logged and the remaining domains continue.
- The loop runs in the connector process on a daemon thread; the connector keeps `CONNECTOR_AUTO=false`.
- Removing the label (or the domain from the allowlist) stops further runs for that domain.

Out of scope: alerting or notifications on change (the Note and snapshot already say what changed); per-domain intervals; prioritising by risk; running outside the connector process.

## Assumptions (approved by the user's standing instruction to proceed)

1. The connector's OpenCTI token must be allowed to request enrichments; this development stack uses the admin token. A dedicated connector user needs that capability (documented).
2. The cycle period is a quarter of the interval, between 60 s and 15 min.
3. "Last scan" is the `at` of the newest readable snapshot Note (state already kept in OpenCTI by scan-changes); a domain whose snapshots were deleted counts as never scanned.
4. The in-memory "recently asked" record is lost on restart; the snapshot time then governs, and a scan still running at restart can at worst be asked once more.

## Commands

```bash
cd connector && . .venv/bin/activate
pytest && ruff check . && ruff format --check .
```

## Test strategy

Unit with injected collaborators and a fake clock: due logic (never scanned, recent, old), no repeat within the interval, allowlist, subdomains, cap and order, normalisation, failure isolation, thread stop; config parsing; the two OpenCTI helpers with a fake query.
Live: label a real test domain, run with a short interval, watch the automatic request, scan and snapshot, confirm it is not asked again early and is asked again when due, then remove the label and restore the setting.

## Boundaries

**Always**: require the label and the allowlist; keep it off unless configured; cap per cycle.
**Ask first**: alerting, scanning domains found by the loop, any default-on behaviour.
**Never**: scan a domain that is not on the allowlist; start scans without an analyst's label.
