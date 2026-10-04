# Reflection: fix-infra-attribution

Date: 2026-10-04 · Spec: SPEC-fix-infra-attribution.md (approved) · Plan: 2 phases DONE · Live check: re-enrichment read back from OpenCTI, plus real events against `dig` ground truth

## Implementation vs spec

| Spec requirement | Result |
|---|---|
| Registrar, DNS and mail counted only when their source is the target or a parent | Met (tests, real data) |
| Hosting counted only for an IP imported for the target, independent of event order | Met |
| Third-party mail never triggers the mail-without-SPF finding | Met |
| bugoverflow.com shows no mail host or finding; zonetransfer.me keeps both | Met, against `dig` |

Deviations: none.

## What went wrong earlier

- The `Infrastructure` line shipped without a source check although WHOIS and TXT, built later, had one. The rule "check `source_data`" existed in my head per feature but was not applied to the older mapping.
- Two tasks then built on top of it (the key finding used the wrong mail host) and both were "verified live". The live checks asserted that a line existed and the pipeline finished; they did not compare the line's inputs with the target's real records.
- The error surfaced only because the next task began with a ground-truth `dig` for a different reason (planning DNS checks). It was found by design of the investigation, not by a test.

## Workflow evaluation

- Reporting the defect immediately, fixing it test-first, correcting every earlier note that repeated the wrong claim, and re-verifying on the real target kept the record honest.
- The fix was small because the source filter already existed as `_is_target_or_parent`; the cost was in the three archived claims that had to be corrected.

## Rules extracted

- New `check-source-on-every-event-type-that-names-a-domains-records` (safety-boundaries).
- New `compare-imported-values-with-ground-truth-in-live-checks` (external-integrations).
- Reinforced: `never-attribute-shared-infrastructure-to-the-target` (evidence 3).

## Follow-ups (not blocking)

- A catalogue check that flags event types carrying a domain's own records without a source rule would catch this class earlier.
