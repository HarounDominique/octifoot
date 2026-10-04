# Archive: partial-scan-visibility

Closed 2026-10-04 · Spec: [SPEC-partial-scan-visibility.md](../specs/SPEC-partial-scan-visibility.md) · Reflection: [reflection/partial-scan-visibility.md](../reflection/partial-scan-visibility.md) · Builds on: [archive/key-findings.md](key-findings.md)

## What was built

When the connector had to stop a scan (timeout) or SpiderFoot ended it with a status other than FINISHED, the first key finding of that scan's Note says so (`scan incomplete: stopped after N s, results are partial (SPIDERFOOT_TIMEOUT_SECONDS)` or `scan ended <STATUS>, not FINISHED: results may be partial`).
A partial scan never reads as "nothing notable". Each scan of an expansion carries its own flag.

- 319 tests, `ruff` clean; README documents the finding and the cause on certificate-rich domains
- Verified live with a forced 25 s timeout (scan `30B41FA2`, ABORTED, Note read back); the connector was restored to 900 s and confirmed

## Deviations accepted

None. Earlier live checks that read Notes of the aborted scan `06410167` described partial data; their conclusions were re-checked and stand, but this is recorded.

## Not done / next

- Certificate-rich domains exceed 900 s (53 certificates took 15 minutes); the owner can raise `SPIDERFOOT_TIMEOUT_SECONDS`. No cap on certificate fetching exists in SpiderFoot v4.0.
- The `<STATUS>, not FINISHED` wording was not seen live.
