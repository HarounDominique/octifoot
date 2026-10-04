---
slug: spiderfoot-ui-link
spec: SPEC-spiderfoot-ui-link.md
status: approved
---

## Implementation Roadmap

Routing: standard.

- [x] Phase 1 — Config, mapper references and Note line, connector wiring, compose and env example, tests (satisfies: SPEC-spiderfoot-ui-link.md#objective, SPEC-spiderfoot-ui-link.md#boundaries)
- [x] Phase 2 — Docs, live check (satisfies: SPEC-spiderfoot-ui-link.md#test-strategy)

## Execution State

**Build Status**: COMPLETE
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {1: 1, 2: 1}
**Last Block Rule**: none
**Can Resume**: NO

## Deviations

- A shell slip while probing: I used a variable named `path`, which zsh ties to `PATH`, and the rest of that command failed with "command not found". Re-run without it; no repository state was affected.
- A scripted patch applied step by step with individual success reports (the lesson of `scan-changes`); one lint import-order fix via `ruff --fix`.

**Probe (real SpiderFoot):** `GET /scaninfo?id=<scan>` returns the scan page (HTTP 200, the id appears 16 times); an unknown id also returns 200 (it is the same single-page shell).

**Live check (2026-10-04, connector rebuilt from this branch, Compose default `SPIDERFOOT_UI_URL=http://localhost:5001`):** replay of the recorded scan `A074967B` through the real helper. Read back from OpenCTI:
the Note's first line is `SpiderFoot scan A074967B for zonetransfer.me. Full results in SpiderFoot: http://localhost:5001/scaninfo?id=A074967B`; the observable `5.196.105.14` carries an external reference `A074967B` with that URL;
opening the URL returns 200. The replay's snapshot Note was deleted and none remain.
Not seen live: the URL in the OpenCTI UI as a clickable reference (checked through the API only).
