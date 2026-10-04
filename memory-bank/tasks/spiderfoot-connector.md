---
slug: spiderfoot-connector
spec: SPEC-spiderfoot-connector.md
status: approved
---

## Implementation Roadmap

Routing: standard (≈15 files, clear requirement; mapping decisions already fixed in spec, no creative pass needed).

- [x] Phase 1 — Scaffold: `connector/` package skeleton, `pyproject.toml` (pinned pycti, ruff, pytest), empty module files, `pytest`/`ruff` run green (satisfies: SPEC-spiderfoot-connector.md#commands, SPEC-spiderfoot-connector.md#structure)
- [x] Phase 2 — Allowlist + config: `allowlist.py` and `config.py` with fail-fast on empty allowlist, passive-by-default usecase; unit tests first incl. `evilexample.com` and trailing-dot cases (satisfies: SPEC-spiderfoot-connector.md#boundaries, SPEC-spiderfoot-connector.md#test-strategy)
- [x] Phase 3 — Mapper: `mapper.py` maps `IP_ADDRESS`, `INTERNET_NAME`, `EMAILADDR`, `AFFILIATE_INTERNET_NAME` to STIX 2.1 with provenance (Identity, score, external-reference, summary Note), counts unmapped types; fixtures from SpiderFoot JSON (satisfies: SPEC-spiderfoot-connector.md#objective, SPEC-spiderfoot-connector.md#test-strategy)
- [x] Phase 4 — SpiderFoot client: `client.py` start/poll/fetch with timeout and partial results; integration tests against fake HTTP server; confirm real endpoint shapes against pinned SpiderFoot (satisfies: SPEC-spiderfoot-connector.md#test-strategy)
- [x] Phase 5 — Connector wiring: `connector.py` + `__main__.py` on pycti `InternalEnrichmentConnector`; allowlist refusal before any client call; bundle send; `Dockerfile` (satisfies: SPEC-spiderfoot-connector.md#objective, SPEC-spiderfoot-connector.md#boundaries)
- [x] Phase 6 — Deploy: `deploy/docker-compose.yml` + `.env.example` with OpenCTI CE, SpiderFoot and connector, versions verified against registries and pinned; `docker compose config` validates (satisfies: SPEC-spiderfoot-connector.md#commands)
- [x] Phase 7 — Docs + E2E: `docs/README.md` (setup, authorization policy, mapping table, limitations, manual E2E checklist); run manual E2E on an owned domain if stack available (satisfies: SPEC-spiderfoot-connector.md#test-strategy)

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

- Phase 3 finding (verified in SpiderFoot source `sfwebui.py#startscan`): `usecase` is matched against module `group` values, which are capitalized (`Passive`, `Footprint`, `Investigate`; only `all` is lowercase). Env var stays lowercase (`SPIDERFOOT_USECASE=passive`); the phase 4 client must translate to `Passive`. Also: SpiderFoot "passive" modules can still resolve DNS for the target; document in phase 7. Accepted: no spec change needed.
- Phase 3: IPv6 events (`IPV6_ADDRESS`) are not mapped (spec lists only the four v1 types); counted as unmapped. `IP_ADDRESS` carrying an IPv6 literal would be mapped to `ipv6-addr`.
- Phase 5: Docker daemon not running on this machine, so `connector/Dockerfile` is written but not built/verified. Verify in phase 6/7 once Docker is up (needs `libmagic1` for pycti's `python-magic`; installed in the image). Refusal and scan failure are raised as exceptions so OpenCTI shows the work as failed, not silently "processed".
- Phase 6: verified against registries on 2026-10-04: `opencti/platform:7.261002.0` and `opencti/worker:7.261002.0` exist and match `pycti==7.261002.0`. No SpiderFoot image on Docker Hub, so compose builds upstream git tag `v4.0` (endpoints `startscan`/`scanstatus`/`stopscan`/`scanexportjsonmulti` and JSON export fields confirmed identical at `v4.0` and at HEAD). Deliberately omitted from OpenCTI's official compose: xtm-composer, xtm-one stack and the default data/import/export connectors (not needed for the prototype). Validated with `docker compose config` only; stack not started (no Docker daemon). `rabbitmq:4.3-management` and Silo `RELEASE.2026-09-16T00-00-00Z` pinned as in upstream; redis 8.10.1 and Elasticsearch 8.19.21 likewise.
