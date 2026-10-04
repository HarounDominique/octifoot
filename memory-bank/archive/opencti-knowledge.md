# Archive: opencti-knowledge

Closed 2026-10-04 · Spec: [SPEC-opencti-knowledge.md](../specs/SPEC-opencti-knowledge.md) · Reflection: [reflection/opencti-knowledge.md](../reflection/opencti-knowledge.md) · Builds on: [archive/iterative-scan-loop.md](iterative-scan-loop.md)

## What was built

Before sending the bundle, the connector queries OpenCTI (read-only, batched by 50) about the imported domain names, IPs and emails and adds a Note, `OpenCTI knowledge (queried by octifoot before this import; ...)`, on the root target: what other sources attach
(non-revoked indicators with their highest score, reports, labels other than `spiderfoot:*`, other creators) or an explicit "none". Octifoot's own objects never count; the lookup modifies nothing and never fails an enrichment.

- `knowledge.py`, connector wiring through `helper.api.query`; 337 tests, `ruff` clean; README section
- Verified live by replaying a recorded scan: the IP with a seeded test indicator was reported (`1 of 2 observables already known`), the analyst's own target was not. The test fixture (indicator, label, Note) was deleted and its removal verified

## Deviations accepted

None. A cleanup mistake (wrong delete mutation) was caught by the verification query and redone.

## Not done / next

- No real intelligence in the local platform: the value on real overlaps is unproven; feed it with public threat intelligence to see it.
- Acting on knowledge (scores, expansion seeds) is "ask first" and not built.
- Reports and other-creator evidence, batching and caps were not seen live.
