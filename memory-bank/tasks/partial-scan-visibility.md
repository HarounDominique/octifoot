---
slug: partial-scan-visibility
spec: SPEC-partial-scan-visibility.md
status: approved
---

## Implementation Roadmap

Routing: fix.

- [x] Phase 1 — Failing tests, finding in the Note, connector wiring (satisfies: SPEC-partial-scan-visibility.md#objective)
- [x] Phase 2 — Real data, docs, live check with a forced short timeout (satisfies: SPEC-partial-scan-visibility.md#test-strategy)

## Execution State

**Build Status**: COMPLETE
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {1: 1, 2: 1}
**Last Block Rule**: none
**Can Resume**: NO

## Deviations

- Earlier notes that relied on the Notes of the aborted scan `06410167` (WHOIS, DNS and certificate checks of zonetransfer.me) described partial data; their conclusions were re-checked against `dig` and the complete scans and stand, but they did not say the scan was partial. Recorded here and in the reflection.
- The decision not to change SpiderFoot's global module options (certificate fetching) or the default timeout is deliberate: the owner can raise `SPIDERFOOT_TIMEOUT_SECONDS`; the evidence is in the spec.

**Root cause of the long scan (scan log of `06410167`, 51,310 rows over 923 s):** `sfp_crt` fetched certificates one at a time from 9 s to 902 s and each certificate's names produced co-hosted-site events that every module processed;
crt.sh had recovered and returned 53 certificates. The scan ended `ABORTED` at the 900 s limit.

**Real data:** the aborted scan, mapped with status ABORTED and a 900 s timeout, gets `scan incomplete: stopped after 900 s, results are partial (SPIDERFOOT_TIMEOUT_SECONDS)` as its first finding; the finished sub-scan `0CA6AE42` gets none.

**Live check (2026-10-04, connector rebuilt from this branch, temporarily run with `SPIDERFOOT_TIMEOUT_SECONDS=25`):** enrichment of registrolineas.com, scan `30B41FA2`, SpiderFoot status `ABORTED`, work complete 12/12 (partial results imported).
The Note read back from OpenCTI starts `Key findings (as of this scan): - scan incomplete: stopped after 25 s, results are partial (SPIDERFOOT_TIMEOUT_SECONDS)`.
The connector was then recreated without the override and confirmed back at 900 s.
Not seen live: the "ended <STATUS>, not FINISHED" wording (unit-tested).
