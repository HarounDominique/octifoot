# Archive: event-catalogue

Closed 2026-10-04 · Spec: [SPEC-event-catalogue.md](../specs/SPEC-event-catalogue.md) · Reflection: [reflection/event-catalogue.md](../reflection/event-catalogue.md) · Builds on: [archive/drop-affiliate-names.md](drop-affiliate-names.md)

## What was built

A generated catalogue of all 172 SpiderFoot v4.0 event types: what it takes to produce each, which modules produce it, how often 21 real scans emitted it, and a decision with a rationale.

- `data/sf_event_types_v4.0.json` (SpiderFoot's `eventDetails`), `data/observed_events.json` (counts only), `catalogue.py`, `tools/build_catalogue.py`, `data/event_catalogue.json`, `docs/event-catalogue.md`
- Result: imported 15, planned 4 (`DOMAIN_WHOIS`, `DNS_TEXT`, `WEB_ANALYTICS_ID`, `SSL_CERTIFICATE_RAW`), declined 41, blocked 34 (keys or active modules), no-data 78
- 210 tests, `ruff` clean; tests keep the catalogue, the mapper and the Markdown in sync; licence notices updated for the new SpiderFoot-derived data

## Deviations accepted

Tests written before the spec file; one test assumption corrected (`EMAILADDR` is imported but was never seen in real scans).

## Not done / next

- Slices `whois-dns-notes` and `x509-certificates` (named in the catalogue).
- Owner decisions: API keys worth obtaining (`sfp_spyse`, `sfp_binaryedge`, `sfp_shodan`, `sfp_certspotter`...), and whether active modules may ever run.
