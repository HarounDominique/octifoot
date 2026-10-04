# SPEC: run-control

Status: draft (planning; build starts when the owner says so)
Extends: [SPEC-control-panel.md](SPEC-control-panel.md) (the panel, its token, CSRF and audit), [SPEC-total-deadline.md](SPEC-total-deadline.md) (partial results are kept when a run ends early)

## Objective

First step of a single entry point over SpiderFoot and OpenCTI (agreed with the owner on 2026-10-05: integrate at the seams, do not fuse the two products). From the control panel the operator can **start** an analysis of an authorised domain and **stop** the one that is running, and sees what is running now and what ran recently.
Today an analysis starts only from OpenCTI (create the observable, "enrich") and cannot be stopped at all: on 2026-10-04 a 40-minute run could only be abandoned by hand, and its results were lost (the total deadline and early imports reduced that risk; stopping is the missing control).

Success:
- **Run registry.** A thread-safe object shared by the connector and the panel holds the current run (domain, start time, state, scan target now, scans done, scans queued, stop requested) and the last 20 finished runs (domain, start, duration, result: finished, stopped, failed, deadline). The audit log records every start, stop and end.
- **Stop.** The operator stops the *current* run from the panel. The running scan is stopped in SpiderFoot, the partial events are imported like a timeout (the Note says `scan incomplete: stopped by the operator after N s`), queued sub-scans are not started and are named in the expansion Note (`Skipped, stopped by the operator: ...`), the snapshot is incomplete, the work message says `stopped by operator`. A stop is detected at the next poll (at most `SPIDERFOOT_POLL_SECONDS`) and between scans. The stop request names the run it was meant for, so a late click never stops a later run; a new run always starts with no stop pending. Stopping with nothing running says so.
- **Start.** The operator enters a domain in the panel. Only a domain in the *effective allowlist* is accepted (same validation as everywhere); the panel finds or creates the Domain-Name observable in OpenCTI and asks OpenCTI to enrich it with this connector, so the normal path (queue, work, import) is used and nothing bypasses the connector's own gate. Starting the same domain while it is running or already requested in the last 10 minutes is refused with a message. Audited with the work id.
- **Status.** The dashboard shows the current run, refreshes itself every 5 s while a run is active (no script needed), shows the recent runs and, for each, links to OpenCTI's observable and to the SpiderFoot scan (the link already exists in the Note).
- Same access rules as the rest of the panel: token, session, CSRF, `Host` check, audit; every new text in English and Spanish.

Out of scope: cancelling requests still queued in OpenCTI (the panel shows "requested", not "queued position"); running several analyses at once (OpenCTI delivers one message at a time to a connector); scheduling from the panel (the watcher exists); editing SpiderFoot options or API keys from the panel (a later step); a persistent run history across restarts beyond the audit log.

## Assumptions (to confirm when the build starts)

1. Stopping imports what was collected, as a timeout does, rather than discarding it (the owner lost data on 2026-10-04 and asked for results as they finish).
2. Domains are started only from the effective allowlist; there is no "add and start" shortcut, so authorisation stays a separate, confirmed act.
3. The registry lives in memory; a restart forgets history, and the audit log keeps the actions.
4. The panel creates observables through the connector's own OpenCTI client (`helper.api`), which already has the token the connector uses.
5. A stop cannot interrupt a single SpiderFoot HTTP call; the latency is the poll interval.

## Design notes

- `runs.py`: `RunRegistry` (begin, update, finish, request_stop(run_id), stop_requested(run_id), snapshot()) with an injected clock; no I/O.
- `SpiderFootClient.run_scan(..., should_stop=None)`: checked after every poll; on stop it calls `stop_scan` and returns `ScanOutcome(..., timed_out=False, stopped=True)` with the partial events.
- Connector loop: registers the run, calls `registry.update` per scan, passes `should_stop` for the current run id, breaks out on stop, reports skipped targets, finishes the run in a `finally` (also on exception: result `failed`).
- Panel: routes `/run` (POST domain) and `/stop` (POST run id); a `runs` dependency (registry) and a `launcher` callable (domain -> work id) injected like the other dependencies, so the panel is testable with fakes and keeps no OpenCTI code.
- `launcher` (connector side): validates through `validate_domain`, checks `_allowlist()`, creates or reads the observable, calls `ask_enrichment` (already used by the watcher).

## Commands

```bash
cd connector && . .venv/bin/activate
pytest && ruff check . && ruff format --check .
```

## Test strategy

Unit: registry (begin/finish, history cap, stop tied to run id, stale stop ignored, clock injected, thread safety), client stop (stop between polls returns partial events and calls stop_scan; no stop = unchanged), connector (stop mid-root, stop between scans, skipped named, snapshot incomplete, work message, early bundles kept, registry state after success/failure/stop).
HTTP, against a real server like the existing panel tests: login/CSRF required for both routes, domain outside the allowlist refused, duplicate within 10 minutes refused, launcher failure shown without a traceback, stop with nothing running, stale run id ignored, refresh header only while running, escaping, Spanish strings, audit lines, no token in output.
Live: start a real analysis from the panel, see it running, stop it, see the partial import and the Note, then start another and confirm the stop did not carry over.

## Boundaries

**Always**: start only domains in the effective allowlist; keep the confirmation of authorisation in the add-domain step; audit every start and stop; keep partial results when stopping.
**Ask first**: starting domains not yet in the allowlist; running several analyses at once; cancelling queued OpenCTI requests; exposing the panel beyond localhost.
**Never**: bypass the connector's own allowlist gate; let a stale stop affect a later run; start an active use case from the panel.
