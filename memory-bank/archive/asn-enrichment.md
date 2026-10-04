# Archive: asn-enrichment

Closed 2026-10-04 · Spec: [SPEC-asn-enrichment.md](../specs/SPEC-asn-enrichment.md) · Reflection: [reflection/asn-enrichment.md](../reflection/asn-enrichment.md) · Builds on: [archive/iterative-scan-loop.md](iterative-scan-loop.md)

## What was built

Each imported IP is linked to its autonomous system: `IP -belongs-to-> autonomous-system`, from the
chain `NETBLOCK_MEMBER`/`NETBLOCKV6_MEMBER` (IP→CIDR) + `BGP_AS_MEMBER` (CIDR→ASN). AS objects carry
only the number and SpiderFoot provenance and exist only when linked to an imported IP. The scan Note
lists ASNs and IP counts. Netblocks, AS names and any AS↔domain link are deliberately not created.
For a site behind a CDN every IP points to the CDN's AS, which exposes shared hosting at a glance.

- `mapper.py`: `parse_asn`, chain, `as_ips`; README table; 116 tests (21 new), `ruff` clean
- Verified live: replay of real events and a fresh connector scan; one `AS13335`, 4 links, merged provenance

## Deviations accepted

None.

## Not done / next

- AS names/organisations (not in the events; would need another source). Ask first per spec.
- Still open from earlier archives: live test of multi-scan expansion on a domain with allowlisted subdomains; ports/banners/technologies; `Indicator` with CDN-aware filtering.
