# SPEC: fix-cert-and-mail-attribution

Status: approved
Extends: [SPEC-x509-certificates.md](SPEC-x509-certificates.md) (amends its attribution rule), [SPEC-key-findings.md](SPEC-key-findings.md), [SPEC-dns-checks.md](SPEC-dns-checks.md)

## Objective

Fix two defects exposed by the first live run in which crt.sh answered and the expansion ran (zonetransfer.me, 2026-10-04):

1. **Certificates wrongly rejected.** crt.sh returned 53 certificates for `zonetransfer.me`; all were reported "not issued for the target". Their CN is `digi.ninja` or `alertlab.digi.ninja` (the owner's other
   domains); `zonetransfer.me` is a SAN, which SpiderFoot truncates (both its export and its stored events stop at 1024 characters). The CN-only rule of `x509-certificates` rejected 100 % of the real certificates.
2. **Mail finding repeated on sub-scans.** The `www.zonetransfer.me` sub-scan Note repeated "receives mail ... no SPF" from the parent zone's records (event-based fallback with a parent-allowed source), duplicating the root finding.

Evidence: upstream `sfp_crt` (v4.0) queries crt.sh for `%.<name>` of an `INTERNET_NAME`/`DOMAIN_NAME` event and emits one `SSL_CERTIFICATE_RAW` per returned certificate with `source_data` = the name queried.
Every returned certificate therefore carries that name in its subject or SAN; a certificate listing the target in its SAN is a certificate for the target. The real risk the CN rule guarded against is other customers'
names inside a shared certificate; that is contained by never creating objects from names inside certificates.

Success:
- A certificate is the target's when its event's `source_data` **is the scanned name** (exact) or its CN covers the target (CN rule as before, including a wildcard or parent CN). Parent-sourced certificates with another CN are not imported into a sub-scan.
- Everything else stays as specified: related-to the scanned domain, no objects from names inside, cap of 10 newest, the Note line.
- The certificate key finding looks only at the **newest** certificate per subject CN (older, expired certificates are normal rotation history): `certificate for <CN> expired on ...` / `expires in N days` only for that newest one.
- The event-based mail fallback uses only mail and DNS events whose source is exactly the scanned name, never a parent; with native DNS facts nothing changes.
- Replaying the recorded real scan `06410167` (53 certificates) imports 10 certificates and reports `10 imported, 43 over the cap of 10, 0 not issued for the target`.

Out of scope: SAN parsing (the text is truncated upstream); certificate fetching by the connector.

## Assumptions (approved by the user's standing instruction to proceed)

1. The amendment of the x509 spec (accept by query source) is a deliberate CTO decision backed by the evidence above; the spec's old Boundary "never import a certificate whose subject is not the target" is replaced by "never create objects from names inside certificates".
2. Parent-allowed sources stay for WHOIS, TXT, registrar, DNS and mail in the `Infrastructure` line (registered-domain facts are relevant to subdomains); only certificates and the mail finding become exact.

## Test strategy

Unit: SAN-style certificate accepted by source; foreign-source certificate with foreign CN rejected; parent-sourced certificate with a foreign CN rejected for a subdomain target; newest-per-CN expiry logic; exact-source mail fallback.
Real data: map the recorded scan `06410167` and the sub-scan `0CA6AE42`. Live: replay `06410167` through the connector path and read the certificates back from OpenCTI.

## Boundaries

**Always**: say what the attribution rests on (the name crt.sh was queried for).
**Never**: create domain objects from names inside a certificate; report old expired certificates as a current problem.
