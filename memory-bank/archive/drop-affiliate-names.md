# Archive: drop-affiliate-names

Closed 2026-10-04 · Spec: [SPEC-drop-affiliate-names.md](../specs/SPEC-drop-affiliate-names.md) · Reflection: [reflection/drop-affiliate-names.md](../reflection/drop-affiliate-names.md) · Builds on: [archive/source-health-note.md](source-health-note.md), [archive/reputation-and-infra-notes.md](reputation-and-infra-notes.md)

## What was built

`AFFILIATE_INTERNET_NAME` is no longer imported: no `domain-name` object, no relationship, no half-score; it is counted under "Unmapped event types" in the Note.
Because the mapper used `domains.get(source_host, target_obj)`, an IP whose source host is such a name is now skipped and counted instead of being linked to the target.
`DOMAIN_EVENTS` is `{INTERNET_NAME}`, `IMPORTED_EVENTS` and the README table updated.

- 192 tests (8 new, 3 rewritten), `ruff` clean
- Real events: only affiliate domains and their relationships disappear (zonetransfer.me 39 to 5 objects, bugoverflow.com 17 to 7, registrolineas.com 18 to 14)
- Verified live: zonetransfer.me scan `A074967B`, work 8/8 (was 42), Note with `domain-name=1`, AS, Infrastructure line and `AFFILIATE_INTERNET_NAME=22` unmapped

## Deviations accepted

Reverses the original design (affiliates at half score) by the user's decision of 2026-10-04.

## Not done / next

- Objects imported by earlier scans remain in OpenCTI (Google MX hosts etc.); deleting them is an explicit decision.
- Modules that now only feed affiliate events may be deniable; needs a valid A/B.
- The IP-from-affiliate-host guard has no real case yet (0 of 7 scans).
