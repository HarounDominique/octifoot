# Archive: control-panel

Closed 2026-10-04 · Spec: [SPEC-control-panel.md](../specs/SPEC-control-panel.md) · Reflection: [reflection/control-panel.md](../reflection/control-panel.md) · Builds on: [archive/watch-automation.md](watch-automation.md)

## What was built

A local control panel served by the connector (standard library only, off unless `OCTIFOOT_UI_TOKEN` is set, published on `127.0.0.1:8099`) to add and remove the domains octifoot may analyse and to change the maximum time of an analysis (60-7200 s) without editing `deploy/.env`.
The `.env` list stays and is read-only in the page; the effective allowlist (`.env` plus the panel's) and the effective time are read at each use by the connector, the expansion and the watcher. State and an audit log live in the `octifoot-state` volume.

Safety: token login with throttling, `HttpOnly` `SameSite=Strict` session, CSRF on every change, `Host` and `Origin` checks, ownership confirmation for every added domain, restrictive security headers, an audit line per change, and domain validation (no bare TLDs, public suffixes, IPs, wildcards, URLs or ports), which now also applies to `.env`.

- `allowlist.validate_domain`, `runtime.py`, `panel.py`, config, connector wiring, Compose (loopback-only port, volume), env example, README; 615 tests (44 against a real HTTP server), `ruff` clean
- Verified live end to end with a reserved test domain: refused, added from the panel and analysed with a 60 s limit (the Note says so), removed and refused again; the audit log holds the changes; test data removed

## Deviations accepted

None. A pre-existing weakness (the allowlist accepted any text) was closed as part of it.

## Not done / next

- A total deadline per enrichment and importing each scan as it finishes: a 5-scan expansion can run 75 minutes and imports nothing until the end (seen live on forocoches.com; stopped by the operator and recovered from the recorded scan).
- A "stop analysis" control in the panel. HTTPS and roles are out of scope; do not expose the panel beyond localhost.
