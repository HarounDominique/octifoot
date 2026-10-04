# Archive: spiderfoot-ui-link

Closed 2026-10-04 · Spec: [SPEC-spiderfoot-ui-link.md](../specs/SPEC-spiderfoot-ui-link.md) · Reflection: [reflection/spiderfoot-ui-link.md](../reflection/spiderfoot-ui-link.md) · Builds on: [archive/event-catalogue.md](event-catalogue.md)

## What was built

An optional `SPIDERFOOT_UI_URL` (the address the browser uses; Compose default `http://localhost:5001`, empty = no links). When set, every external reference octifoot creates for a scan carries `url = <UI URL>/scaninfo?id=<scan id>` and the first line of each scan Note ends with
`Full results in SpiderFoot: <URL>`. From any object or Note in OpenCTI one click opens the complete scan in SpiderFoot, including everything the import deliberately leaves out.

- config, mapper and connector wiring, Compose and `.env.example`, README; 383 tests, `ruff` clean
- Verified live by replaying a recorded scan: Note first line, observable reference and the opened page (HTTP 200); the replay's snapshot Note was deleted

## Deviations accepted

None.

## Not done / next

- The link was checked through the API, not in the OpenCTI UI rendering.
- Deep links per event type or module; authentication if the SpiderFoot UI is ever exposed beyond localhost.
