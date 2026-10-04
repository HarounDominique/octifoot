# Archive: value-assessment

Closed 2026-10-04 · Spec: [SPEC-value-assessment.md](../specs/SPEC-value-assessment.md) · Builds on: [archive/spiderfoot-ui-link.md](spiderfoot-ui-link.md)

## What was built

`docs/value-assessment.md` (linked from the README): a side-by-side comparison of SpiderFoot alone, OpenCTI alone, both by hand and octifoot, with figures computed from the project (172 event types, 46 seen, 18 imported, 104 lean modules, 383 tests, 64.8 % and 87.2 % faster),
a section on weaknesses (silent third-party failures, three attribution defects found late, partial scans, knowledge proven on a fixture, change detection under flaky sources) and the split between live-verified and unit-tested behaviour.

Verdict recorded: at least as valuable for passive, keyless domain assessment and it adds capabilities neither tool has; not yet for API-keyed sources, active modules or scheduled monitoring.

## Deviations accepted

None.

## Not done / next

- API keys (28 event types), explicit active scanning and scheduled re-scans are the three things that stand between this and parity beyond the passive keyless scope; each is an owner decision.
- Feeding the local OpenCTI with real intelligence would turn the knowledge feature from a fixture-proven mechanism into a measured one.
