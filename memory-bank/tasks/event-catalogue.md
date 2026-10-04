---
slug: event-catalogue
spec: SPEC-event-catalogue.md
status: approved
---

## Implementation Roadmap

Routing: standard (data derivation plus decisions).

- [x] Phase 1 — Snapshot of SpiderFoot's event types, counts of observed events, `catalogue.py`, generator, tests (satisfies: SPEC-event-catalogue.md#objective)
- [x] Phase 2 — Real-data review of observed types, generated `docs/event-catalogue.md`, licence notices (satisfies: SPEC-event-catalogue.md#test-strategy)

## Execution State

**Build Status**: COMPLETE
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {1: 1, 2: 1}
**Last Block Rule**: none
**Can Resume**: NO

## Deviations

- Order: the tests were written before this spec file (the scope had been agreed in the conversation); the spec was written from the same scope right after. Accepted.
- One test assumption was wrong and was corrected: it required every unobserved type to be blocked, no-data or declined; `EMAILADDR` is imported but was never seen in any real scan (only `AFFILIATE_EMAILADDR` was), so the mapper for the target's own emails is proven on fixtures only. The test now states that explicitly.

**Result (2026-10-04):** 172 types: imported 15, planned 4, declined 41, blocked 34, no-data 78. Observed in real scans: 46.
What it takes to produce the not-yet-seen types: 61 passive (never emitted), 17 only via deny-listed keyless modules, 28 need an API key, 6 need active modules.

**Findings from reading the real values, which changed the plan:**
- `COMPANY_NAME` (registry, registrar, a privacy proxy), `PHYSICAL_ADDRESS` and `LEI` (GLEIF data of the registry operator), `PHONE_NUMBER` (registrar contact) describe the registry side, not the target:
  importing them would misattribute. Declined with that evidence.
- `DOMAIN_WHOIS`, `DNS_TEXT`/`WEB_ANALYTICS_ID` (verification tokens) and `SSL_CERTIFICATE_RAW` are the real candidates: planned as slices `whois-dns-notes` and `x509-certificates`.
- Keys that would unlock the most blocked types: `sfp_spyse` (12), `sfp_binaryedge` (8), `sfp_shodan` (8), `sfp_sslcert` (6), `sfp_certspotter` (5; a certificate-transparency source, an alternative to crt.sh).
- `BGP_AS_OWNER` (AS names) is producible but never appeared: the source `api.bgpview.io` failed on every request (46 connection failures per scan).
