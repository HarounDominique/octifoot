---
slug: watch-automation
spec: SPEC-watch-automation.md
status: approved
---

## Implementation Roadmap

Routing: standard.

- [x] Phase 1 — `watch.py` (scheduler, OpenCTI helpers), config, connector wiring, compose and env, tests (satisfies: SPEC-watch-automation.md#objective, SPEC-watch-automation.md#boundaries)
- [x] Phase 2 — Docs and live check with a short interval on a real test domain (satisfies: SPEC-watch-automation.md#test-strategy)

## Execution State

**Build Status**: COMPLETE
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {1: 1, 2: 1}
**Last Block Rule**: none
**Can Resume**: NO

## Deviations

- Two fixes to my own scripts, not to the product: my first scripted patch of `config.py` stopped on its first substitution because ruff had wrapped the field line (the same lesson as before: read the current text); and the label attachment used the wrong GraphQL variable type (`ID!` instead of `StixRef!`), found from the platform's error message.
- Lint: seven findings in the new code and tests (unused unpacked names, a redundant `Z` replacement); `datetime.fromisoformat` accepts `Z` on this Python, verified before removing the replace.
- The in-memory record of requests is lost on restart (documented in the spec).

**Real watchlist query:** `objectLabel` filter on `Domain-Name` returns exactly the labelled observables.

**Live check (2026-10-04, connector rebuilt from this branch with `SPIDERFOOT_WATCH_INTERVAL_MINUTES=5`, label `octifoot:watch` on registrolineas.com):**
- the loop started (`every_minutes: 5, cycle_s: 75`); at 20:02:07 it asked OpenCTI for the enrichment and the connector started the scan 50 ms later, with nobody clicking;
- the first scan wrote its snapshot Note at 20:05:39 (`first snapshot`); the loop, running every 75 s, did **not** ask again within the interval;
- at 20:10:52, once the snapshot was older than the interval, it asked again: exactly two requests in the whole run;
- the second automatic scan wrote `no changes since 2026-10-04` against the first: the first real comparison between two scans started by the connector itself (the domain did not change in nine minutes);
- after the label was removed no further request was made (checked over a further cycle).
Cleanup verified: label deleted (none left), connector recreated without the interval (loop not started, `SPIDERFOOT_WATCH_INTERVAL_MINUTES=0`). The two real snapshot Notes of registrolineas.com were kept as its real baseline.
Not seen live: the allowlist skip and the cap on a real cycle (unit-tested), a watched domain whose scan fails, a restart in the middle of a scan.
