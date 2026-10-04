# Archive: fix-infra-attribution

Closed 2026-10-04 · Spec: [SPEC-fix-infra-attribution.md](../specs/SPEC-fix-infra-attribution.md) · Reflection: [reflection/fix-infra-attribution.md](../reflection/fix-infra-attribution.md) · Corrects: [archive/reputation-and-infra-notes.md](reputation-and-infra-notes.md), [archive/key-findings.md](key-findings.md)

## What was built

A fix for a misattribution: registrar, name-server and mail records now count only when their source is the scanned domain (or a parent), and hosting only for an IP that was imported for the target. A provider's records seen in the same scan
(bugoverflow.com's CNAME target `dinaserver.com`) are counted as "not the target's" and no longer appear in the `Infrastructure` line or trigger the mail-without-SPF finding.

- 275 tests (7 new), `ruff` clean; README updated; earlier tasks' notes and archives corrected
- Real data against `dig`: bugoverflow.com (no MX) shows no mail host or finding; zonetransfer.me (MX present) keeps both. Verified live (scan `B3A1775D`, work 10/10)

## Deviations accepted

None.

## Not done / next

- A catalogue check that flags event types carrying a domain's own records without a source rule.
