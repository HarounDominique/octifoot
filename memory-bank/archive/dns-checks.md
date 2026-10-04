# Archive: dns-checks

Closed 2026-10-04 · Spec: [SPEC-dns-checks.md](../specs/SPEC-dns-checks.md) · Reflection: [reflection/dns-checks.md](../reflection/dns-checks.md) · Builds on: [archive/fix-infra-attribution.md](fix-infra-attribution.md)

## What was built

The connector queries the root target's own DNS (MX, SPF, `_dmarc`, CAA, DS, `_mta-sts`) with `dnspython`, distinguishing found / none / unknown, and adds `DNS checks (queried by octifoot, not by SpiderFoot)` to the Note. Mail findings now rest on the target's MX:
no SPF, no DMARC, `p=none`, `+all`/`?all`; a name with no MX (or a null MX) gets none; if the MX lookup fails the earlier event-based inference remains with its disclaimer. Sub-scans are not checked; a failing check never fails an enrichment.

- `dnschecks.py`, mapper and connector wiring, `dnspython` (ISC) added and noticed; 304 tests, `ruff` clean
- Matches `dig` on four domains (including `example.com` as a positive control); verified live on zonetransfer.me (7 MX, no SPF, no DMARC, no CAA, no DS)

## Deviations accepted

Null-MX bug found by the positive control and fixed during the build.

## Not done / next

- Unknown states, `p=none` and `+all` were not seen live.
- DKIM (selectors unknowable) and organisational-domain DMARC inheritance for subdomain targets.
- Defects found by the same live run: certificate attribution (53 real certificates rejected) and mail findings repeated on sub-scans; both addressed in following tasks.
