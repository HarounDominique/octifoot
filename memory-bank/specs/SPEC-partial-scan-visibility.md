# SPEC: partial-scan-visibility

Status: approved
Extends: [SPEC-key-findings.md](SPEC-key-findings.md), [SPEC-spiderfoot-connector.md](SPEC-spiderfoot-connector.md) (timeout behaviour)

## Objective

A scan that was stopped before it finished must say so in the OpenCTI Note, as the first key finding. Today the connector imports partial results and mentions it only in the work's internal result message, which an analyst looking at the observable never sees.

Evidence (2026-10-04): the root scan `06410167` of zonetransfer.me ran 923 s and ended `ABORTED`, stopped by the 900 s `SPIDERFOOT_TIMEOUT_SECONDS`. The Note it produced listed WHOIS, DNS, certificates and findings with no hint that the data was incomplete.
Cause (scan log, 51,310 rows): `sfp_crt` fetched certificates one at a time for 15 minutes (crt.sh had recovered and returned 53 certificates), and every certificate's names flooded all modules with co-hosted-site events.
The earlier live checks that used this run's Notes therefore described partial data without saying so.

Success:
- When the connector had to stop the scan (timeout), the first key finding reads `scan incomplete: stopped after N s, results are partial (SPIDERFOOT_TIMEOUT_SECONDS)`.
- When a scan ended with any other status than FINISHED without a timeout, the first key finding reads `scan ended <STATUS>, not FINISHED: results may be partial`.
- A FINISHED scan adds nothing. With a partial scan the block is never the "nothing notable" form.
- Every scan of an expansion carries its own flag in its own Note.
- Nothing else changes: objects, other lines and ids stay the same.

Out of scope: changing SpiderFoot's global module options (e.g. certificate fetching), raising the default timeout, retrying a stopped scan.

## Assumptions (approved by the user's standing instruction to proceed)

1. The CTO decision on 2026-10-04 is to make incompleteness visible first and leave tuning (timeout, module options) to the owner, with the evidence above recorded for that decision.
2. `ScanOutcome.timed_out` is set only by the connector's own timeout path; `status` comes from SpiderFoot.

## Test strategy

Unit: finding present for a timeout (with the number of seconds), for a non-FINISHED status, absent for FINISHED, first in the list, never the empty form; connector passes each scan's outcome and the configured timeout.
Real data: the aborted scan `06410167`. Live: the connector's own message and Note for a forced short timeout.

## Boundaries

**Always**: state incompleteness in the Note, not only in the work message.
**Ask first**: changing SpiderFoot's global settings or the default timeout.
**Never**: present a partial scan's absence of findings as a clean result.
