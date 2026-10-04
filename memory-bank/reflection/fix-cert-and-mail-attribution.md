# Reflection: fix-cert-and-mail-attribution

Date: 2026-10-04 · Spec: SPEC-fix-cert-and-mail-attribution.md (approved; amends SPEC-x509-certificates.md) · Plan: 2 phases DONE · Live check: recorded real scan replayed through the connector path, read back from OpenCTI

## Implementation vs spec

| Spec requirement | Result |
|---|---|
| Certificate is the target's when `source_data` is the scanned name or the CN covers it | Met; real scan: 10 imported instead of 0 |
| Parent-sourced certificates with another CN not imported into sub-scans | Met (test; live: the mocked sub-scan imported none) |
| Certificate finding judges only the newest certificate per CN | Met (tests) |
| Mail fallback only on records of the scanned name itself | Met (tests; the real sub-scan has no mail finding) |
| Replay of `06410167` imports 10 and reports the cap | Met; the figure is 24 over the cap, not the 43 the spec predicted (34 distinct serials) |

Deviations: the arithmetic in the spec; a half-applied scripted edit (no bad state committed).

## What went wrong earlier

- `x509-certificates` was specified from one real sample (a certificate whose CN was the target) and shipped with a rule that fitted that sample. The first time crt.sh returned real data, 100 % of the certificates were rejected.
  The reflection of that task had flagged it as "the weakest-evidenced slice" and the live check as a replay; the risk it named was the cap and volume, not the attribution rule.
- The rule's rationale (other customers' names in shared certificates) was real but the control chosen (CN only) was wrong for how crt.sh and SpiderFoot actually behave: SAN-based matches are the norm, and SpiderFoot truncates the SAN away.

## What went right

- The same live run that found the bug also produced the first real multi-scan expansion, a native DNS check against real MX records and a 53-event certificate set: one broad live run on a domain with real features revealed more than three narrow ones.
- Reading the upstream module source (`sfp_crt`) gave the actual guarantee (query name in `source_data`) instead of a guess, and let the new rule be justified.

## Rules extracted

- New `a-rule-fitted-to-one-sample-is-a-hypothesis` (external-integrations).
- Reinforced: `compare-imported-values-with-ground-truth-in-live-checks` (evidence 3), `replay-recorded-events-when-upstream-is-nondeterministic` (evidence 4).

## Follow-ups (not blocking)

- The certificate expiry finding has still never fired on real data.
- SANs remain unavailable; if SpiderFoot's truncation could be lifted, SAN-based checks (does the cert actually list the target) would replace the query-source proxy.
