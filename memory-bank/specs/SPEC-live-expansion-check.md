# SPEC: live-expansion-check

Status: approved
Extends: [SPEC-iterative-scan-loop.md](SPEC-iterative-scan-loop.md) (verification of a path that was only unit-tested)

## Objective

Run the iterative expansion against the real stack (OpenCTI, worker, connector, SpiderFoot) and
record what actually happens, because three archives list "expansion not exercised live" as open.
This is a verification task: code changes only if the live run exposes a defect.

Success:
- One real enrichment with `SPIDERFOOT_MAX_DEPTH=1` completes in OpenCTI with no work errors.
- The expansion Note exists and states scans run, depth reached, failed sub-scans, skipped
  (outside the allowlist) and skipped (over budget).
- If SpiderFoot discovers allowlisted subdomains, they are scanned once each, within `SPIDERFOOT_MAX_SCANS`, and merged.
- If it discovers none, say so plainly; do not widen the allowlist to force a result.

Out of scope: adding domains to the allowlist that the owner has not authorized; parallel scans.

## Assumptions (approved by the user's standing instruction to proceed)

1. Targets are the two domains already in the test allowlist (`registrolineas.com`, `bugoverflow.com`).
2. The work is selected by the id returned from the enrichment request, never "the latest" (rule `e2e-scripts-select-by-id`).
3. A real subdomain that is not allowlisted still exercises the refusal path of the loop; that is reported separately from the success path.

## Commands

```bash
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d
# create the observable, askEnrichment(connectorId), poll work(id) until complete (OpenCTI GraphQL)
```

## Test strategy

Live only. Evidence: work id and status, expansion Note text, SpiderFoot scan ids and the discovered list
recomputed from the exported events.

## Boundaries

**Always**: select the work by id; report what was not exercised.
**Never**: add a third-party domain to the allowlist to obtain a result; call the success path verified when only the refusal path ran.
