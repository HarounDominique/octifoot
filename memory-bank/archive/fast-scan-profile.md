# Archive: fast-scan-profile

Closed 2026-10-04 · Spec: [SPEC-fast-scan-profile.md](../specs/SPEC-fast-scan-profile.md) · Reflection: [reflection/fast-scan-profile.md](../reflection/fast-scan-profile.md) · Builds on: [archive/spiderfoot-connector.md](spiderfoot-connector.md)

## What was built

`SPIDERFOOT_PROFILE` selects which SpiderFoot modules a scan runs. `lean` sends an explicit `modulelist`:
SpiderFoot v4.0 passive modules without API key, `invasive` or `tool` flags, minus `sfp_robtex` and
`sfp_countryname`, derived by a pure function from a committed metadata snapshot. `full` keeps the
previous behaviour. `lean` is the default with `SPIDERFOOT_USECASE=passive`; any other use case keeps `full`.
An A/B harness (`connector/tools/ab_scan.py`) runs the same target with both profiles and compares what
each would import.

- `profiles.py`, `abcompare.py`, config/client/connector plumbing, compose and `.env.example`; 145 tests, `ruff` clean
- Live A/B on two domains: imported objects identical on both; lean faster by 11 % (registrolineas.com) and 58 % (bugoverflow.com)
- Connector rebuilt; effective profile in the container verified as `lean`

## Deviations accepted

- Acceptance rule (identical ids and >= 30 % faster on two domains) **not met**; `lean` made the default
  anyway by the user's decision on 2026-10-04. Recorded in the task file and the spec.
- bugoverflow `full` scan was ABORTED by the 900 s harness timeout, so its 58 % is a lower bound and its
  equality check was against a partial run. The harness did not flag it.
- Known loss: `MALICIOUS_COHOST` lines in the scan Note (10 to 2, 6 to 0).

## Not done / next

- Make `ab_scan.py` mark runs that timed out or aborted as invalid; rerun bugoverflow with a longer timeout.
- Find the module that keeps registrolineas lean at 352 s with 71 events.
- No live connector scan was run with the new default; only the A/B went through SpiderFoot directly.
