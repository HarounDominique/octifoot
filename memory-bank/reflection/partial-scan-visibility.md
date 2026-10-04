# Reflection: partial-scan-visibility

Date: 2026-10-04 · Spec: SPEC-partial-scan-visibility.md (approved) · Plan: 2 phases DONE · Live check: forced 25 s timeout, Note read back from OpenCTI

## Implementation vs spec

| Spec requirement | Result |
|---|---|
| Timeout: first finding states the seconds | Met; live with a 25 s timeout |
| Other non-FINISHED status: first finding says so, without claiming a timeout | Met (tests) |
| FINISHED adds nothing; a partial scan is never the "nothing notable" form | Met |
| Each scan of an expansion carries its own flag | Met (the connector passes each outcome; unit-tested) |

Deviations: none.

## What went wrong earlier

- The connector had always imported partial results after a timeout and said so only in the work's result message. That was acceptable when scans took three minutes; once crt.sh recovered and a certificate-rich domain took 15 minutes,
  the Note presented a cut-off scan as complete. I read those Notes for two other tasks and drew conclusions from them without checking the scan's end status.
- I noticed it only by looking at the scan's duration (923 s against a 900 s limit) while reading a Note for another purpose.

## Workflow evaluation

- The root-cause read of the scan log (what ran for 15 minutes) turned a vague "scan was slow" into a specific finding (certificate fetching plus the event flood), recorded as evidence for the owner's tuning decision instead of changing SpiderFoot's global options blindly.
- Forcing a short timeout is a cheap, deterministic way to exercise a rarely-hit failure path live; it needed an explicit restore step, which I verified.

## Rules extracted

- New `check-the-end-status-of-the-scan-behind-any-evidence` (external-integrations).
- Reinforced: `measurement-harness-rejects-truncated-runs` (evidence 3): the same class of defect, this time in the product itself.

## Follow-ups (not blocking)

- Certificate-rich domains exceed 900 s; the owner may raise the timeout. A cap on certificate fetching is not available in SpiderFoot v4.0 and would need a global module option.
