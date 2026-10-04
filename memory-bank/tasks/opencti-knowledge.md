---
slug: opencti-knowledge
spec: SPEC-opencti-knowledge.md
status: approved
---

## Implementation Roadmap

Routing: standard.

- [x] Phase 1 — `knowledge.py` (query, evidence rules, Note text), connector wiring, tests (satisfies: SPEC-opencti-knowledge.md#objective, SPEC-opencti-knowledge.md#boundaries)
- [x] Phase 2 — Docs, live check with a seeded and then removed test indicator (satisfies: SPEC-opencti-knowledge.md#test-strategy)

## Execution State

**Build Status**: COMPLETE
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {1: 1, 2: 1}
**Last Block Rule**: none
**Can Resume**: NO

## Deviations

- First GraphQL attempt failed on the filter variable type (`[Any!]!`, not `[String!]`); found by probing the real schema before writing the code, not by a test.
- A lint import-order error and a missed `noqa` for a deliberate broad `except` fixed before commit.
- Cleanup mistake: my first attempt to delete the test indicator used a mutation that does not exist (`indicatorEdit`; the right one is `indicatorDelete`) and the verification query showed the indicator still existed.
  Re-done with the correct mutation and verified (no indicator, label or Note left).

**Test fixture (2026-10-04, local OpenCTI only, now removed):** label `octifoot-test-fixture` and an indicator `TEST FIXTURE (octifoot): not real intelligence`, pattern `[ipv4-addr:value = '5.196.105.14']`, score 80, created for a real IP found by earlier scans, plus the knowledge Note the replay produced. All three deleted; verification queries returned zero indicators, labels and Notes mentioning the fixture.

**Real data:** against the real (empty) platform, `query_known` over the imported values of earlier scans returns nothing (our own SpiderFoot objects and labels are excluded).

**Live check (2026-10-04, connector rebuilt from this branch):** the recorded scan `A074967B` was replayed through `process_message` with the real helper and `helper.api.query`. The Note read back from OpenCTI:
abstract `OpenCTI knowledge before this import: 1 of 2 observables already known`, content `- 5.196.105.14 (IPv4-Addr): 1 indicator (highest score 80); labels: octifoot-test-fixture`; the analyst-created target `zonetransfer.me` was correctly not counted.
Not seen live: reports and other-creator evidence (unit-tested), the 50-value batching and the 20-line cap on real data, the "none known" wording on a real run.
