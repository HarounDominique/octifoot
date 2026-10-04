# Reflection: source-health-note

Date: 2026-10-04 · Spec: SPEC-source-health-note.md (approved, one amendment) · Plan: 2 phases DONE · Live check: fresh scan, Note read back from OpenCTI

## Implementation vs spec

| Spec requirement | Result |
|---|---|
| Note line naming modules that logged errors, counted, capped at 8, messages cut at 80, entities decoded | Met; unit, client and connector tests; live |
| The line states its own limit | Met (text inside the line, plus README section) |
| No errors, no line; objects never change | Met (tests) |
| A failing log read never fails the enrichment | Met (unit test); not seen live |
| With expansion each scan reads its own log | Met in the connector (`fetch_errors(outcome.scan_id)`), unit-tested; multi-scan not seen live |

Deviations: ordering changed from alphabetical to most-errors-first after rendering the line on a real log (spec updated). Accepted.

## What it can and cannot do

- Detects the 13 failing components of a real scan (HTTP 401/403/404, API errors, connection failures, parse errors).
- Cannot detect crt.sh outages: `sfp_crt` does not look at the HTTP code and logs the same `STATUS` row for a 502 and for a domain without certificates.
  That was the case that motivated the task, so the real fix for it is not here; the line says so, and the next step would be a direct probe of
  the key sources, which the spec explicitly left as "ask first".
- Constant configuration noise (`sfp_customfeed`, `sfp_flickr`, `sfp_accounts`) is reported; it is cheap to see and filtering it would hide regressions.

## Workflow evaluation

- Rendering the real line before wiring anything caught the ordering problem for free; an alphabetical cap would have hidden the two failing
  subdomain sources behind "and 5 more".
- The first drafts of two tests encoded my assumptions, not SpiderFoot's behaviour (log order, wording); the failing run corrected them. SpiderFoot returns the log newest first.
- A scripted insertion broke syntax once; `ruff` caught it in seconds.

## Rules extracted

- New `a-log-derived-diagnostic-must-say-what-the-log-cannot-show` (external-integrations).
- Reinforced: `inspect-real-output-before-specifying-a-mapping` (evidence 4), `empty-live-result-check-source-health` (evidence 2), `patch-with-exact-edits-and-verify` (evidence 4).

## Follow-ups (not blocking)

- Probe the key subdomain sources directly (crt.sh at least) and report their status in the Note; needs a decision on outbound requests from the connector.
- Verify the failing-log-read path live.
