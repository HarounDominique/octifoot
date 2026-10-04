# Archive: fix-additions-may-be-visibility

Closed 2026-10-04 · Spec: [SPEC-scan-changes.md](../specs/SPEC-scan-changes.md) (amended) · Reflection: [reflection/fix-additions-may-be-visibility.md](../reflection/fix-additions-may-be-visibility.md) · Corrects: [archive/scan-changes.md](scan-changes.md)

## What was built

Two real consecutive scans of bugoverflow.com differed only because crt.sh answered the second time; the changes Note reported a new hostname and 13 certificates as additions. Snapshots now record `source_gaps`, hostname additions after a scan whose subdomain sources failed carry
"this may only be newly visible", and certificate additions where the previous scan had none carry "crt.sh may not have answered". Older snapshots remain readable.

- 370 tests, `ruff` clean; README and the scan-changes spec amended
- Verified live by replaying two recorded scans of zonetransfer.me (both caveats shown); the replay Notes were deleted; the two real bugoverflow.com snapshots were kept as the real baseline

## Deviations accepted

Spec amended after the fact.

## Not done / next

- crt.sh outages remain undetectable; a direct probe (outbound request, "ask first") would turn the caveat into a fact.
