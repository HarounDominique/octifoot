# Reflection: watch-automation

Date: 2026-10-04 · Spec: SPEC-watch-automation.md (approved) · Plan: 2 phases DONE · Live check: a real domain watched with a 5-minute interval through two automatic runs

## Implementation vs spec

| Spec requirement | Result |
|---|---|
| Off by default; 5..10080 minutes; cap per cycle | Met (tests); live with 5 minutes |
| Only labelled and allowlisted domains | Met (tests); live for the label (removing it stopped the runs) |
| Due when the last snapshot is older than the interval; no repeat within the interval | Met live: first ask, no repeat for 8 minutes, second ask once due |
| Oldest first, never-scanned first, capped | Met (tests) |
| Failures never stop the loop | Met (tests); not provoked live |
| Runs as an ordinary enrichment work item | Met live: the connector started its scan 50 ms after the request |

Deviations: none.

## What it changes

Until now the comparison feature needed a person to re-run each domain. With a label and one setting, a domain is re-analysed on its own and each run writes the changes Note; the first real pair ended in `no changes`, which is itself a result worth having
(a stable surface). The safety model is unchanged: the label is an explicit opt-in per domain, the allowlist still gates every request, the default is off, and the loop only ever asks for the same enrichment an analyst's click would.

## Workflow evaluation

- Reusing the platform's own enrichment request (instead of calling the enrichment function from a thread) kept every automated run visible as a normal work item and avoided sharing the helper's work state between a thread and the message listener.
- Choosing a 5-minute interval for the live test made the due logic observable in under 12 minutes; the cost was that the test is not evidence for 24-hour operation, only for the logic.
- Cleanup was verified in both systems (label gone, interval restored, loop not started).

## Rules extracted

- New `automation-reuses-the-manual-path-and-keeps-the-same-gates` (safety-boundaries).
- Reinforced: `after-cleaning-test-data-query-to-prove-it-is-gone` (evidence 3).

## Follow-ups (not blocking)

- Alerting on change (out of scope here, "ask first").
- A dedicated least-privilege OpenCTI user for the connector, with the capability to request enrichments, instead of the admin token this development stack uses.
