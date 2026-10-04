# SPEC: drop-affiliate-names

Status: approved
Extends: [SPEC-spiderfoot-connector.md](SPEC-spiderfoot-connector.md) (mapping table), [SPEC-risk-signal-mapping.md](SPEC-risk-signal-mapping.md) (shared infrastructure is never attributed to the target)

## Objective

Stop importing `AFFILIATE_INTERNET_NAME` as `domain-name` objects related to the target. They are other parties' hostnames, not the target's.

Evidence (the six scans of 2026-10-04 that were mapped, plus the three most recent):
- Of the domain objects that are not the target itself, **2 of 2** (registrolineas.com), **5 of 6** (bugoverflow.com) and **17 of 17** (zonetransfer.me) came from `AFFILIATE_INTERNET_NAME`.
- In zonetransfer.me they were Google's MX hosts (`aspmx.l.google.com`...), eight `*.1e100.net` reverse-DNS names of Google IPs, and the two name servers: all "related-to" the target at half score.
- The same MX and name-server hosts are already reported, more clearly, in the `Infrastructure` Note line.
- This is the same reasoning already applied to affiliate emails and IPs: attributing a third party's data to the target is misleading.

Success:
- `AFFILIATE_INTERNET_NAME` produces no object and no relationship; it is counted under "Unmapped event types" in the Note.
- `INTERNET_NAME` mapping is unchanged (same ids, same score, same relationship), and so is every other object.
- A name that is both an `INTERNET_NAME` and an `AFFILIATE_INTERNET_NAME` is still imported (the target's own event wins).
- An IP whose source host is an affiliate hostname that is not imported is not linked to the target; it is counted instead.
- `mapper.IMPORTED_EVENTS` no longer lists `AFFILIATE_INTERNET_NAME`, and the profile coverage test still passes.

Out of scope: deleting objects already imported by earlier scans (OpenCTI keeps them); deny-listing modules that now only feed affiliates (needs an A/B, see below);
`AFFILIATE_DOMAIN_NAME` (already unmapped).

## Assumptions (approved by the user's standing instruction to proceed)

1. The user decided on 2026-10-04 to stop importing `AFFILIATE_INTERNET_NAME`.
2. Previously imported affiliate objects stay in OpenCTI; they remain harmless and carry their SpiderFoot provenance.
3. Real scans showed no `IP_ADDRESS` event sourced from an affiliate hostname (0 of 7 scans), so the guard is defensive; SpiderFoot emits `AFFILIATE_IPADDR` for those.
4. Score halving for affiliates (`AFFILIATE_SCORE_DIVISOR`) is removed with its only use.
5. Modules that only produce affiliate names (some of the co-hosted chain still in `lean`) may now be wasted time; whether to deny them is a separate A/B decision, not made here.

## Commands

```bash
cd connector && . .venv/bin/activate
pytest && ruff check . && ruff format --check .
```

## Test strategy

- Unit: affiliate names not imported and counted; own names unchanged; own-and-affiliate name imported; IP from affiliate host not linked to target;
  flagged affiliate hostname counted as not imported; `IMPORTED_EVENTS`/`DOMAIN_EVENTS`; the existing mapper tests updated where they asserted affiliate objects.
- Real data: old versus new mapper on recorded events of the three domains, object ids identical except the affiliate domains and their relationships.
- Live: rebuild, enrich a real domain, read the Note and observables back.

## Boundaries

**Always**: keep affiliate data out of the target's graph; count what is not imported.
**Ask first**: deleting already-imported objects; denying more modules.
**Never**: link an IP to the target because its real source host was dropped.
