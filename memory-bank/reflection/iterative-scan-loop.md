# Reflection: iterative-scan-loop

Date: 2026-10-04 · Spec: SPEC-iterative-scan-loop.md (approved) · Plan: 3 phases DONE · Live check: done, with one caveat

## Implementation vs spec

| Spec requirement | Result |
|---|---|
| Default (depth 0) identical to before | Met (unit test; live run with depth 1 and no subdomains behaved as one scan) |
| Allowlisted subdomains scanned breadth-first, once each, bounded by scans | Met (unit tests with fake client) |
| Out-of-scope discoveries never scanned, reported | Met (unit tests, incl. look-alike `evilexample.com`) |
| Sub-scan failure tolerated, root failure raises | Met (unit tests) |
| Summary message and Note | Met; seen live: "Expansion: scans=1 depth=0 ..." and the expansion Note |
| Limits 0-3 depth, 1-20 scans, off by default | Met (config tests, compose defaults) |

Not proven live: the multi-scan path. The only available domain sits behind Cloudflare and has no
discoverable subdomains, so expansion had nothing to follow. That path rests on unit tests with a fake client.

## Defect found in the previous iteration

Live verification of `risk-signal-mapping` (already merged) exposed a real bug: per-feed external
references lacked `external_id`/`url` and OpenCTI dropped them silently, while the label arrived. 95
passing unit tests could not see it because they assert the generated object, not what OpenCTI accepts.
Fixed here with a regression test and verified by replaying the real events into OpenCTI. The Maltiverse
flag itself is non-deterministic across scans, so a fresh scan could not reproduce it on demand.

## Workflow evaluation

- Autonomy was granted ("no te detengas"); SEED gates were still produced (spec, plan, review, reflect, archive) rather than skipped.
- Scoping the loop to allowlisted `INTERNET_NAME` only turned a risky feature into one that cannot widen authorization by construction.
- Slips caught by process: a test asserting capitalized "Expansion" against a lowercase abstract (it would have passed vacuously for the depth-0 case); caught because the positive case failed first.
- Lesson: ending an iteration without a live check let a bug ship to `main`; the "live check not run" caveat in the previous archive was exactly where it hid.

## Rules extracted

`external-integrations` (round-trip new fields through the real target; replay recorded events when upstream is nondeterministic), `safety-boundaries` (autonomous expansion must be opt-in, bounded, and gated per step; allowlist layering reinforced, evidence 2).
