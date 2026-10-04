---
slug: control-panel
spec: SPEC-control-panel.md
status: approved
---

## Implementation Roadmap

Routing: standard (security-sensitive, so the HTTP layer is tested against a real server).

- [x] Phase 1 — Domain validation (also for `.env`), runtime state store with audit log, effective allowlist and timeout (satisfies: SPEC-control-panel.md#objective, SPEC-control-panel.md#boundaries)
- [x] Phase 2 — Connector and watcher use the runtime values (satisfies: SPEC-control-panel.md#objective)
- [x] Phase 3 — The web panel (standard library server, token, session, CSRF, Host check, throttling, headers, language) (satisfies: SPEC-control-panel.md#objective, SPEC-control-panel.md#boundaries)
- [x] Phase 4 — Compose (port on localhost, volume), env example, documentation, live check (satisfies: SPEC-control-panel.md#test-strategy)

## Execution State

**Build Status**: COMPLETE
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {1: 1, 2: 1, 3: 1, 4: 1}
**Last Block Rule**: none
**Can Resume**: NO

## Deviations

- A weakness that existed before the panel, found while designing it: the allowlist accepted any text, so an entry such as `com` would have authorised every `.com` domain. Names are now validated in the panel, in the store and in `.env` (the connector refuses to start with an unsafe entry).
- Defects found by the tests and fixed before commit: the page read the store's `problem` flag **before** refreshing it, so a corrupt state file was not reported; routes were a mutable class attribute (lint); the panel tests took 24 s because the server's shutdown polled every 0.5 s (now 4 s in total); my Compose test used a regular expression that did not match a port written with variables.
- Two of my own shell slips: a variable named `path` earlier, and a relative path in a rules patch run from the wrong directory (the closing step of api-keys); this time every patch used absolute paths.
- While finishing, the live system exposed a product problem that is not the panel's: a large site (forocoches.com) with `SPIDERFOOT_MAX_DEPTH=1` and `SPIDERFOOT_MAX_SCANS=5` is analysed as five consecutive scans of up to 900 s each (a worst case of 75 minutes), and **nothing is imported until the last one ends**. After about 40 minutes the operator asked to stop.
  I stopped the run (recreated the connector, aborted the running SpiderFoot scan, closed the stuck work as stopped by the operator) and imported the recorded root scan without rescanning, flagged incomplete (126 objects). The panel's maximum time helps but does not remove that worst case; see the follow-up.

**Live check (2026-10-04, connector rebuilt from this branch, panel on `http://localhost:8099`, test domain `example.org`, a reserved documentation name):**
- login page 200 with the security headers and no token in it; a foreign `Host` header 403; no session redirects to `/login`; a wrong token 401; the right token 303 with an `HttpOnly; SameSite=Strict; Path=/` cookie;
- changes refused without the CSRF token (403), for `com` (400) and without the ownership confirmation (400), none of them written to the audit log;
- end to end: analysing `example.org` before adding it: the work ended with `example.org is not in SPIDERFOOT_ALLOWED_DOMAINS`; after adding it from the panel (and setting the maximum time to 60 s) the same request ran with no change to `.env` and no restart (25 objects) and its Note said `scan incomplete: stopped after 60 s`;
  after removing it from the panel the next request was refused again; the audit log holds the four changes with time, action, value and client address (`172.18.0.1`, the Docker gateway, not `127.0.0.1`, because the request crosses the published port);
- cleanup verified: the test Notes and observables deleted (none left), no scan running in SpiderFoot, the maximum time back at the default.
Not seen live: the Spanish page in a browser, the login throttling and session expiry against the real server (covered by the HTTP tests), a real browser rendering (checked through HTTP only).
