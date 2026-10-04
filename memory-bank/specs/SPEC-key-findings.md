# SPEC: key-findings

Status: approved
Extends: [SPEC-whois-dns-notes.md](SPEC-whois-dns-notes.md), [SPEC-x509-certificates.md](SPEC-x509-certificates.md), [SPEC-source-health-note.md](SPEC-source-health-note.md), [SPEC-reputation-and-infra-notes.md](SPEC-reputation-and-infra-notes.md)

## Objective

The scan Note is now a list of facts (infrastructure, WHOIS, TXT, certificates, reputation, source errors). An analyst still has to read all of it to learn what matters.
Add a `Key findings` block at the top of the Note that says what is notable in that data, derived by fixed rules, each tied to the evidence behind it. This is synthesis neither SpiderFoot's
raw output nor an empty OpenCTI provides.

Evidence (real scans, 2026-10-04; ground truth checked with `dig`):
- registrolineas.com was registered 7 days before the scan; the Note shows the date but not that it matters.
- bugoverflow.com and zonetransfer.me receive mail (MX present) and publish no SPF record (dig confirms; SpiderFoot reported none either), a spoofing exposure worth stating.
- SpiderFoot does not query `_dmarc.<domain>`, so DMARC absence cannot be asserted from its data; the block must not claim it.
- With subdomain sources failing (Sublist3r, CommonCrawl, Crobat) a scan with no subdomains is not evidence of none; the source-health line holds it, the findings block should say it.

Success (each finding appears only when its evidence is present; otherwise it is absent):
1. **Flagged**: the target or imported hostnames/IPs carry the malicious label: `N hostname(s)/IP(s) flagged malicious by <feeds>: <values>`.
2. **Mail without SPF**: mail hosts known (MX/provider mail) and DNS TXT records were returned for the target (`RAW_DNS_RECORDS` for it), but no `v=spf1` record: `receives mail (MX: ...) but publishes no SPF record`.
3. **Certificate**: an imported certificate that is expired at scan time, or expires within 14 days: `certificate for <CN> expired on ... / expires in N days`.
4. **Newly registered**: created less than 30 days before the scan: `registered N days ago`.
5. **Registration expiring**: expires within 30 days of the scan: `registration expires in N days`.
6. **Shared infrastructure listed**: reputation lists naming subnets or co-hosts: `N reputation listings on shared infrastructure (not the target's own)`.
7. **Coverage**: subdomain-producing sources of the lean profile that reported errors: `subdomain discovery may be incomplete: <modules> reported errors (sfp_crt cannot report outages)`.
- The block is `Key findings (as of this scan):` followed by `- ` lines, flagged first; with nothing notable it reads `Key findings: nothing notable in the data the answering sources returned.` (never "clean").
- The block never changes objects; thresholds are constants; no finding claims DMARC, DKIM or anything not observed.

Out of scope: scoring or labelling objects from findings (labels such as "newly registered" go stale); DMARC/DKIM checks (own source, later); alerting.

## Assumptions (approved by the user's standing instruction to proceed)

1. The user delegated engineering judgment to the CTO role on 2026-10-04 ("apruebo tu criterio y condiciones").
2. Thresholds: newly registered 30 days, registration expiring 30 days, certificate expiring 14 days.
3. "Subdomain sources" are the lean-profile modules whose produced events include `INTERNET_NAME`, from SpiderFoot's own metadata.
4. Findings are text in the existing Note, placed right after its first line, so existing line consumers keep working.

## Commands

```bash
cd connector && . .venv/bin/activate
pytest && ruff check . && ruff format --check .
```

## Test strategy

Unit: each finding present with its evidence and absent without it; the SPF rule's guards (no MX, no DNS answer, SPF present); ordering; the empty wording; no change to objects; determinism.
Real data: the three domains' recorded events (findings must match the ground truth above). Live: enrich and read the block back.

## Boundaries

**Always**: tie every finding to observed data; say "as of this scan".
**Ask first**: labels or scores derived from findings.
**Never**: assert DMARC/DKIM absence; call a scan "clean".
