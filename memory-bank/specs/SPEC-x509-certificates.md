# SPEC: x509-certificates

Status: approved
Extends: [SPEC-event-catalogue.md](SPEC-event-catalogue.md) (slice `x509-certificates`), [SPEC-reputation-and-infra-notes.md](SPEC-reputation-and-infra-notes.md)

## Objective

Import the TLS certificates SpiderFoot (via crt.sh) found for the target as STIX `x509-certificate` objects, a standard type OpenCTI models, related to the scanned domain.
Certificate history is useful CTI context (issuer, issue date, rotation pattern).

Evidence (real data, 2026-10-04): across 21 scans exactly **one** `SSL_CERTIFICATE_RAW` event appeared (crt.sh answered only once; it was down for hours afterwards, HTTP 502).
Its text is the `openssl x509 -text` form for `CN=registrolineas.com`, issued by Google Trust Services, valid 2026-09-27 to 2026-12-26.
SpiderFoot **truncates the text at 1024 characters**: serial, signature algorithm, issuer, validity and subject arrive, the extensions (including the SAN list) do not.

Success:
- A certificate whose subject CN is the target, a wildcard of it, a name under it, or (for a subdomain target) a parent domain, becomes one `x509-certificate`
  (serial number, issuer, subject, validity start/end, signature algorithm) with provenance, and a `related-to` relationship from it to the scanned domain.
- Certificates whose CN is anything else are not imported and are counted as `SSL_CERTIFICATE_RAW (not the target's)` under Unmapped.
- Names inside a certificate never become domain objects (a certificate can list other customers' names).
- At most 10 certificates are imported (most recent `Not Before` first); the rest are counted. The Note says how many were imported, over the cap, and not the target's.
- A certificate with no parseable serial or subject counts as invalid. The same serial is imported once. Existing object ids are unchanged.
- `IMPORTED_EVENTS` includes `SSL_CERTIFICATE_RAW`; the catalogue is regenerated.

Out of scope: SANs and extensions (truncated away); other `SSL_CERTIFICATE_*` types (never observed); fingerprints (no DER available); revocation or expiry alerts.

## Assumptions (approved by the user's standing instruction to proceed)

1. The STIX id of an `x509-certificate` comes from its serial number; two issuers reusing a serial would collide, which CAs do not do within an issuer. Documented, not engineered around.
2. The cap of 10 keeps a domain with hundreds of certificates readable; the Note states the count that was left out.
3. Timestamps are read from `Mon DD HH:MM:SS YYYY GMT` and written as UTC.
4. Because crt.sh was down, the live check replays the recorded real event through the real connector path (`process_message`, helper, queue, worker).

## Commands

```bash
cd connector && . .venv/bin/activate
python tools/build_catalogue.py
pytest && ruff check . && ruff format --check .
```

## Test strategy

Unit with certificate text in the real shape on reserved names: fields, wildcard, name under the target, parent for a subdomain target, foreign CN, truncated text, missing fields, duplicates, cap and ordering, Note line, relationship, determinism, no domain objects from names.
Real data: map the recorded event; compare ids with the old mapper. Live: replay the real event into OpenCTI and read the certificate and its relationship back.

## Boundaries

**Always**: tie a certificate to the target by its subject CN; report what was left out.
**Ask first**: creating objects from SAN names; fetching certificates directly.
**Never**: import a certificate whose subject is not the target or a name under it; create domain objects from certificate names.
