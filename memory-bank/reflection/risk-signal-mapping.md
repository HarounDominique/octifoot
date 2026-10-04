# Reflection: risk-signal-mapping

Date: 2026-10-04 · Spec: SPEC-risk-signal-mapping.md (approved) · Plan: 3 phases, all DONE · Live check: not run

## Implementation vs spec

| Spec requirement | Result |
|---|---|
| IPv6 imported like IPv4 | Met (unit-tested with relationship) |
| Flagged output IP gets label + per-feed reference | Met; two feeds → one label, two references |
| Flagged IP not in output skipped and counted | Met |
| Subnet/co-host only in Note, max 20 then "and N more" | Met |
| `AFFILIATE_*` never produce objects | Met, counted as unmapped |
| Unparsable feed data counted invalid | Met |
| Live confirmation in OpenCTI | **Not done**: stack was paused at the user's request; procedure recorded in the task file |

Deviations: none against the spec. Against the user's original request, `MALICIOUS_SUBNET`/`MALICIOUS_COHOST` became Note lines and `AFFILIATE_EMAILADDR` stayed unmapped; agreed with the user before the spec was written.

## Workflow evaluation

- The decisive step was reading the real events from the previous scan *before* writing the spec. The original list would have linked unrelated Cloudflare customers and their WHOIS emails to the target.
- Routing "standard" fit; 3 small phases, no creative pass needed, no spec correction mid-build.
- Two self-inflicted slips, both caught by the process: a test missing `import json` (not a valid RED, fixed before implementing) and a blind string-replace patch that silently missed because ruff had reformatted the target line (caught by a failing test, fixed with an exact edit).
- Gap: no live verification before archive; the evidence is the unit suite plus a fixture derived from the real scan.

## Rules extracted

`external-integrations` (inspect real output before specifying a mapping), `safety-boundaries` (never attribute shared-infrastructure data to the target), `code-editing` (patch with exact-match edits and verify the change landed).
