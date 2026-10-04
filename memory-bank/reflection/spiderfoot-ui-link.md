# Reflection: spiderfoot-ui-link

Date: 2026-10-04 · Spec: SPEC-spiderfoot-ui-link.md (approved) · Plan: 2 phases DONE · Live check: replay of a recorded scan through the real helper; the link opened

## Implementation vs spec

| Spec requirement | Result |
|---|---|
| Optional `SPIDERFOOT_UI_URL`: http(s) only, trailing slash removed, empty means off, else ConfigError | Met (tests) |
| Every reference of a scan carries the scan URL; the Note's first line ends with it | Met; live on an observable and the Note |
| Compose default `http://localhost:5001`; `.env.example` documents it | Met |
| Nothing else changes (ids, objects) | Met (test) |

Deviations: none.

## Why it matters

The project's gap against SpiderFoot standalone was never the data (SpiderFoot keeps it all) but the path to it: octifoot deliberately imports a small, safe, attributed part of a scan, and everything else looked lost.
With the link the two halves are one workflow: triage in OpenCTI from the curated Notes and objects, then one click into SpiderFoot's complete record for the same scan. It costs no data and no extra scan.

## Workflow evaluation

- The URL shape was probed on the running SpiderFoot before designing anything; the browser-facing address had to be a separate setting from the internal one, which only becomes obvious by looking at the Compose network.
- A one-line shell mistake (a variable named `path` in zsh) broke the rest of a command; harmless, but a reminder to avoid shell-reserved variable names in probes.
- Verified through the API and by opening the URL; the OpenCTI UI rendering of the link was not looked at.

## Rules extracted

- None new. Reinforced: `patch-from-the-current-text-never-from-memory` (evidence 2).

## Follow-ups (not blocking)

- Deep links to event types or modules; embedding; authentication in front of the SpiderFoot UI if it is ever exposed beyond localhost.
