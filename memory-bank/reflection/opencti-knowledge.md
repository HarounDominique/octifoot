# Reflection: opencti-knowledge

Date: 2026-10-04 · Spec: SPEC-opencti-knowledge.md (approved) · Plan: 2 phases DONE · Live check: replay of a recorded scan through the real helper against a platform seeded with a test indicator that was then removed

## Implementation vs spec

| Spec requirement | Result |
|---|---|
| One batched read-only query per 50 values, before sending the bundle | Met; live through the real `helper.api.query` |
| Only other sources count (indicators not revoked, reports, non-`spiderfoot:*` labels, other creators); own objects never | Met (tests, and live: our own IP/domain objects were ignored) |
| Separate Note on the root target with one line per known observable, or an explicit "none" | Met; live: `1 of 2 observables already known` |
| Analyst-created observable with nothing attached is not known | Met live (the target) |
| A failing lookup never fails the enrichment; nothing modified | Met (tests) |

Deviations: none from the spec; a cleanup slip fixed (see task file).

## Why this matters

This is the first time the connector reads the platform. Until now data flowed one way. With intelligence in OpenCTI (feeds, analysts, reports), each enrichment now says which of the freshly discovered observables are already tracked and by whom, which is a question neither SpiderFoot (no memory)
nor an empty OpenCTI (no discovery) can answer. In this local platform there is no real intelligence, so the live check proves the mechanism with a labelled fixture, not the value on real data.

## Workflow evaluation

- Probing the real schema first avoided building on a guessed query shape.
- The fixture approach (seed, use, delete, verify) is the only way to test a feature whose value depends on data the platform does not have; the verification of deletion caught that my first cleanup had silently not worked.
- Honest limit: I cannot show the value on real intelligence until the platform is fed (for example with public threat feeds), and the connector deliberately does not act on the knowledge.

## Rules extracted

- New `after-cleaning-test-data-query-to-prove-it-is-gone` (deployment).
- Reinforced: `inspect-real-output-before-specifying-a-mapping` (evidence 6; here the real API shape).

## Follow-ups (not blocking)

- Feed the local OpenCTI with real public threat intelligence to see the lookup on real overlaps.
- Acting on knowledge (score, expansion seeds) needs its own spec and is "ask first".
