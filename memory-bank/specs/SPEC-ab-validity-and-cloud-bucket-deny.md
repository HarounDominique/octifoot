# SPEC: ab-validity-and-cloud-bucket-deny

Status: approved
Extends: [SPEC-fast-scan-profile.md](SPEC-fast-scan-profile.md) (A/B harness, deny-list)

## Objective

Close the two follow-ups left by fast-scan-profile: (1) an A/B run that was cut off or aborted must
never count as evidence, (2) find what still keeps a `lean` scan slow and remove it only if the
evidence says it adds nothing we import, then re-measure with valid runs.

Evidence (SpiderFoot scan log of lean scan `E664397D`, registrolineas.com, 352 s, 71 events):
every module but one had finished by +188 s; `sfp_s3bucket` kept running until +351 s (1975 log
rows of "Spawning thread to check bucket: https://<guess>.s3...amazonaws.com"). Its siblings
`sfp_azureblobstorage`, `sfp_digitaloceanspace`, `sfp_googleobjectstorage` do the same on other
providers. All four are tagged `Passive` by SpiderFoot, yet they send HTTP requests with guessed
names to third-party storage hosts, and the events they produce (`CLOUD_STORAGE_BUCKET*`) are not
imported by the mapper. Separately, bugoverflow `full` scan `635DE72C` ended ABORTED at the 900 s
harness timeout, and `ab_scan.py` still printed `accepted: true` for that domain.

Success:
- `ab_scan.py` reports `valid: false` plus the reasons when either run timed out or did not end
  FINISHED, and `accepted` is then always false.
- The four cloud-bucket modules are in the deny-list, so they are absent from `lean_modules.json`.
- A test guarantees no deny-listed cloud module produces an event type the connector imports, and
  that `lean` still produces every imported event type that the passive set produces.
- A/B re-run on both domains with valid (FINISHED) runs, results recorded in the task file.

Out of scope: mapping `CLOUD_STORAGE_BUCKET_OPEN` (an open bucket is a real finding; that is a
separate feature, and these modules stay denied until it exists), changing `full`.

## Assumptions (approved by the user's standing instruction to proceed)

1. "Imported" means: becomes an object, a label or a Note line (`mapper.IMPORTED_EVENTS`).
2. A deny-list addition needs both the time evidence above and the test that nothing imported is lost.
3. `--timeout` for the re-run is 1800 s so `full` can finish; a run that still hits it is invalid, not retried silently.
4. The user approved extending the deny-list with evidence ("ask first" in the previous spec).

## Commands

```bash
cd connector && . .venv/bin/activate
pytest && ruff check . && ruff format --check .
SPIDERFOOT_ALLOWED_DOMAINS=example.com python tools/ab_scan.py --target example.com --timeout 1800
```

## Test strategy

- Unit, pure: `invalid_reasons` (finished, timed out, aborted, both); profile tests for the
  deny-list, the committed list matching `derive_lean(snapshot, DENY)`, and the event-coverage guard.
- Live: A/B on registrolineas.com and bugoverflow.com with `--timeout 1800`.

## Boundaries

**Always**: treat a non-FINISHED or timed-out run as invalid; record scan ids and times.
**Ask first**: denying any module whose events the mapper imports.
**Never**: mark a result accepted from an invalid run; deny a module without the coverage test passing.
