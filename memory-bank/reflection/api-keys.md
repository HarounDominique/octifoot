# Reflection: api-keys

Date: 2026-10-04 · Spec: SPEC-api-keys.md (approved) · Plan: 2 phases DONE · Live check: real SpiderFoot settings API through the real connector, with a dummy value, no scan and no third party contacted

## Implementation vs spec

| Requirement | Result |
|---|---|
| Optional key file, off by default, read-only mount, git-ignored | Met (tests; `git check-ignore` confirms a real file is ignored) |
| Fail fast naming the entry, never the value | Met (tests with a sentinel); live: exit 2 with a readable message |
| Apply by the `<mod>:<opt>` name after checking the option exists, read back, compare; drop unverified keys | Met (tests with a fake that reproduces the silent no-op); live against the real SpiderFoot |
| The lean list gains exactly the keyed modules whose key was verified; a key never enables an active module | Met (tests; live 104 -> 105) |
| Values never in logs, Notes, objects, errors | Met (tests and live greps: 0 matches) |
| Open source only | Met: no dependency added; the documentation says what a key is and that the providers are third-party services |

Deviations: a readable-error fix to `main()` found during verification (see task file).

## What it does and does not do

It removes the one thing that separated octifoot from SpiderFoot-with-keys: the ability to use free keyed sources, at the cost of the owner registering for each service. It adds no new object types: 52 keyed modules produce types octifoot already imports,
so the effect is more reputation evidence and more subdomains through existing mappings. I could not verify a provider accepting a real key, because creating accounts needs the owner's identity and acceptance of terms; that is stated, not hidden.

## Workflow evaluation

- The decisive step was the round trip against the real SpiderFoot before designing: it showed that a "successful" write can store nothing. A design that trusted `SUCCESS` would have looked fine in every unit test and would have silently run keyed modules without keys.
- Verification found a second, unrelated defect (a configuration error invisible to the operator) because I tested the failure path on the real stack rather than only in unit tests.
- Keeping the live check free of third-party calls (simulated scan, dummy value) respected the spec's own "ask first" boundary and still proved the settings path end to end.

## Rules extracted

- New `verify-a-write-by-reading-it-back-when-the-api-answers-success-to-anything` (external-integrations).
- New `validate-configuration-before-registering-and-print-errors-where-the-operator-looks` (deployment).
- Reinforced: `patch-from-the-current-text-never-from-memory` (evidence 3) and `compare-imported-values-with-ground-truth-in-live-checks` (evidence 4).

## Follow-ups (not blocking)

- Try it with one real free key (the owner registers); the source-health line will show a rejected or exhausted key.
- Mapping the other event types keyed modules emit needs real data first.
