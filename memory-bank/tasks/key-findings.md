---
slug: key-findings
spec: SPEC-key-findings.md
status: approved
---

## Implementation Roadmap

Routing: standard.

- [x] Phase 1 — Mapper: findings block, evidence capture, subdomain sources from metadata, tests (satisfies: SPEC-key-findings.md#objective, SPEC-key-findings.md#boundaries)
- [x] Phase 2 — Docs + real-data check + live check (satisfies: SPEC-key-findings.md#test-strategy)

## Execution State

**Build Status**: COMPLETE
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {1: 1, 2: 1}
**Last Block Rule**: none
**Can Resume**: NO

## Deviations

- Not in the first draft of the spec, added after checking the data: the coverage finding uses a curated list of real subdomain enumerators (`profiles.SUBDOMAIN_SOURCES`) instead of "any module that emits `INTERNET_NAME`",
  because `sfp_flickr` (always "Failed to obtain API key") and others emit hostnames only as a by-product and would raise a false alarm in every scan. A test validates the list against SpiderFoot's metadata.

**Ground truth (2026-10-04, `dig`):** registrolineas.com publishes only a google-site-verification TXT; bugoverflow.com publishes no TXT; zonetransfer.me only a google-site-verification TXT; none has `_dmarc`.
SpiderFoot reported no SPF for any of them. So "mail without SPF" is true for bugoverflow.com and zonetransfer.me (both have MX); registrolineas.com has no MX, so no mail finding. SpiderFoot does not query `_dmarc`, so DMARC is deliberately not claimed.

**Real data:** newest finished scan per domain: registrolineas.com: registered 7 days ago, 2 listings on shared infrastructure, coverage warning; zonetransfer.me: mail without SPF, 4 listings, coverage warning; bugoverflow.com: mail without SPF, coverage warning. All consistent with the ground truth above.

**Live check (2026-10-04, connector rebuilt from this branch):** enrichment of bugoverflow.com, scan `508A0136`, work complete 10/10, no errors. The Note read back from OpenCTI opens with the `Key findings (as of this scan)` block (mail without SPF, coverage warning) on its second line.
**Correction (2026-10-04, found while preparing the DNS-checks task):** the statements above that bugoverflow.com "receives mail" were wrong. `dig MX bugoverflow.com` returns NOERROR with no answers; the
`PROVIDER_MAIL mail.dinaserver.com` event had `source_data = dinaserver.com`, a provider's domain seen while resolving a CNAME, and the mapper (from `reputation-and-infra-notes`) did not filter infrastructure
events by source. Fixed in task `fix-infra-attribution`; the mail-without-SPF finding now appears only for zonetransfer.me (the one test domain with MX).

Not seen live: flagged hosts, certificate expiry and registration-expiry findings (unit-tested with synthetic data; no real domain triggered them).
