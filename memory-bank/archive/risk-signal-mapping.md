# Archive: risk-signal-mapping

Closed 2026-10-04 · Spec: [SPEC-risk-signal-mapping.md](../specs/SPEC-risk-signal-mapping.md) · Reflection: [reflection/risk-signal-mapping.md](../reflection/risk-signal-mapping.md) · Builds on: [archive/spiderfoot-connector.md](spiderfoot-connector.md)

## What was built

Mapper extension in `connector/src/spiderfoot_connector/mapper.py`:
- `IPV6_ADDRESS` imported as `ipv6-addr` with `resolves-to`.
- `MALICIOUS_IPADDR`: imported IPs get label `spiderfoot:malicious` and one external reference per feed.
- `MALICIOUS_SUBNET` / `MALICIOUS_COHOST`: listed in the scan Note (max 20 lines), never objects.
- `AFFILIATE_*` events: never objects, counted as unmapped.
- `parse_feed_event` for the `"Feed [value]"` format; fixture anonymized from a real scan.
- README documents the table and the reasoning (shared CDN infrastructure is not the target's).

68 tests (17 new), `ruff` clean.

## Deviations accepted

- `MALICIOUS_SUBNET`/`MALICIOUS_COHOST` as Note lines and `AFFILIATE_EMAILADDR` unmapped, instead of objects as first requested; agreed with the user after reading real scan data.

## Not done / next

- **Live check not run** (stack paused at the user's request). To verify: start the stack, re-enrich an owned domain, expect label `spiderfoot:malicious` on the Maltiverse-flagged IPs and the VoIPBL/Comodo lines in the Note.
- Possible next: ports/banners/technologies, `Indicator` objects with CDN-aware filtering, iterative investigation loop (see spec *Future* in SPEC-spiderfoot-connector).
