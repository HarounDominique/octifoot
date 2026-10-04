# Archive: spiderfoot-connector

Closed 2026-10-04 · Spec: [SPEC-spiderfoot-connector.md](../specs/SPEC-spiderfoot-connector.md) · Reflection: [reflection/spiderfoot-connector.md](../reflection/spiderfoot-connector.md)

## What was built

An OpenCTI `INTERNAL_ENRICHMENT` connector that runs a passive SpiderFoot scan on a
`Domain-Name` observable and imports subdomains, IPs and emails as STIX 2.1 objects with
provenance, plus a pinned Docker Compose stack (OpenCTI CE 7.261002.0, SpiderFoot v4.0,
the connector).

- `connector/`: `allowlist`, `config` (fail-fast), `mapper`, `client`, `connector`, Dockerfile; 51 tests
- `deploy/`: Compose, `.env.example`, own SpiderFoot Dockerfile
- `docs/README.md`: usage, authorization policy, mapping table, E2E checklist

Verified live: registration, real scan of an owner-provided domain, refusal of a
non-allowlisted domain with no scan started, no duplicates on re-run, Compose refusing an empty allowlist.

## Deviations accepted

- SpiderFoot `usecase` is case-sensitive; client translates `passive` → `Passive`.
- Upstream SpiderFoot `v4.0` Dockerfile no longer builds; replaced with `deploy/spiderfoot/Dockerfile` on the same tag.
- Compose trimmed versus OpenCTI's official file; Elasticsearch 2G.
- Review gate ran inline; no `agent-rules/` existed to check against.

## Not done / next

- Next iteration: map `MALICIOUS_IPADDR`, `MALICIOUS_COHOST`, `MALICIOUS_SUBNET`, then `AFFILIATE_EMAILADDR`, `IPV6_ADDRESS` (needs spec update first).
- Spec "Future": iterative investigation loop (allowlist propagation, depth limits, scan dedupe); non-CTI entities.
- Partial-results-on-timeout path covered by integration tests only, not exercised live.
