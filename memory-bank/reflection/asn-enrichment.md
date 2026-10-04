# Reflection: asn-enrichment

Date: 2026-10-04 · Spec: SPEC-asn-enrichment.md (approved) · Plan: 2 phases DONE · Live check: done, full round-trip and end-to-end

## Implementation vs spec

| Spec requirement | Result |
|---|---|
| Imported IPs linked to `autonomous-system` with `belongs-to` via netblock chain (v4 and v6) | Met; live: AS13335 linked to all 4 IPs |
| No orphan AS; no netblock objects; no AS-domain link | Met (unit tests); live graph shows only IP→AS links |
| ASN validated 1..4294967295, invalid counted | Met |
| Provenance (external_id = scan id) | Met; live AS merged references from two scans |
| Note line with ASNs and IP counts | Met; live: "Autonomous systems: AS13335 (4 IPs)" |
| Netblock/BGP events no longer unmapped | Met |
| Round-trip through real OpenCTI before archive | Done twice: replay of recorded real events, then a fresh connector scan (20 objects, no errors, no duplicate AS) |

Deviations: none.

## Workflow evaluation

- Reading real events first showed the exact chain (`NETBLOCK_MEMBER.source_data` = IP, `BGP_AS_MEMBER.source_data` = CIDR) and kept the design to ~40 lines of mapper.
- This time the live round-trip was part of the spec's Boundaries ("Always"), not an afterthought; it would have caught the previous iteration's dropped-reference bug.
- Edits to `mapper.py` were exact-match edits, no failed patch. Routing "standard" fit; 2 phases, no spec correction.
- Residual gap: AS names are not available from these events, so OpenCTI shows only the number.

## Rules extracted

No new rules. Reinforced with evidence: `round-trip-new-fields-through-the-real-target`, `inspect-real-output-before-specifying-a-mapping`, `patch-with-exact-edits-and-verify`.
