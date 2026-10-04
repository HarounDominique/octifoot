# Archive: total-deadline

Closed 2026-10-04 · Spec: [SPEC-total-deadline.md](../specs/SPEC-total-deadline.md) · Reflection: [reflection/total-deadline.md](../reflection/total-deadline.md) · Builds on: [archive/control-panel.md](control-panel.md)

## What was built

One analysis is now bounded as a whole: `SPIDERFOOT_MAX_TOTAL_SECONDS` (default 3600), changeable in the control panel (60-14400 s, applies to the next analysis, audited). Each scan gets `min(per-scan limit, time left)`; no scan starts with under 60 s left; skipped targets are named in the expansion Note and counted as `deadline_skipped` in the work message; the snapshot is marked incomplete.
While more scans are queued, each finished scan's new objects are sent to OpenCTI immediately, so a stopped or crashed run keeps what was imported; the final bundle still carries everything.

- `config.py`, `runtime.py`, `panel.py`, `connector.py` (injected clock), Compose, `.env.example`, `docs/README.md`; 659 tests, `ruff` clean
- Live: total 150 s on zonetransfer.me, sub-scan skipped and named, finished within the limit

## Deviations accepted

None in the spec; one wrong test expectation corrected.

## Not done / next

- A "stop analysis" control in the panel (out of scope here).
- A real free API key trial needs the owner to register one.
