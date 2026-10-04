# Reflection: spiderfoot-connector

Date: 2026-10-04 · Spec: SPEC-spiderfoot-connector.md (approved) · Plan: 7 phases, all DONE · Manual E2E: passed

## Implementation vs spec

| Spec requirement | Result |
|---|---|
| Domain-Name enrichment via SpiderFoot, STIX 2.1 with provenance | Met. E2E on an owner-provided domain: 436 events → 11 objects, Identity/score/external-reference/Note present |
| Allowlist refusal before any SpiderFoot call | Met and proven live: refused work shows the error in OpenCTI, SpiderFoot scan list stayed empty |
| Empty allowlist → no start | Met twice: `ConfigError` in the connector, `:?` in Compose |
| Passive by default, active needs opt-in | Met (`SPIDERFOOT_ALLOW_ACTIVE`) |
| No duplicates on re-run | Met live: second scan left the same 6 observables and 4 relationships |
| Partial results on timeout | Met in integration tests only; not exercised live (scan finished in ~7 min of 15) |
| Pinned versions | Met; OpenCTI/pycti verified in lockstep (7.261002.0) |

Deviations (all accepted, none needed a spec change):
- SpiderFoot's `usecase` is case-sensitive against capitalized module groups; the client translates. Found by reading upstream source in phase 3, before any test could have passed on a wrong assumption.
- Upstream SpiderFoot `v4.0` Dockerfile no longer builds; replaced by `deploy/spiderfoot/Dockerfile` (same tag, relaxed `pyyaml` pin). Found only at E2E.
- Compose trimmed versus OpenCTI's official file (no xtm-one/composer/default connectors); Elasticsearch at 2G for a 7.6 GiB Docker VM.
- Review gate (step 4) ran inline without a subagent; `agent-rules/` was empty so there was nothing to check beyond the spec's Boundaries.

Open at close: mapping of `MALICIOUS_*`, `AFFILIATE_EMAILADDR`, `IPV6_ADDRESS` (user scheduled it for the next iteration); iterative phase 3 loop (spec "Future").

## Workflow evaluation

- Routing: "standard" fit. Mapping design decisions were already in the spec, so skipping `/seed:creative` cost nothing.
- Spec corrections mid-build: none required. Assumption 5 (`passive` value) was wrong at the API boundary but harmless at the config boundary; recorded as a deviation rather than a spec-sync.
- Sharding leaks: none.
- Weak spot: phases 5 and 6 reported Docker artifacts as written but unverified because the daemon was down; the first real build failure (SpiderFoot image) only surfaced at E2E, after phase 6 was marked done.
- A throwaway E2E polling script picked "latest work" instead of the work it had just created and reported a stale result; caught by reading the output, not by the script.

## Rules extracted

See `agent-rules/_learned/`: external-integrations, deployment, safety-boundaries.
