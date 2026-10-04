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
- [ ] Phase 4 — Compose (port on localhost, volume), env example, documentation, live check (satisfies: SPEC-control-panel.md#test-strategy)

## Execution State

**Build Status**: NOT_STARTED
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {1: 0, 2: 0, 3: 0, 4: 0}
**Last Block Rule**: none
**Can Resume**: YES

## Deviations

[none yet]
