# Reflection: provenance-coverage

Spec: [SPEC-provenance-coverage.md](../specs/SPEC-provenance-coverage.md) · Date: 2026-10-05

## Implementation vs spec

All criteria met. Each scan Note (root and sub-scans) carries a Provenance line (octifoot and SpiderFoot versions, profile, use case, module count with list digest, applied time, event count with SHA-256 digest) and a Coverage line (modules that produced data, modules with errors, API-keyed modules by name). `/ping` supplies the SpiderFoot version, `unknown` on any failure. README and docs gained the personal-data and data-handling text.
Live (zonetransfer.me): the Note showed 104 requested modules, 18 producing data, 13 with errors; the digest `cfbc45de272d22a5` was recomputed from SpiderFoot's own JSON export (133 events) and matched, so the claim in the docs was checked, not assumed.

## Deviations

- The data-handling check the spec called for: `EMAILADDR` is the only personal data imported, WHOIS contact text is never copied. Documented as it is; no code change needed.
- A first draft of one digest test used a contorted expression; rewritten before it ever ran green on it.

## Workflow

- Routing "standard" fit; tests first again drove the design (pure `provenance.py`, mapper only takes `extra_lines`).
- The external report supplied the idea, but the useful part was filtering it against what already existed: most of it was already covered or out of scope, which kept this to three small changes.

## Rules extracted

- verify-a-documented-claim-against-the-real-system (external-integrations)
- filter-an-external-report-against-the-existing-product (safety-boundaries)
