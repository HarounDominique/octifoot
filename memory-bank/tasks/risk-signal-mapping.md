---
slug: risk-signal-mapping
spec: SPEC-risk-signal-mapping.md
status: approved
---

## Implementation Roadmap

Routing: standard (one file extended, spec fixes every design decision, no creative pass).

- [x] Phase 1 — IPv6 + feed parser: `IPV6_ADDRESS` joins the IP path; `parse_feed_event` with tests (satisfies: SPEC-risk-signal-mapping.md#objective, SPEC-risk-signal-mapping.md#style)
- [ ] Phase 2 — Risk signals: `MALICIOUS_IPADDR` label + per-feed references on output IPs, subnet/co-host lines in the Note (max 20), affiliate events ignored and counted; anonymized fixture from the real scan (satisfies: SPEC-risk-signal-mapping.md#objective, SPEC-risk-signal-mapping.md#boundaries)
- [ ] Phase 3 — Docs: README mapping table and rationale; live check noted as optional (satisfies: SPEC-risk-signal-mapping.md#test-strategy)

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
