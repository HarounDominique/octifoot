# SPEC: opencti-knowledge

Status: approved
Extends: [SPEC-spiderfoot-connector.md](SPEC-spiderfoot-connector.md) (connector), [SPEC-iterative-scan-loop.md](SPEC-iterative-scan-loop.md) (the loop's original "OpenCTI feeds back" idea)

## Objective

Close the loop the project started with: what SpiderFoot discovers should be read against what OpenCTI already knows. Today the connector only sends data; it never asks the platform anything. Neither SpiderFoot (no knowledge base)
nor an empty OpenCTI (no discovery) can say "this IP SpiderFoot just found already has indicators, reports or labels from your other sources". That is the unified value.

Success:
- Before sending the bundle, the connector asks OpenCTI (GraphQL, one batched query per 50 values) about the imported observables (domain names, IPs, emails) and records what **other sources** say: indicators (not revoked), reports,
  labels other than `spiderfoot:*`, and a creator other than SpiderFoot.
- Objects created by octifoot itself never count as knowledge (previous imports carry the SpiderFoot creator and its labels).
- A separate Note, `OpenCTI knowledge (queried by octifoot before this import)`, is added for the root target: one line per known observable with counts, report names (capped), labels and creator;
  or the explicit statement that none of the N imported observables is known from other sources. Its abstract carries the counts.
- An analyst-created observable with no indicator, report, label or other creator (the target itself, typically) is not "known".
- A failing query never fails the enrichment (a warning is logged and no Note is added).
- Nothing in the OpenCTI graph is modified by the lookup; no new object types.

Out of scope: acting on the knowledge (raising scores, creating indicators, expanding scans from it); expansion sub-scans (the root Note covers the merged set); AS numbers (no `value`); a "known" feed of third-party threat data.

## Assumptions (approved by the user's standing instruction to proceed)

1. The lookup uses the platform API the connector already has (`helper.api.query`) with the connector's own token; it reads only.
2. Verification needs intelligence in the platform; the local OpenCTI has none, so a labelled test indicator is created for a real IP found by earlier scans, used, and deleted, and this is recorded as a test fixture.
3. At most 5 report names per observable are shown; lines capped at 20, then "and N more".
4. "Not revoked" is read from the indicator's `revoked` flag; expiry (`valid_until`) is shown as information, not filtered.

## Commands

```bash
cd connector && . .venv/bin/activate
pytest && ruff check . && ruff format --check .
```

## Test strategy

Unit with a fake `run_query`: each kind of evidence, exclusion of SpiderFoot's own objects and labels, revoked indicators, batching, caps, the empty statement, failure isolation, no mutation.
Live: seed a test indicator for a real IP, enrich a domain whose scan imports that IP, read the knowledge Note back, delete the indicator.

## Boundaries

**Always**: exclude octifoot's own objects; read only.
**Ask first**: acting on the knowledge (scores, indicators, expansion seeds).
**Never**: count a previous SpiderFoot import as knowledge; modify existing objects during the lookup.
