# SPEC: event-catalogue

Status: approved
Extends: [SPEC-spiderfoot-connector.md](SPEC-spiderfoot-connector.md) (mapping), [SPEC-fast-scan-profile.md](SPEC-fast-scan-profile.md) (lean profile)

## Objective

Make "how much of SpiderFoot's value does octifoot carry into OpenCTI" measurable. For every event type SpiderFoot v4.0 can emit,
record what octifoot does with it and why, from evidence, so further mapping work is chosen by value instead of by guess.

Evidence: SpiderFoot v4.0 defines 172 event types; octifoot imported 15 (9 %). The lean list can produce 112 of them. Across 21 real passive scans of 3 domains only
46 types ever appeared.

Success:
- A committed catalogue with one entry per event type: SpiderFoot category and description, what it takes to produce it with this configuration
  (`passive`, `denied-module`, `api-key`, `active`, `none`), producing modules, how often real scans emitted it, and a decision
  (`imported`, `planned`, `declined`, `blocked`, `no-data`) with a rationale; `planned` names the slice that will do it.
- Tests fail if a type has no entry, an observed type is undecided, `imported` differs from the mapper's `IMPORTED_EVENTS`, third-party families
  (`AFFILIATE_*`, `CO_HOSTED_*`, `BLACKLISTED_*`) are not declined, or the JSON or `docs/event-catalogue.md` drift from the generator.
- Decisions about observed-but-not-imported types rest on the values real scans produced, recorded in the rationale.

Out of scope: implementing any mapping (each is its own slice); running active or keyed modules.

## Assumptions (approved by the user's standing instruction to proceed)

1. Inputs: SpiderFoot's own `eventDetails` table at `v4.0` (identical to the live `/eventtypes`, 172 rows), the committed module snapshot, and counts of
   observed events per type (counts only; no third-party values are committed).
2. "Observed" means appeared in the 21 stored scans of registrolineas.com, bugoverflow.com and zonetransfer.me (lean and full profiles).
3. Types policy-declined regardless of data: `AFFILIATE_*`, `MALICIOUS_AFFILIATE_*`, `CO_HOSTED_*` (third parties), `BLACKLISTED_*` (not equivalent to malicious).
4. `blocked` types are those only producible by keyed or non-passive modules; unblocking them is the owner's decision (keys, explicit permission for active modules).

## Commands

```bash
cd connector && . .venv/bin/activate
python tools/build_catalogue.py     # regenerate data/event_catalogue.json and docs/event-catalogue.md
pytest && ruff check . && ruff format --check .
```

## Test strategy

Unit: `classify_needs` on synthetic metadata; the committed catalogue against the real snapshots, the mapper and the generator; the Markdown against the renderer.

## Boundaries

**Always**: record the evidence behind a decision; keep the catalogue generated, not hand-edited.
**Ask first**: unblocking a type (API keys, active modules).
**Never**: mark a third party's data as the target's to make the catalogue look more complete.
