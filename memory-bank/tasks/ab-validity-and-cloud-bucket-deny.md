---
slug: ab-validity-and-cloud-bucket-deny
spec: SPEC-ab-validity-and-cloud-bucket-deny.md
status: approved
---

## Implementation Roadmap

Routing: standard (small pure code, then a measurement).

- [x] Phase 1 — Validity + deny-list: `invalid_reasons`, `valid`/`invalid_reasons` in the harness report, `IMPORTED_EVENTS`, four cloud-bucket modules denied, list regenerated, coverage tests (satisfies: SPEC-ab-validity-and-cloud-bucket-deny.md#objective)
- [x] Phase 2 — Valid A/B re-run on both domains, record results (satisfies: SPEC-ab-validity-and-cloud-bucket-deny.md#test-strategy)

## Execution State

**Build Status**: COMPLETE
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {2: 1}
**Last Block Rule**: none
**Can Resume**: NO

## Deviations

**Phase 2 — valid A/B re-run (2026-10-04, `ab_scan.py --timeout 1800`, lean list of 104 modules, cloud-bucket modules denied)**

| Domain | order | full | lean | faster | identical objects | valid |
|---|---|---|---|---|---|---|
| registrolineas.com | lean→full | 503.0 s (430 ev.) scan 65BDF828 | 177.1 s (71 ev.) scan 02C50657 | 64.8 % | yes | yes |
| bugoverflow.com | full→lean | 1229.8 s (483 ev.) scan 7E44329B | 156.9 s (62 ev.) scan 9DFEE516 | 87.2 % | yes | yes |

- All four runs FINISHED, none timed out. Acceptance rule of SPEC-fast-scan-profile (identical ids, >= 30 % faster on two
  domains) is **met with valid evidence**; this retroactively supports the user's decision to make `lean` the default.
- Effect of the deny-list: registrolineas lean went from 352.5 s (with `sfp_s3bucket` and siblings) to 177.1 s.
- `full` timings vary a lot between runs (registrolineas 397.5 s then 503.0 s; bugoverflow aborted at 900 s then finished in 1229.8 s)
  because WHOIS on co-hosted sites is throttled; speedups are therefore ranges, not constants.
- Orders were `ba` and `ab` on purpose, one each; with one run per cell, order and domain effects are not separable.
- Known loss unchanged: `MALICIOUS_COHOST` lines in the Note.
- The harness fix was exercised live only on valid runs; the invalid-run path is covered by unit tests, not by a live aborted run.
