# SPEC: iterative-scan-loop

Status: approved
Extends: [SPEC-spiderfoot-connector.md](SPEC-spiderfoot-connector.md) (this is its "Future" phase 3, reduced to a safe subset)

## Objective

Let one enrichment request follow its own discoveries: after scanning a domain, scan the
**subdomains it discovered**, up to a small bounded depth, and import everything in one
bundle with provenance. Opt-in; default behaviour (one scan) is unchanged.

Why it is safe by construction: expansion only ever targets domains that pass the same
`SPIDERFOOT_ALLOWED_DOMAINS` check as the original target, so discoveries can never widen
the authorized scope. Anything outside it is counted and reported, never scanned.

Success:
- With `SPIDERFOOT_MAX_DEPTH=0` (default) behaviour is identical to today.
- With depth ≥ 1, discovered `INTERNET_NAME` subdomains that are allowlisted are scanned,
  breadth-first, each at most once, never exceeding `SPIDERFOOT_MAX_SCANS`.
- Out-of-allowlist discoveries (e.g. third-party hosts) are never scanned and are reported.
- A failing sub-scan does not lose results already collected; the root scan failing still fails the work.
- The final message and Note state how many scans ran, depth reached, and what was skipped and why.

Out of scope: expansion from IPs, emails, affiliates or co-hosts; triggering OpenCTI
enrichment jobs per discovery; parallel scans; persisting a scan history across requests;
non-CTI entities.

## Assumptions (approved by the user's standing instruction to proceed)

1. The loop runs inside one `process_message` call (sequential scans, one merged bundle).
2. Config: `SPIDERFOOT_MAX_DEPTH` (int 0-3, default 0 = disabled), `SPIDERFOOT_MAX_SCANS`
   (int 1-20, default 5, counts the root scan).
3. Candidates: `INTERNET_NAME` events only (not `AFFILIATE_INTERNET_NAME`), normalized, excluding the
   scanned target itself.
4. Candidate must satisfy `is_allowed`; otherwise it is counted in `out_of_scope` and skipped.
5. Dedupe: a domain is scanned at most once per request (set of normalized names).
6. Order: breadth-first, discovery order within a level; stop when depth or scan budget is reached;
   the remainder is counted in `budget_skipped`.
7. Each scan is mapped with its own target and scan id, then merged by STIX id (deterministic
   ids keep merges idempotent). Sub-target domains get the usual `related-to` link to the domain
   that discovered them (already produced by the mapper relative to its scan target).
8. Per-scan timeout and passive use case apply to every scan unchanged.
9. A sub-scan error (SpiderFoot error, `ERROR-FAILED`) is logged and recorded in the summary;
   remaining scans continue.

## Commands

```bash
cd connector && . .venv/bin/activate
pytest tests/unit -q
pytest && ruff check . && ruff format --check .
```

## Structure

```
connector/src/spiderfoot_connector/expansion.py   # new: pure planner
connector/src/spiderfoot_connector/config.py      # + max_depth, max_scans
connector/src/spiderfoot_connector/mapper.py      # MapResult.discovered_domains
connector/src/spiderfoot_connector/connector.py   # loop + merge
connector/tests/unit/test_expansion.py            # new
connector/tests/unit/test_config.py, test_connector.py, test_mapper.py  # extended
deploy/docker-compose.yml, deploy/.env.example, docs/README.md          # new variables + docs
```

## Style

Planner is pure and has no I/O:

```python
def plan_next(
    discovered: Iterable[str],
    *,
    scanned: set[str],
    allowlist: frozenset[str],
    remaining_budget: int,
) -> Plan:
    """Split discoveries into targets to scan, out-of-scope and budget-skipped."""
```

## Test strategy

- Unit (TDD, no network): planner (allowlist, dedupe, self-exclusion, budget, ordering,
  case/trailing-dot); config bounds and defaults; mapper reports discovered domains
  (INTERNET_NAME only, not target, not affiliates, not false positives).
- Connector tests with a fake client returning events per target: depth 0 → one scan;
  depth 1 → allowlisted subdomains scanned, third-party not; no repeated scans; max-scans cap;
  depth limit respected across two levels; sub-scan failure tolerated; root failure raises;
  allowlist refusal of the root still happens before any call.
- Live check (manual, optional): needs an owned domain that has allowlisted subdomains.

## Boundaries

**Always**
- Gate every scan, including expansions, with `is_allowed` before calling SpiderFoot.
- Keep expansion bounded by both depth and total scan count.
- Report what was skipped (out of scope, over budget, failed).

**Ask first**
- Expanding from anything other than `INTERNET_NAME` (IPs, emails, affiliates, co-hosts).
- Raising the depth/scan ceilings (3 / 20) or running scans in parallel.
- Using non-passive use cases for expansions.

**Never**
- Scan a domain outside the allowlist because a scan "discovered" it.
- Enable expansion by default.
- Create unbounded or recursive-without-limit scanning.
