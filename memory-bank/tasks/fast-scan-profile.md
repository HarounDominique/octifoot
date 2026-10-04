---
slug: fast-scan-profile
spec: SPEC-fast-scan-profile.md
status: approved
---

## Implementation Roadmap

Routing: designed-lite (module selection derived from metadata; design fixed in spec, A/B decides the default).

- [x] Phase 1 — Profiles: metadata snapshot, pure `derive_lean`, generated list, passive-only tests (satisfies: SPEC-fast-scan-profile.md#objective, SPEC-fast-scan-profile.md#boundaries)
- [x] Phase 2 — Plumbing: `SPIDERFOOT_PROFILE` config, client `modulelist`, connector wiring, compose/env (satisfies: SPEC-fast-scan-profile.md#objective, SPEC-fast-scan-profile.md#commands)
- [ ] Phase 3 — A/B harness: pure compare + CLI (satisfies: SPEC-fast-scan-profile.md#test-strategy)
- [ ] Phase 4 — Live A/B + decision: run on two domains, record times/diffs, apply acceptance rule, set default, docs (satisfies: SPEC-fast-scan-profile.md#objective)

## Execution State

**Build Status**: NOT_STARTED
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {2: 0, 3: 0, 4: 0}
**Last Block Rule**: none
**Can Resume**: YES

## Deviations

[Anything a build phase did differently from what the spec/plan predicted, and whether
it was accepted, and by whom.]
