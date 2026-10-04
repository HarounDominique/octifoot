---
slug: whois-dns-notes
spec: SPEC-whois-dns-notes.md
status: approved
---

## Implementation Roadmap

Routing: standard.

- [x] Phase 1 — Mapper: WHOIS and TXT Note lines, `IMPORTED_EVENTS`, catalogue regenerated, tests (satisfies: SPEC-whois-dns-notes.md#objective, SPEC-whois-dns-notes.md#boundaries)
- [x] Phase 2 — Docs + live check: README, old-vs-new on real events, rebuild, enrich, read the Note back (satisfies: SPEC-whois-dns-notes.md#test-strategy)

## Execution State

**Build Status**: COMPLETE
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {1: 1, 2: 2}
**Last Block Rule**: none
**Can Resume**: NO

## Deviations

- Catalogue correction: `WEB_ANALYTICS_ID` was `planned`; reading the real events showed it loses the source domain (the TXT string is its source), so it was declined and `DNS_TEXT` carries the tokens. Accepted.
- Unplanned fix, found by the live check: the first live run failed after 52 s with `SpiderFoot request to /scanstatus failed: RemoteDisconnected` (SpiderFoot closed a
  keep-alive connection while the connector polled). One dropped GET aborted a multi-minute scan. `SpiderFootClient._request` now retries GETs up to 3 times (2 s, 4 s);
  POST `/startscan` is never retried (a repeat would start a second scan) and HTTP errors are not retried. Four tests. Accepted.
- One test had wrong arithmetic (559 days instead of 558); verified with `datetime` and the test corrected, not the code.

**Old vs new mapper on recorded real events (3 domains):** object ids unchanged on all; the Note gains the `WHOIS` line (and the `DNS TXT` line where TXT existed);
WHOIS and TXT of `dinaserver.com` (a provider's domain, seen from bugoverflow.com) are excluded and counted as "not the target's".

**Live check (2026-10-04, connector rebuilt from this branch):** enrichment of registrolineas.com, scan `A70D2B5E`, work complete 17/17, no errors.
Note read back from OpenCTI: `WHOIS (as reported by SpiderFoot): created 2026-09-27 (7 days before this scan); updated 2026-09-27; expires 2027-09-27; status: clientDeleteProhibited, clientTransferProhibited; DNSSEC: unsigned`
and `DNS TXT (as reported by SpiderFoot): verification tokens: google (1)`; no registrant text, abuse contact or token value in the Note.
Not seen live: SPF and DMARC (none of the three domains had them in `DNS_TEXT`); proven on synthetic data only.
