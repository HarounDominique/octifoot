# Reflection: fast-scan-profile

Date: 2026-10-04 · Spec: SPEC-fast-scan-profile.md (approved, amended) · Plan: 4 phases DONE · Live check: A/B on two real domains, connector rebuilt and registered

## Implementation vs spec

| Spec requirement | Result |
|---|---|
| `full` behaves as before | Met; selectable with `SPIDERFOOT_PROFILE=full`, unit-tested |
| `lean` = explicit passive keyless non-invasive `modulelist` minus `sfp_robtex`, `sfp_countryname` | Met; derived from the v4.0 metadata snapshot, tested against it |
| Lean list never contains an active module | Met (test against SpiderFoot metadata) |
| A/B: identical imported ids and >= 30 % faster on at least two domains | **Not met.** registrolineas.com 11 %, bugoverflow.com 58 % (lower bound). Ids identical on both |
| Lean default only after the A/B passes | **Overridden by the user** on 2026-10-04 |

Deviations:
- `lean` is the default although the acceptance rule failed (accepted by the user, recorded in the task file and in the spec). Default is `lean` only with `SPIDERFOOT_USECASE=passive`; otherwise `full`, because lean with another use case is a `ConfigError`.
- Known loss, accepted in the spec: `MALICIOUS_COHOST` lines in the Note (listed 10 to 2 and 6 to 0).

## Evidence quality of the A/B

- bugoverflow full `635DE72C` ended ABORTED at the 900 s harness timeout. The 58 % is a floor, but "identical objects" there compares lean to a partial full run. `ab_scan.py` never checks `timed_out`, so it reported `accepted: true` for that domain.
- registrolineas: 71 events in 352 s means something still in the lean list dominates the time; the hypothesis (tail chain from robtex) only explained the CDN-less, subdomain-heavy case. Not investigated.
- Order was `ab` on one domain and `ba` on the other, so order effects are not separable from domain effects.
- Effective profile in the rebuilt container verified as `lean`; no live connector scan was run with it.

## Workflow evaluation

- Routing "designed-lite" fit: three small phases of code, one of measurement. The measurement phase carried all the risk.
- The spec put a hard gate on the default. The gate was reasonable, but the harness that enforced it had a hole (truncated runs), and the owner overrode it on partial evidence. Closing the harness gap would have made the decision cleaner either way.
- The previous session's E2E start (Docker up, long foreground wait) ended without a result and the user reported the session exiting unrequested; the cause was not verified from here. State was recoverable because every phase was committed and the stack stayed up.
- A scripted multi-file edit chained after BSD `sed -i` silently skipped the rest. Caught by `git status` before reporting; no wrong state was committed.
- No spec correction was needed mid-build.

## Rules extracted

- New `measurement-harness-rejects-truncated-runs` (deployment).
- New `macos-sed-and-chains-skip-silently` (code-editing); `patch-with-exact-edits-and-verify` bumped to evidence_count 3.

## Follow-ups (not blocking)

- Make `ab_scan.py` report `valid: false` when either run timed out or aborted; rerun bugoverflow with a longer `--timeout`.
- Find the slow module in registrolineas lean scan `E664397D`.
