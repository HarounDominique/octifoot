---
slug: fast-scan-profile
spec: SPEC-fast-scan-profile.md
status: approved
---

## Implementation Roadmap

Routing: designed-lite (module selection derived from metadata; design fixed in spec, A/B decides the default).

- [x] Phase 1 — Profiles: metadata snapshot, pure `derive_lean`, generated list, passive-only tests (satisfies: SPEC-fast-scan-profile.md#objective, SPEC-fast-scan-profile.md#boundaries)
- [x] Phase 2 — Plumbing: `SPIDERFOOT_PROFILE` config, client `modulelist`, connector wiring, compose/env (satisfies: SPEC-fast-scan-profile.md#objective, SPEC-fast-scan-profile.md#commands)
- [x] Phase 3 — A/B harness: pure compare + CLI (satisfies: SPEC-fast-scan-profile.md#test-strategy)
- [x] Phase 4 — Live A/B + decision: run on two domains, record times/diffs, apply acceptance rule, set default, docs (satisfies: SPEC-fast-scan-profile.md#objective)

## Execution State

**Build Status**: NOT_STARTED
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {2: 0, 3: 0, 4: 0}
**Last Block Rule**: none
**Can Resume**: YES

## Deviations

**Phase 4 — live A/B (2026-10-04, OpenCTI + SpiderFoot v4.0, passive, `tools/ab_scan.py`)**

| Domain | order | full | lean | faster | identical objects |
|---|---|---|---|---|---|
| registrolineas.com | full→lean | 397.5 s (431 ev.) scan A0852CDD | 352.5 s (71 ev.) scan E664397D | 11 % | yes |
| bugoverflow.com | lean→full | 904.0 s (452 ev.) scan 635DE72C | 377.6 s (62 ev.) scan 5041B7B8 | 58 % | yes |

- Acceptance rule (identical ids, >= 30 % faster on two domains) **not met**: only bugoverflow.com passes.
- Dropped events are the discarded third-party ones (CO_HOSTED_SITE*, AFFILIATE_EMAILADDR, COUNTRY_NAME).
  Known loss: MALICIOUS_COHOST lines in the Note (listed 10→2 and 6→0).
- Caveat: bugoverflow full ran 904 s against a 900 s harness timeout, so it may have been cut off and
  the 58 % inflated. Not verified. registrolineas lean stayed at 352 s with 71 events, so a module still
  in the lean list likely dominates; not investigated.
- **Deviation, accepted by the user (Dominique Haroun) on 2026-10-04:** `lean` is the default despite the
  rule, judging 58 % on the larger domain and 11 % on the other worth it. Default is `lean` only with
  `SPIDERFOOT_USECASE=passive`; any other use case keeps `full`. `full` stays selectable.
