# SPEC: dns-checks

Status: approved
Extends: [SPEC-key-findings.md](SPEC-key-findings.md) (mail finding), [SPEC-fix-infra-attribution.md](SPEC-fix-infra-attribution.md)

## Objective

Add what neither SpiderFoot nor OpenCTI produce: the target's own mail-authentication and DNS-hardening records, queried directly, so the Note can state DMARC, SPF strength, CAA, DNSSEC and MTA-STS
with confirmed absence instead of silence. Also make the mail finding rest on the target's authoritative MX instead of inferring it from scan events (which misled once).

Evidence (ground truth with `dig`, 2026-10-04): none of registrolineas.com, bugoverflow.com or zonetransfer.me has `_dmarc`, CAA, DS or `_mta-sts`; zonetransfer.me has MX (Google) and no SPF; the other two have no MX.
SpiderFoot never queries `_dmarc`, CAA, DS or `_mta-sts`, so none of this can come from its events. `example.com` publishes `v=spf1 -all` and `v=DMARC1;p=reject;...`, a positive control for the parsers.

Success:
- For the root target of an enrichment (never for expansion sub-scans), the connector queries MX, TXT (SPF), `_dmarc` TXT, CAA, DS and `_mta-sts` TXT for the scanned name through the normal resolver, with a short timeout.
- Each result is one of: found (value), confirmed absent (NXDOMAIN or empty answer) or unknown (timeout, SERVFAIL, resolver error). Unknown is never reported as absent.
- The Note gets `DNS checks (queried by octifoot, not by SpiderFoot): MX: ...; SPF: ...; DMARC: ...; CAA: ...; DNSSEC: ...; MTA-STS: ...` with `unknown` stated where it applies.
- Key findings (only for a name with MX): `publishes no SPF record`, `publishes no DMARC record`, `DMARC policy is p=none`, `SPF allows any sender (+all or ?all)`; no mail findings for a name without MX.
- When native facts exist they replace the event-derived SPF/mail inference; when they do not (check failed), the earlier inference remains with its DMARC disclaimer.
- A failing DNS check never fails the enrichment. No objects are added.

Out of scope: DKIM (selectors are unknowable), checking organisational-domain DMARC for subdomains (only the scanned name is queried), zone transfers, brute force, any query to hosts other than the resolver.

## Assumptions (approved by the user's standing instruction to proceed)

1. The queries are ordinary recursive DNS lookups for a name the owner has authorised, the same kind SpiderFoot's `sfp_dnsraw` already issues; they are passive.
2. `dnspython` (ISC licence) is added as a dependency; the lookup function is injectable so tests need no network.
3. Resolver timeout 5 s total per query; six queries; a total worst case of about 30 s, only when the resolver is unresponsive.
4. "Confirmed absent" means NXDOMAIN or NOERROR with no matching record; for SPF/DMARC also "TXT answered but no `v=spf1`/`v=DMARC1` record".
5. Only the scanned name is checked; DMARC inheritance from an organisational domain is not modelled and the Note says "for this name".

## Commands

```bash
cd connector && . .venv/bin/activate
pytest && ruff check . && ruff format --check .
```

## Test strategy

Unit with an injected lookup: found / absent / unknown for every record; SPF and DMARC parsing; MX-based mail rule; findings with and without native facts; wording of unknown; sub-scans skipped; failure isolation.
Ground truth: run against the three domains and `example.com`, compare each field with `dig`. Live: rebuild, enrich, read the Note back.

## Boundaries

**Always**: distinguish absent from unknown; query only the authorised scanned name.
**Ask first**: querying other hosts (authoritative servers directly, DKIM selectors).
**Never**: report unknown as absent; fail an enrichment because of a DNS check.
