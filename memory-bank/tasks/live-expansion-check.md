---
slug: live-expansion-check
spec: SPEC-live-expansion-check.md
status: approved
---

## Implementation Roadmap

Routing: verification only.

- [x] Phase 1 — Live run: enrich bugoverflow.com with depth 1, read work, Note and discovered list back (satisfies: SPEC-live-expansion-check.md#objective)

## Execution State

**Build Status**: COMPLETE
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {1: 1}
**Last Block Rule**: none
**Can Resume**: NO

## Deviations

**Result (2026-10-04, OpenCTI 7.261002.0, connector with `SPIDERFOOT_MAX_DEPTH=1`, `SPIDERFOOT_MAX_SCANS=5`, profile `lean`)**

- Work `work_68301203-..._2026-10-04T11:49:41.455Z` for observable bugoverflow.com: `complete`, 20 of 20 objects processed, no errors, 7 min 4 s, one SpiderFoot scan `E1E0F7E5`.
- Expansion Note present: "scans run: 1, max depth reached: 0. Failed sub-scans: none. Skipped, outside the allowlist (never scanned): redirecciones.dinaserver.com. Skipped, over the scan budget: none."
- **Verified live:** the loop runs, reads the scan's events, applies the allowlist (a real discovered hostname outside it was refused and never scanned), reports skips, and finishes cleanly.
- **Not verified live:** the success path (scanning allowlisted subdomains). Recomputing the discovered list from the exported events of all four scans on the two test domains gives no allowlisted subdomain (`registrolineas.com`: none, behind Cloudflare; `bugoverflow.com`: only `redirecciones.dinaserver.com`). Forcing it would mean authorizing a third-party domain, which was not done.
- To close it: allowlist a domain you own that has public subdomains and enrich it with depth 1.

**Second attempt (2026-10-04) on `zonetransfer.me`, a domain published by its owner for security training** (allowlisted for the test, depth 1, max 5 scans, profile `lean`)

- Work complete, 42/42 objects, no errors, 3 min 34 s, one SpiderFoot scan `0115B5B0`. Expansion Note: "scans run: 1, max depth reached: 0, skipped outside the allowlist: none, over budget: none".
- The domain has public subdomains (`www`, `office`, `dc-office`, `vpn`, `owa`, `staging`, `testing` resolve), but the scan returned only `zonetransfer.me` as `INTERNET_NAME`: the success path was **again not exercised**.
- Cause, read from the scan log and by probing: every passive subdomain source was unavailable or empty. `crt.sh` answered **HTTP 502** from the host and from the SpiderFoot container (12 retries over about 6 minutes, never 200) and `sfp_crt` reports it as "No certificate transparency info found"; `sfp_sublist3r` "Bad response code None from Sublist3r API"; `sfp_commoncrawl` "index collection doesn't seem to be available"; `sfp_crobat_api` "Failed to retrieve content"; `sfp_dnsgrep` no records. The subdomains here are only reachable by a zone transfer or brute force, which are active modules and are not in `lean`.
- Consequence: a scan can finish successfully with zero subdomains because upstream sources failed, without anything in the OpenCTI Note saying so.
- Not done on purpose: switching to an active use case (`SPIDERFOOT_ALLOW_ACTIVE`) to force a zone transfer. It would run invasive modules against third-party IPs that the zone points to and break the passive-only promise of the README.
- To close it: retry when crt.sh is back (a 3-4 minute run), or use a domain you own whose subdomains have public certificates.
