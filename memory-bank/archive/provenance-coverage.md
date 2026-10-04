# Archive: provenance-coverage

Closed 2026-10-05 · Spec: [SPEC-provenance-coverage.md](../specs/SPEC-provenance-coverage.md) · Reflection: [reflection/provenance-coverage.md](../reflection/provenance-coverage.md) · Builds on: [archive/total-deadline.md](total-deadline.md)

## What was built

Reproducibility and coverage in every scan Note: a Provenance line (versions, profile, use case, module list digest, applied time, event count and SHA-256 digest of SpiderFoot's export) and a Coverage line (modules that produced data, modules with errors, API-keyed modules by name). `provenance.py`, `SpiderFootClient.version()`, `extra_lines` in the mapper, wiring in the connector. README and `docs/README.md` document the provenance lines and data handling (the only personal data imported is email addresses; WHOIS contact data is never copied; retention and removal).

- 675 tests, `ruff` clean
- Live: zonetransfer.me; the digest in the Note was recomputed from SpiderFoot's JSON export and matched

## Deviations accepted

None.

## Not done / next

- A second discovery source (Amass, Apache-2.0) to cross-check subdomains; adopt only if a measurement shows subdomains SpiderFoot misses.
- Run-time metrics (time to first data, duration per scan) for the owner's own use.
- A "stop analysis" control in the panel.
