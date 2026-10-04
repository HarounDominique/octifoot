---
slug: fix-cert-and-mail-attribution
spec: SPEC-fix-cert-and-mail-attribution.md
status: approved
---

## Implementation Roadmap

Routing: fix (defects in shipped behaviour, found by live data).

- [x] Phase 1 — Failing tests, certificate attribution by query source, newest-per-CN expiry finding, exact-source mail fallback (satisfies: SPEC-fix-cert-and-mail-attribution.md#objective)
- [x] Phase 2 — Docs, real data, live replay of the 53-certificate scan (satisfies: SPEC-fix-cert-and-mail-attribution.md#test-strategy)

## Execution State

**Build Status**: COMPLETE
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {1: 1, 2: 1}
**Last Block Rule**: none
**Can Resume**: NO

## Deviations

- The spec predicted `10 imported, 43 over the cap`: it assumed 53 distinct certificates. The 53 events are 34 distinct serials (crt.sh returns precertificate/leaf pairs), so the real figure is `10 imported, 24 over the cap`. Corrected here.
- A scripted edit stopped halfway when ruff had reformatted a line my pattern expected on one line, leaving inconsistent code and 17 failing tests; I re-read the file and applied the remaining edits one by one. No wrong state was committed.
- Amends the x509 spec's boundary (see the note appended there).

**Real data (recorded live scan `06410167`, zonetransfer.me, 53 certificate events):** 10 `x509-certificate` imported (all CN `alertlab.digi.ninja`, six Let's Encrypt issuers), `10 imported, 24 over the cap of 10, 0 not issued for the target`.
The sub-scan `0CA6AE42` (`www.zonetransfer.me`) imports none and repeats no mail finding.

**Live check (2026-10-04, connector rebuilt from this branch):** the recorded scan was replayed through `process_message` with the real helper, queue and worker. OpenCTI shows 10 `X509-Certificate` objects referencing scan `06410167`, each `related-to zonetransfer.me`,
and two Notes: the root one (`10 imported, 24 over the cap of 10, 0 not issued for the target`) and one for the mocked expansion sub-scan of `www.zonetransfer.me` (`0 imported, 0 over the cap of 10, 53 not issued for the target`), the exact-source rule at work.
Not seen live: the certificate expiry finding on real data (the newest certificate was healthy).
