# SPEC: whois-dns-notes

Status: approved
Extends: [SPEC-event-catalogue.md](SPEC-event-catalogue.md) (slice `whois-dns-notes`), [SPEC-reputation-and-infra-notes.md](SPEC-reputation-and-infra-notes.md) (Note lines, no new objects)

## Objective

Carry two facts SpiderFoot already finds about the target into the OpenCTI Note, without new object types:
1. **Registration facts** from `DOMAIN_WHOIS`: creation, update and expiry dates, EPP status, DNSSEC, and how long before the scan the domain was created.
   Domain age is standard CTI context (a domain registered days ago is a signal); STIX has no field for it.
2. **TXT records** from `DNS_TEXT`: SPF policy, DMARC policy, and which services issued domain-verification tokens.

Evidence (real scans of three domains, 2026-10-04):
- WHOIS text contained `Creation Date`, `Updated Date`, `Registry Expiry Date`, `Domain Status` lines; `registrolineas.com` was created 2026-09-27, days before the scan.
- SpiderFoot's export **truncates the WHOIS text at 1024 characters** for all three, so later fields (name servers, DNSSEC) are sometimes missing: the parser must tolerate partial text.
- `DNS_TEXT` held only `google-site-verification=...` tokens (and a record of a third party's zone). No SPF or DMARC appeared in these three domains, so those parsers are proven on synthetic data only.
- `WEB_ANALYTICS_ID` repeated the same tokens but with the TXT string as `source_data`, losing the domain: it cannot be attributed, so it is declined (the catalogue said `planned`; corrected).
- The WHOIS text also contains registrar abuse contacts and, on other domains, registrant data: none of it is to be copied.

Success:
- The Note gets `WHOIS (as reported by SpiderFoot): created YYYY-MM-DD (N days before this scan); updated ...; expires ...; status: a, b; DNSSEC: ...` with only the fields that parsed.
- The Note gets `DNS TXT (as reported by SpiderFoot): SPF: <record>; DMARC: p=<policy>; verification tokens: google (1); other records: N` with only the parts present.
- Only events whose `source_data` is the target or a parent domain of it are used; others are counted as `DOMAIN_WHOIS (not the target's)` / `DNS_TEXT (not the target's)` under Unmapped.
- No registrant, contact, phone or email text from WHOIS ever reaches the Note; token values are never printed, only the service name.
- A WHOIS event with no parseable date and no status counts as invalid and produces no line. No objects are added; existing object ids are unchanged.
- `IMPORTED_EVENTS` includes `DOMAIN_WHOIS` and `DNS_TEXT`; the catalogue is regenerated (`WEB_ANALYTICS_ID` declined).

Out of scope: registrant, contact and name-server data from WHOIS (name servers are already in `Infrastructure`); RDAP; `DNS_SPF`/`RAW_DNS_RECORDS`; reading beyond SpiderFoot's 1024 characters.

## Assumptions (approved by the user's standing instruction to proceed)

1. Dates are the first `YYYY-MM-DD` found in the value of the key; keys accepted: creation (`Creation Date`, `Created`, `Registered On`, `Registration Time`),
   update (`Updated Date`, `Last Updated`, `Last Modified`), expiry (`Registry Expiry Date`, `Registrar Registration Expiration Date`, `Expiry Date`, `Expiration Date`, `Paid-till`).
2. Several WHOIS events for the target are merged first-wins per field.
3. Status tokens keep only the EPP name (the URL after it is dropped), de-duplicated in order.
4. "N days before this scan" uses the `now` passed to the mapper and is omitted if the creation date is in the future.
5. SPF is shown verbatim (public DNS data of the target) capped at 160 characters; DMARC only as its `p=` policy; unrecognised TXT records are only counted.

## Commands

```bash
cd connector && . .venv/bin/activate
python tools/build_catalogue.py
pytest && ruff check . && ruff format --check .
```

## Test strategy

Unit with synthetic WHOIS/TXT shaped like the real ones (reserved example names): dates and age, status tokens, partial and truncated text, merge, other keys, no PII, third-party source, parent domain, SPF/DMARC/verification, determinism, no new objects.
Real data: old vs new mapper on recorded events (ids unchanged, Note gains two lines). Live: rebuild, enrich, read the Note back.

## Boundaries

**Always**: copy only dates, EPP status, DNSSEC and TXT classes; state in the Note that the values are as reported.
**Ask first**: importing registrant or contact data; reading RDAP.
**Never**: print verification token values or any WHOIS contact data; use WHOIS or TXT of a domain that is not the target or its parent.
