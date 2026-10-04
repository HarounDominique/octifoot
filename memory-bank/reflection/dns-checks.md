# Reflection: dns-checks

Date: 2026-10-04 · Spec: SPEC-dns-checks.md (approved) · Plan: 2 phases DONE · Live check: enrichment read back from OpenCTI; `check_domain` compared with `dig` on four domains

## Implementation vs spec

| Spec requirement | Result |
|---|---|
| Root target only: MX, SPF, `_dmarc`, CAA, DS, `_mta-sts` through the resolver | Met; live: the sub-scan Note has no DNS line |
| Found / confirmed absent / unknown; unknown never reported as absent | Met (tests); the resolver never failed live, so unknown is proven on fakes only |
| `DNS checks (queried by octifoot, not by SpiderFoot)` line | Met |
| Mail findings only for a name with MX; native facts replace the event-based inference; fallback keeps its disclaimer | Met (tests); live for no-SPF and no-DMARC |
| A failing check never fails the enrichment; no objects added | Met (tests) |

Deviations: a null-MX bug fixed during the build (see task file).

## What it adds

This is the first output in the project that SpiderFoot cannot produce at all: DMARC, CAA, DNSSEC and MTA-STS, with confirmed absence. For zonetransfer.me the Note now states that it receives mail but publishes neither SPF nor DMARC,
on the target's own MX and from direct queries rather than inferred from scan events, which had misled once (see `fix-infra-attribution`).

## Workflow evaluation

- A positive control (`example.com`, which publishes SPF, DMARC and a DS record) was the only thing that exposed the null-MX case; the three real targets all had empty answers and would have passed with any parser.
- My ground-truth comparison used the same normalisation as the code, so it agreed with the bug. A ground-truth check must use an independent reading of the answer, not a copy of the same logic.
- Running the live check on a domain that was supposed to exercise one feature also exercised others (expansion, certificates), and surfaced two defects (certificate attribution, mail finding on sub-scans) that no earlier check had reached.

## Rules extracted

- New `use-a-positive-control-and-an-independent-ground-truth-reading` (external-integrations).
- Reinforced: `compare-imported-values-with-ground-truth-in-live-checks` (evidence 2).

## Follow-ups (not blocking)

- `tls-attribution-by-query` and `mail-findings-root-only` (found by this live run).
- DKIM is not checkable (selectors unknowable); organisational-domain DMARC inheritance for subdomain targets is not modelled.
