# SPEC: fix-infra-attribution

Status: approved
Extends: [SPEC-reputation-and-infra-notes.md](SPEC-reputation-and-infra-notes.md) (the `Infrastructure` line), [SPEC-key-findings.md](SPEC-key-findings.md)

## Objective

Stop attributing a provider's DNS, mail and registrar records to the scanned domain.

Defect (found with `dig`): bugoverflow.com has no MX (NOERROR, zero answers). The scan also resolved `dinaserver.com` (the domain a CNAME points to); its
`PROVIDER_MAIL mail.dinaserver.com`, four `PROVIDER_DNS` and one `DOMAIN_REGISTRAR` events carried `source_data = dinaserver.com`, and were shown as the target's in the `Infrastructure` line.
The mail-without-SPF key finding fired on that wrong mail host.

Success:
- `DOMAIN_REGISTRAR`, `PROVIDER_DNS`, `PROVIDER_MAIL` count only when `source_data` is the target or a parent domain of it; others are counted as `<TYPE> (not the target's)` under Unmapped.
- `PROVIDER_HOSTING` (whose source is an IP) counts only when that IP was imported for the target (or the source is the target/parent); event order does not matter.
- Third-party mail never triggers the mail-without-SPF finding.
- Ground truth: bugoverflow.com's Note shows no mail host and no mail finding; zonetransfer.me (real MX) keeps both.

Out of scope: records of CNAME targets as a separate, labelled fact (could be useful, not now).

## Assumptions (approved by the user's standing instruction to proceed)

1. The same source rule already used for WHOIS and TXT applies to every event type that names a domain's records.
2. Existing infrastructure tests used the target as source; they keep passing unchanged.

## Test strategy

Unit tests with the real shape (provider domain as source, parent, sibling, hosting by imported/foreign IP, order independence, finding not triggered). Real data against `dig` MX ground truth. Live: re-enrich bugoverflow.com and read the Note.

## Boundaries

**Always**: check `source_data` on every event type that carries a domain's own records.
**Never**: show a provider's records as the target's.
