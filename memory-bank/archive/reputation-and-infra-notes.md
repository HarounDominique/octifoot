# Archive: reputation-and-infra-notes

Closed 2026-10-04 · Spec: [SPEC-reputation-and-infra-notes.md](../specs/SPEC-reputation-and-infra-notes.md) · Reflection: [reflection/reputation-and-infra-notes.md](../reflection/reputation-and-infra-notes.md) · Builds on: [archive/risk-signal-mapping.md](risk-signal-mapping.md), [archive/ab-validity-and-cloud-bucket-deny.md](ab-validity-and-cloud-bucket-deny.md)

## What was built

- `MALICIOUS_INTERNET_NAME`: an imported hostname, or the target itself, flagged by a feed gets label `spiderfoot:malicious` and one reference per
  feed, like flagged IPs; flags on hostnames that are not imported are only counted in the Note. Applied independently of event order.
- `DOMAIN_REGISTRAR`, `PROVIDER_HOSTING`, `PROVIDER_DNS`, `PROVIDER_MAIL`: one `Infrastructure` line in the scan Note (sorted, de-duplicated, five per kind).
  No new object types.
- `BLACKLISTED_*` deliberately stays unmapped (`sfp_cloudflaredns` uses it for a content filter). `IMPORTED_EVENTS` covers the new types; docs updated.
- 169 tests (18 new), `ruff` clean. Same object ids as the previous mapper on real events from two scans.
- Verified live: fresh enrichment (Note with the Infrastructure line, work 20/20 no errors) and replay of recorded real events through the connector path
  (label and Comodo reference on `redirecciones.dinaserver.com`).

## Deviations accepted

None. Scope was narrowed from the archives' "possible next" list on evidence (no passive port/banner/technology events; `BLACKLISTED_*` is not `MALICIOUS_*`).

## Not done / next

- Needing their own specs: `Indicator` objects with a CDN false-positive policy, AS names (another data source), non-CTI entities, an OpenCTI-triggered bidirectional loop (first verify multi-scan expansion live on an owned domain).
- Open-bucket finding (`CLOUD_STORAGE_BUCKET_OPEN`) is unmapped; the cloud modules stay denied until it is.
- "Flagged hostname not imported" Note line is unit-tested only.
- Why a direct API import dropped the label and reference was not investigated.
