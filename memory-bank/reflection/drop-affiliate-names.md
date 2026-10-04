# Reflection: drop-affiliate-names

Date: 2026-10-04 · Spec: SPEC-drop-affiliate-names.md (approved) · Plan: 2 phases DONE · Live check: fresh scan read back, plus old-vs-new on recorded real events

## Implementation vs spec

| Spec requirement | Result |
|---|---|
| `AFFILIATE_INTERNET_NAME` produces no object or relationship and is counted as unmapped | Met; live: `AFFILIATE_INTERNET_NAME=22` in the Note, `domain-name=1` |
| `INTERNET_NAME` and every other object unchanged | Met: real-event diff shows nothing added or changed, only affiliate domains and their relationships removed |
| A name that is also an own `INTERNET_NAME` is still imported | Met (test) |
| IP from an unimported affiliate host is not linked to the target | Met (test); 0 real cases |
| `IMPORTED_EVENTS` no longer lists it; profile coverage test passes | Met |

Deviations: none. It reverses an early design choice of the connector (import at half score) by the user's decision.

## What the change did

Per scan the object count dropped from 39 to 5 (zonetransfer.me), 17 to 7 (bugoverflow.com) and 18 to 14 (registrolineas.com), and the OpenCTI work for
zonetransfer.me went from 42 to 8 objects. What was removed was Google's mail servers, reverse-DNS names of Google IPs, and name servers. The information is not lost:
mail and name servers remain in the `Infrastructure` Note line and the unmapped count shows how many affiliate names were seen.

## Workflow evaluation

- The risky part was not the removal but what depended on the removed objects: `domains.get(source_host, target_obj)` would have linked a dropped host's IP to the
  target. It was found by reading the code that consumed `domains`, before running anything; real data had no such case, so only a synthetic test exercises it.
- Quantifying the effect first (2 of 2, 5 of 6, 17 of 17) turned an opinion into a measured decision and went straight into the spec.
- Old-vs-new on recorded events gave a cheap proof that only the intended objects changed, as in the previous mapper task.
- This does not touch the modules that produce those names: part of the co-hosted chain in `lean` now only feeds affiliate events. Whether to deny those modules needs
  an A/B (valid runs) and was left out on purpose.

## Rules extracted

- New `when-dropping-an-entity-audit-fallbacks-that-linked-to-it` (safety-boundaries).
- Reinforced: `never-attribute-shared-infrastructure-to-the-target` (evidence 2).

## Follow-ups (not blocking)

- A/B to see whether modules that now only feed affiliate events can be denied (lean already runs in about 3 minutes).
- Objects imported by earlier scans stay in OpenCTI; deleting them is a separate, explicit decision.
