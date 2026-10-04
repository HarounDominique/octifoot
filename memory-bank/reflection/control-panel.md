# Reflection: control-panel

Date: 2026-10-04 · Spec: SPEC-control-panel.md (approved) · Plan: 4 phases DONE · Live check: the real panel against the real stack, end to end with a reserved test domain

## Implementation vs spec

| Requirement | Result |
|---|---|
| Add and remove authorised domains from a page; the `.env` list read-only and not removable | Met (tests; live with `example.org`: refused, allowed after adding, refused after removing) |
| Maximum time changeable from the page (60-7200 s), applied to the next analysis and reported in the Note | Met live (`stopped after 60 s`) |
| Names validated, also for `.env` | Met (tests); this closed a pre-existing weakness (`com` would have authorised every .com) |
| Local, token, session, CSRF, Host and Origin checks, throttling, headers, ownership confirmation, audit | Met (44 HTTP tests against a real server; the main ones repeated live) |
| Off unless configured; standard library only | Met (no dependency added) |

Deviations: none from the spec.

## What it changes

Until now changing what may be scanned, or how long an analysis may run, meant editing a file and recreating a container. It is now a page, but the page is the authorisation boundary, so it was designed from how it could be abused:
local only, token, confirmation of ownership, validation that refuses names which would authorise strangers, and an audit trail. The most important single finding of the work was not in the panel: the existing allowlist accepted a bare `com`.

## The operational finding

The user asked for the panel because a scan of a large site hit the fixed limit. Finishing the work, the live system showed a second, bigger limit: expansion multiplies the maximum time (five scans of up to 15 minutes) and the import happens only at the end, so one enrichment
can run 75 minutes with nothing visible and be lost if stopped. The panel lets the owner raise or lower the per-scan time, which is the wrong lever for this; the right levers are a total deadline for one enrichment and importing as scans finish.

## Workflow evaluation

- Writing the HTTP tests against a real server first (rather than unit-testing the handler) caught the stale `problem` flag, which a mock would not have shown.
- Testing the abuse cases (foreign Host, no CSRF, `com`, no confirmation) live as well as in tests confirmed that the running container behaves like the test server.
- When the user asked to stop, the safe path was to name what would be lost (nothing is imported until the end) before acting, and then to recover the recorded data rather than rescan.

## Rules extracted

- New `a-control-that-sets-scope-needs-validation-authentication-and-an-audit-trail` (safety-boundaries).
- New `a-long-multi-step-job-needs-a-total-deadline-and-incremental-output` (deployment).
- New `read-a-status-flag-after-refreshing-what-it-describes` (code-editing).

## Follow-ups (not blocking)

- A total deadline per enrichment (for example `SPIDERFOOT_MAX_TOTAL_SECONDS`) and importing each scan as it finishes, so that a stopped or failing expansion does not lose the scans already done.
- A way to stop a running analysis from the panel.
- HTTPS and roles are out of scope by design; do not expose the panel beyond localhost.
