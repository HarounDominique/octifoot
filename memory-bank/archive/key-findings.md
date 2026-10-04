# Archive: key-findings

Closed 2026-10-04 · Spec: [SPEC-key-findings.md](../specs/SPEC-key-findings.md) · Reflection: [reflection/key-findings.md](../reflection/key-findings.md) · Builds on: [archive/x509-certificates.md](x509-certificates.md)

## What was built

A `Key findings (as of this scan)` block on the second line of the scan Note, from fixed rules tied to observed evidence: flagged hostnames/IPs, mail without SPF (never claims DMARC), certificate expiry, newly registered domain (< 30 days),
registration expiry, reputation listings on shared infrastructure, and subdomain-source coverage (curated list `profiles.SUBDOMAIN_SOURCES`). With nothing notable it says so without calling the target clean.

- 268 tests, `ruff` clean; documented in the README
- Matches ground truth on three domains (checked with `dig`); verified live on bugoverflow.com (scan `508A0136`, work 10/10)

## Deviations accepted

Curated subdomain-source list instead of "any module that emits hostnames" (false alarms from `sfp_flickr`).

## Not done / next

- Flagged, certificate-expiry and registration-expiry findings were not triggered by any real domain (synthetic tests only).
- DMARC, CAA and DNSSEC presence need an own DNS check (SpiderFoot does not query them).
