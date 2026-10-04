---
slug: spiderfoot-connector
spec: SPEC-spiderfoot-connector.md
status: approved
---

## Implementation Roadmap

Routing: standard (≈15 files, clear requirement; mapping decisions already fixed in spec, no creative pass needed).

- [ ] Phase 1 — Scaffold: `connector/` package skeleton, `pyproject.toml` (pinned pycti, ruff, pytest), empty module files, `pytest`/`ruff` run green (satisfies: SPEC-spiderfoot-connector.md#commands, SPEC-spiderfoot-connector.md#structure)
- [ ] Phase 2 — Allowlist + config: `allowlist.py` and `config.py` with fail-fast on empty allowlist, passive-by-default usecase; unit tests first incl. `evilexample.com` and trailing-dot cases (satisfies: SPEC-spiderfoot-connector.md#boundaries, SPEC-spiderfoot-connector.md#test-strategy)
- [ ] Phase 3 — Mapper: `mapper.py` maps `IP_ADDRESS`, `INTERNET_NAME`, `EMAILADDR`, `AFFILIATE_INTERNET_NAME` to STIX 2.1 with provenance (Identity, score, external-reference, summary Note), counts unmapped types; fixtures from SpiderFoot JSON (satisfies: SPEC-spiderfoot-connector.md#objective, SPEC-spiderfoot-connector.md#test-strategy)
- [ ] Phase 4 — SpiderFoot client: `client.py` start/poll/fetch with timeout and partial results; integration tests against fake HTTP server; confirm real endpoint shapes against pinned SpiderFoot (satisfies: SPEC-spiderfoot-connector.md#test-strategy)
- [ ] Phase 5 — Connector wiring: `connector.py` + `__main__.py` on pycti `InternalEnrichmentConnector`; allowlist refusal before any client call; bundle send; `Dockerfile` (satisfies: SPEC-spiderfoot-connector.md#objective, SPEC-spiderfoot-connector.md#boundaries)
- [ ] Phase 6 — Deploy: `deploy/docker-compose.yml` + `.env.example` with OpenCTI CE, SpiderFoot and connector, versions verified against registries and pinned; `docker compose config` validates (satisfies: SPEC-spiderfoot-connector.md#commands)
- [ ] Phase 7 — Docs + E2E: `docs/README.md` (setup, authorization policy, mapping table, limitations, manual E2E checklist); run manual E2E on an owned domain if stack available (satisfies: SPEC-spiderfoot-connector.md#test-strategy)

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
