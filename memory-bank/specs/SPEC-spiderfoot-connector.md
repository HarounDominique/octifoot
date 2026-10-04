# SPEC: spiderfoot-connector

Status: draft

## Objective

Build a prototype OpenCTI `INTERNAL_ENRICHMENT` connector that enriches a `Domain-Name`
observable with passive OSINT data from SpiderFoot, and a Docker Compose environment to
run OpenCTI Community Edition + SpiderFoot + the connector locally.

For: an analyst investigating a domain they are **authorized** to investigate.

Success:
- From the OpenCTI UI, triggering the connector on an allowlisted domain produces, in
  OpenCTI, related subdomains, IPs and email addresses linked to the domain, each with
  provenance (source identity, scan id, SpiderFoot module).
- A domain outside the allowlist is refused with a clear log line and no SpiderFoot call.
- Re-running on the same domain creates no duplicate observables.

Out of scope (v1): recursive/bidirectional investigations (OpenCTI triggering new scans
from results), custom UI, person/profile/event modeling, active SpiderFoot modules,
OpenCTI Enterprise Edition features, automated E2E tests.

## Assumptions (approved)

1. Python 3.11+, `pycti` pinned to the same version as OpenCTI, `requests`, `pytest`.
2. OpenCTI CE, `pycti` and SpiderFoot versions pinned exactly; verified against registries
   at plan time.
3. `INTERNAL_ENRICHMENT`, `CONNECTOR_SCOPE=Domain-Name`, `CONNECTOR_AUTO=false`.
4. Mandatory allowlist `SPIDERFOOT_ALLOWED_DOMAINS` (domain + subdomains). Empty/missing
   allowlist → connector refuses to start. Non-allowlisted target → refused, logged.
5. Passive modules only by default (`SPIDERFOOT_USECASE=passive`); active modules need a
   separate explicit opt-in variable.
6. SpiderFoot OSS HTTP API (`/startscan`, `/scanstatus`, `/scaneventresults` or
   `/scanexportjsonmulti`), polled with configurable timeout (default 15 min); partial
   results returned on timeout and flagged.
7. v1 mapping covers only `IP_ADDRESS`, `INTERNET_NAME`, `EMAILADDR`,
   `AFFILIATE_INTERNET_NAME`; all other event types are skipped and counted in the log.
8. Provenance: `created_by_ref` Identity "SpiderFoot", low default score (30,
   configurable), `external-reference` (scan id + module), one summary Note per scan.
9. Dedupe relies on OpenCTI/STIX deterministic ids; no own datastore.
10. Tests: unit (mapping, allowlist) with JSON fixtures; integration for the SpiderFoot
    client against a fake HTTP server; E2E manual.
11. Layout below. 12. Code/comments/docs in English.

## Commands

```bash
# Dev environment
cd connector && python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"

# Tests / lint
pytest                          # unit + integration (no network, no Docker)
pytest tests/unit -q
ruff check . && ruff format --check .

# Local stack (OpenCTI CE + SpiderFoot + connector)
cp deploy/.env.example deploy/.env      # fill tokens, allowlist
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d
docker compose -f deploy/docker-compose.yml logs -f connector-spiderfoot
docker compose -f deploy/docker-compose.yml down
```

## Structure

```
connector/
  pyproject.toml
  Dockerfile
  src/spiderfoot_connector/
    __init__.py
    config.py        # env parsing, allowlist validation (fail-fast)
    allowlist.py     # is_allowed(domain, allowlist)
    client.py        # SpiderFoot HTTP client: start, poll, fetch
    mapper.py        # SpiderFoot events -> STIX 2.1 objects
    connector.py     # pycti InternalEnrichmentConnector wiring
    __main__.py
  tests/
    unit/            # test_allowlist.py, test_mapper.py, test_config.py
    integration/     # test_client.py (fake server)
    fixtures/        # sample SpiderFoot JSON
deploy/
  docker-compose.yml
  .env.example
docs/
  README.md          # setup, authorization policy, mapping table, limitations
```

## Style

Typed, small pure functions; mapping and allowlist have no I/O so they test without mocks.

```python
def is_allowed(target: str, allowlist: frozenset[str]) -> bool:
    """True if target equals an allowlisted domain or is a subdomain of one."""
    t = target.lower().rstrip(".")
    return any(t == d or t.endswith("." + d) for d in allowlist)
```

- `ruff` for lint/format, line length 100, type hints on public functions.
- No secrets in code or logs; tokens only via env.

## Test strategy

- **Unit (`pytest`, `tests/unit`)**: allowlist edge cases (`evilexample.com` must not match
  `example.com`, trailing dot, case), config fail-fast, mapper per event type, unmapped
  types counted, relationship direction, deterministic output for identical input.
- **Integration (`tests/integration`)**: client against fake HTTP server (`responses`):
  success, polling until FINISHED, timeout → partial, HTTP errors.
- **E2E manual**: documented checklist in `docs/README.md` against an owned domain.
- Coverage: all of `allowlist.py`, `config.py`, `mapper.py` covered; no numeric gate on
  `connector.py` (thin pycti glue).
- TDD: failing test first for each module, per SEED build phases.

## Boundaries

**Always**
- Check allowlist before any SpiderFoot call; refuse and log otherwise.
- Default to passive modules; record scan id + module as provenance on every object.
- Pin image and package versions; keep `.env` out of git (`.env.example` only).

**Ask first**
- Adding active SpiderFoot modules or any non-allowlist bypass.
- Mapping new event types or custom `x_` STIX properties.
- Changing pinned OpenCTI/pycti/SpiderFoot versions.

**Never**
- Scan a target not on the allowlist, or start with an empty allowlist.
- Commit tokens, `.env`, or SpiderFoot/OpenCTI data volumes.
- Use OpenCTI Enterprise Edition code or features.
- Fork or vendor SpiderFoot/OpenCTI source into this repo.
