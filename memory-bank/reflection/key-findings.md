# Reflection: key-findings

Date: 2026-10-04 · Spec: SPEC-key-findings.md (approved) · Plan: 2 phases DONE · Live check: fresh scan read back from OpenCTI; findings compared with `dig` ground truth

## Implementation vs spec

| Spec requirement | Result |
|---|---|
| Block at the top of the Note with seven rule-based findings, each tied to evidence | Met; 21 tests; live on bugoverflow.com |
| Findings appear only with their evidence; empty wording never says "clean" | Met (tests) |
| Never claim DMARC/DKIM | Met (test) |
| No objects, labels or scores derived from findings | Met |

Deviations: coverage uses a curated source list validated by a test (see task file). Accepted.

## What this iteration is and is not

- It adds synthesis, not data: the same facts, ranked by what an analyst should look at first. On the three test domains it states three real things: one domain is a week old, two receive mail without SPF, and subdomain discovery is unreliable right now.
- It is also the first output where an analyst can act without reading the rest of the Note, which is the part neither SpiderFoot's raw event list nor an empty OpenCTI gives.
- Three of the seven rules (flagged hosts, certificate expiry, registration expiry) did not fire on any real domain, so they are proven on synthetic data only.

## Workflow evaluation

- Checking the inference with `dig` before writing the rule paid off twice: it confirmed "no SPF" was true (SpiderFoot's silence was not a lookup failure) and it exposed what cannot be claimed (DMARC, because SpiderFoot never queries `_dmarc`). That second point is a real product gap, taken as the next iteration.
- The ordering and the neutral empty wording were decided in the spec, so there was no rework on them.

## Rules extracted

- New `validate-absence-claims-against-ground-truth` (external-integrations).

## Follow-ups (not blocking)

- Own DNS checks (DMARC, CAA, DNSSEC presence), which would feed new findings with data SpiderFoot does not produce.
