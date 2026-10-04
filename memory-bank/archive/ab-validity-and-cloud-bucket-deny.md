# Archive: ab-validity-and-cloud-bucket-deny

Closed 2026-10-04 · Spec: [SPEC-ab-validity-and-cloud-bucket-deny.md](../specs/SPEC-ab-validity-and-cloud-bucket-deny.md) · Reflection: [reflection/ab-validity-and-cloud-bucket-deny.md](../reflection/ab-validity-and-cloud-bucket-deny.md) · Builds on: [archive/fast-scan-profile.md](fast-scan-profile.md)

## What was built

- `ab_scan.py` now reports `valid` and `invalid_reasons`; a run that timed out or did not end FINISHED can never be `accepted`
  (`abcompare.invalid_reasons`, pure, unit-tested).
- The slow tail of `lean` was found in SpiderFoot's scan log: `sfp_s3bucket` alone ran 164 s after all other modules finished.
  It and `sfp_azureblobstorage`, `sfp_digitaloceanspace`, `sfp_googleobjectstorage` are now in `DENY`; the lean list has 104 modules.
- `mapper.IMPORTED_EVENTS` plus tests: no denied cloud module produces an imported event type, and `lean` keeps every
  imported event type the passive set produces.
- Valid A/B (all runs FINISHED): registrolineas.com 503.0 s to 177.1 s (64.8 %), bugoverflow.com 1229.8 s to 156.9 s (87.2 %),
  imported objects identical on both. The acceptance rule of fast-scan-profile is now met.
- 151 tests, `ruff` clean.

## Deviations accepted

None.

## Not done / next

- `CLOUD_STORAGE_BUCKET_OPEN` (open bucket) is a real finding that is not mapped; if it ever is, revisit the cloud modules.
- `full` timings are noisy (WHOIS throttling); only one run per cell, so order and domain effects are not separable.
- The invalid-run path of the harness is unit-tested but was not seen on a live aborted run.
