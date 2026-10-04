# Archive: whois-dns-notes

Closed 2026-10-04 · Spec: [SPEC-whois-dns-notes.md](../specs/SPEC-whois-dns-notes.md) · Reflection: [reflection/whois-dns-notes.md](../reflection/whois-dns-notes.md) · Builds on: [archive/event-catalogue.md](event-catalogue.md)

## What was built

Two more lines in the scan Note, text only, from the target's own (or parent) WHOIS and TXT events:
`WHOIS (as reported by SpiderFoot): created ... (N days before this scan); updated; expires; status; DNSSEC` and
`DNS TXT (as reported by SpiderFoot): SPF; DMARC policy; verification tokens by service; other records: N`. No registrant or contact data and no token values are copied;
third-party WHOIS/TXT is counted as "not the target's". `DOMAIN_WHOIS` and `DNS_TEXT` are imported; `WEB_ANALYTICS_ID` declined; the catalogue regenerated.

- Also: `SpiderFootClient` retries GETs on transient connection errors (found by the live check); POST `/startscan` is never retried.
- 233 tests, `ruff` clean
- Verified live: registrolineas.com scan `A70D2B5E`, work 17/17, Note with both lines (domain created 7 days before the scan), no leakage

## Deviations accepted

`WEB_ANALYTICS_ID` moved from planned to declined (it loses the source domain); unplanned retry fix; one test arithmetic corrected.

## Not done / next

- SPF and DMARC parsers are proven on synthetic data only; none of the three test domains had them.
- Remaining planned slice: `x509-certificates`.
