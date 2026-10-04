---
slug: scan-changes
spec: SPEC-scan-changes.md
status: approved
---

## Implementation Roadmap

Routing: standard.

- [x] Phase 1 — `changes.py` (snapshot, diff, Note text, retrieval), connector wiring, tests (satisfies: SPEC-scan-changes.md#objective, SPEC-scan-changes.md#boundaries)
- [x] Phase 2 — Docs and live check with two replayed real scans (satisfies: SPEC-scan-changes.md#test-strategy)

## Execution State

**Build Status**: COMPLETE
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {1: 1, 2: 1}
**Last Block Rule**: none
**Can Resume**: NO

## Deviations

- Two real defects found by the live replays, both fixed test-first before closing: (1) an incomplete scan with nothing added said "no changes", which is misleading because disappearances are not assessed; it now says "no additions ... disappearances are not assessed";
  (2) the serialized snapshot did not sort its lists, so equivalent inputs produced different text (found by a unit test). A third, cosmetic: "1 changes".
- Two of my unit tests encoded wrong assumptions (alphabetical, not numeric, ordering; the snapshot line legitimately holds the full list). Corrected in the tests, not the code.
- Ruff reformatted lines that my scripted patches expected verbatim twice; I stopped patching blind and read the current code before each patch.

**Retrieval probe (real OpenCTI):** `attribute_abstract` with the `starts_with` operator returns the right Notes; the free-text `search` is fuzzy and is not used.

**Live check (2026-10-04, connector rebuilt from this branch):** six replays of two recorded real scans of zonetransfer.me (the 3.5-minute scan `A074967B` and the 15-minute `06410167`, which really ended ABORTED), each through `process_message` with the real helper:
1. first: `first snapshot`, nothing to compare;
2. `06410167` as ABORTED: `2 changes`: `hostnames added: www.zonetransfer.me`, `certificates added: 10 (...)`, with the caveat that disappearances are not reported;
3. `A074967B` after an incomplete one: `no additions ...; disappearances are not assessed` (the wording fix);
4. the same scan again, both complete: `no changes since the previous scan`;
5. `06410167` with a replay override to FINISHED (artificial, to exercise the complete-to-complete path): the same two additions;
6. back to `A074967B`, both complete: `hostnames not seen this time: www.zonetransfer.me (subdomain sources reported errors: they may not be gone)`; certificates not reported as removed, by design.
The six snapshot Notes created by the replays were deleted afterwards and zero remain, so the next real enrichment starts from a clean baseline.
Not seen live: other categories (IPs, emails, AS, infrastructure, SPF/DMARC state changes; unit-tested), and a comparison between two real scans run by the connector itself.
