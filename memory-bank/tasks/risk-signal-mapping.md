---
slug: risk-signal-mapping
spec: SPEC-risk-signal-mapping.md
status: approved
---

## Implementation Roadmap

Routing: standard (one file extended, spec fixes every design decision, no creative pass).

- [x] Phase 1 — IPv6 + feed parser: `IPV6_ADDRESS` joins the IP path; `parse_feed_event` with tests (satisfies: SPEC-risk-signal-mapping.md#objective, SPEC-risk-signal-mapping.md#style)
- [x] Phase 2 — Risk signals: `MALICIOUS_IPADDR` label + per-feed references on output IPs, subnet/co-host lines in the Note (max 20), affiliate events ignored and counted; anonymized fixture from the real scan (satisfies: SPEC-risk-signal-mapping.md#objective, SPEC-risk-signal-mapping.md#boundaries)
- [x] Phase 3 — Docs: README mapping table and rationale; live check noted as optional (satisfies: SPEC-risk-signal-mapping.md#test-strategy)

## Execution State

**Build Status**: DONE
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {2: 0, 3: 0, 4: 0}
**Last Block Rule**: none
**Can Resume**: YES

## Deviations

[Anything a build phase did differently from what the spec/plan predicted, and whether
it was accepted, and by whom.]
- Phase 3: live check against the running stack was not done: the user paused the Docker stack and asked to continue development. Covered by 68 unit/integration tests with a fixture anonymized from the real scan. To verify live: start the stack, re-enrich an owned domain, expect label `spiderfoot:malicious` on the IPs flagged by Maltiverse and the VoIPBL/Comodo lines in the Note.
- Scope change vs the user's original request (agreed before the spec): `MALICIOUS_SUBNET`/`MALICIOUS_COHOST` go to the Note instead of objects, and `AFFILIATE_EMAILADDR` stays unmapped, because real data showed they describe third parties on shared CDN infrastructure.
