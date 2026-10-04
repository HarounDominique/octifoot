---
slug: dns-checks
spec: SPEC-dns-checks.md
status: approved
---

## Implementation Roadmap

Routing: standard.

- [x] Phase 1 — `dnschecks.py`, parsers, Note line, findings, connector wiring, dependency and licence notice, tests (satisfies: SPEC-dns-checks.md#objective, SPEC-dns-checks.md#boundaries)
- [x] Phase 2 — Ground truth against `dig`, docs, live check (satisfies: SPEC-dns-checks.md#test-strategy)

## Execution State

**Build Status**: COMPLETE
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {1: 1, 2: 1}
**Last Block Rule**: none
**Can Resume**: NO

## Deviations

- Bug found by the positive control and fixed before the live run: `example.com` publishes a null MX (`0 .`, RFC 7505, meaning "accepts no mail"); the first parser returned `['']`, which would have produced "receives mail (MX: )".
  The comparison with `dig` could not catch it because my ground-truth normaliser shared the flaw; only knowing what a null MX means did. Two tests added.
- Lint: a deliberate broad `except Exception` in the connector (a diagnostic must never fail the enrichment) carries an explicit `noqa: BLE001` with its reason.

**Ground truth (2026-10-04, `check_domain` vs `dig`, all six record kinds):** registrolineas.com, bugoverflow.com, zonetransfer.me and `example.com` (positive control: SPF `-all`, DMARC `p=reject`, a DS record) match field by field.

**Live check (2026-10-04, connector rebuilt from this branch; the container resolves DNS):** enrichment of zonetransfer.me (work complete 12/12, no errors). The root-scan Note read back from OpenCTI has
`DNS checks (queried by octifoot, not by SpiderFoot): MX: alt1..., alt2..., aspmx.l.google.com and 4 more; SPF: none; DMARC: none; CAA: none; DNSSEC: no DS record; MTA-STS: none`
(`dig`: 7 MX, no DMARC, CAA or DS) and the findings `publishes no SPF record` and `no DMARC record at _dmarc.zonetransfer.me`. The sub-scan Note (`www.zonetransfer.me`) carries no DNS line, as specified.

**Side results of the same live run (new facts, handled in separate tasks):**
- First live success of the multi-scan expansion: `scans run: 2, max depth reached: 1`; `www.zonetransfer.me` was discovered and scanned (crt.sh had recovered).
- crt.sh returned 53 certificates and none was imported: their CN is `digi.ninja` / `alertlab.digi.ninja` (the owner's other domains) and zonetransfer.me is only a SAN, which SpiderFoot truncates. The CN rule of `x509-certificates` is too strict.
- The sub-scan Note repeated the mail finding from the parent domain's records (fallback inference); mail findings belong to the root target.
Not seen live: unknown states (the resolver never failed), `p=none`, `+all`.
