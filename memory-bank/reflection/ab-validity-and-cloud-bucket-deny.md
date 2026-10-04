# Reflection: ab-validity-and-cloud-bucket-deny

Date: 2026-10-04 · Spec: SPEC-ab-validity-and-cloud-bucket-deny.md (approved) · Plan: 2 phases DONE · Live check: valid A/B on two domains

## Implementation vs spec

| Spec requirement | Result |
|---|---|
| Harness reports `valid: false` with reasons for timed-out or non-FINISHED runs; `accepted` then false | Met; `invalid_reasons` pure and unit-tested; live runs were all valid so the invalid path was not seen live |
| Four cloud-bucket modules denied, absent from `lean_modules.json` | Met; list went 108 to 104, diff is four lines |
| Test: no denied cloud module produces an imported type; lean keeps every imported type passive produces | Met (`IMPORTED_EVENTS` + two tests) |
| Valid A/B re-run on both domains | Met: 64.8 % and 87.2 %, ids identical, all runs FINISHED |

Deviations: none. The result also changes the status of an earlier deviation: the acceptance rule that `lean` had failed
is now met with valid evidence.

## What the investigation found

- The slow tail of the lean scan was one module, found by reading SpiderFoot's own scan log (`/scanlog`), not by guessing:
  `sfp_s3bucket` ran 164 s after every other module had finished. Its three siblings do the same on Azure, DigitalOcean and Google.
- "Passive" is SpiderFoot's label, not a guarantee of behaviour: these modules send HTTP requests with invented bucket names to
  third-party storage hosts. Their events are not imported, so denying them costs nothing we keep; `CLOUD_STORAGE_BUCKET_OPEN`
  (an open bucket) would be a real finding, so a future mapper for it should revisit the deny-list.
- The earlier "58 %" for bugoverflow was a floor measured against an aborted run; the valid figure is higher (87.2 %).
  The first domain's 11 % was mostly the bucket modules, not the co-host chain.

## Workflow evaluation

- A worktree for the long A/B run, with `PYTHONPATH` pointing at it, kept the measurement independent of the branch I was editing in
  the main tree. The first `git worktree add` failed (branch already checked out) and I had already queued the script; I caught it
  because the script's first step would have been `cd` into a missing directory, and recreated the worktree with `--detach`.
- Rebuilding the connector with `--no-deps` kept SpiderFoot from restarting during the A/B; without it a dependent restart
  could have killed the running scan.
- Measuring cost: the two valid runs took about 35 minutes of wall time, dominated by a `full` scan throttled on WHOIS.

## Rules extracted

- New `use-a-worktree-and-no-deps-for-long-measurements` (deployment).
- Existing `measurement-harness-rejects-truncated-runs` reinforced: it is now implemented and its evidence_count is 2.

## Follow-ups (not blocking)

- If an open-bucket mapper is ever written, decide whether to re-enable one bucket module for it.
