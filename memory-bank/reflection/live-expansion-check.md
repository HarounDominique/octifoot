# Reflection: live-expansion-check

Date: 2026-10-04 · Spec: SPEC-live-expansion-check.md (approved) · Plan: 1 phase DONE · Live check: the task itself

## Implementation vs spec

| Spec requirement | Result |
|---|---|
| One real enrichment with depth 1 completes with no work errors | Met: work complete, 20/20 objects, no errors, 7 min 4 s |
| Expansion Note states scans run, depth, failed, skipped (allowlist), skipped (budget) | Met, read back from OpenCTI |
| Discovered allowlisted subdomains scanned once each within budget | **Not exercised**: none were discovered on either test domain |
| Do not widen the allowlist to force a result | Respected |

Deviations: none from the spec. The result is partial and says so: the refusal path ran live (a real hostname,
`redirecciones.dinaserver.com`, was refused and never scanned); the success path did not.

## Workflow evaluation

- The live run cost 7 minutes and could not have exercised the success path. The discovered list can be recomputed
  from events already recorded in earlier scans in seconds; doing that first would have shown that neither authorized
  domain has allowlisted subdomains and turned a blind run into a decision (find a suitable domain, or run it only to
  check the refusal path). I recomputed it afterwards.
- Selecting the work by the id returned from `askEnrichment` worked and avoided any stale match.
- The same "not exercised live" sentence now sits in four archives. Repeating it without a plan to obtain a suitable
  target is a process gap, not a code gap; the task file now says exactly what is needed (an owned domain with public
  subdomains).
- Slip: to print `deploy/.env` I filtered secret-looking keys with a deny pattern and `RABBITMQ_DEFAULT_PASS` slipped
  through into the terminal output (a local-only broker password in a git-ignored file). No external exposure, but the
  approach was wrong.

## Second attempt

A domain published for security training (`zonetransfer.me`, owner's text: "Feel free to use this domain in your training") was allowlisted and
enriched at depth 1: 42/42, no errors, but again one scan only. The passive subdomain sources were down or empty (`crt.sh` HTTP 502 for 6+ minutes
from host and container, Sublist3r API error, CommonCrawl index unavailable, Crobat failure), and this domain's subdomains are not in certificate
transparency anyway. So the precheck I recommended in the first reflection was applicable again and I only had the result, not the prediction:
for this domain a recorded scan did not exist, which is why a cheap precheck (`curl crt.sh`) is also worth doing before a live run.
The more important finding is the silent degradation: the connector reports a successful scan with zero subdomains and nothing in the Note
says the sources failed.

## Rules extracted

- New `precheck-live-preconditions-from-recorded-data` (deployment); reinforced by the second attempt (evidence 2).
- New `empty-live-result-check-source-health` (external-integrations).
- New `print-env-files-with-an-allowlist` (safety-boundaries).

## Follow-ups (not blocking)

- Run the expansion on a domain the owner controls that has public subdomains, to verify the scan-merge-dedupe path live.
