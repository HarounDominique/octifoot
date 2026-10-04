# Archive: api-keys

Closed 2026-10-04 · Spec: [SPEC-api-keys.md](../specs/SPEC-api-keys.md) · Reflection: [reflection/api-keys.md](../reflection/api-keys.md) · Builds on: [archive/fast-scan-profile.md](fast-scan-profile.md)

## What was built

Optional free API keys for keyed SpiderFoot modules. `SPIDERFOOT_API_KEYS_FILE` points to a JSON file (mounted read-only from `deploy/secrets/`, git-ignored). The connector validates it at start (unknown module, non-keyed or active module, blank or over-long value are refused, naming the entry and never the value),
and before each enrichment writes every key into SpiderFoot under the `<module>:<option>` name it actually stores, after checking the option exists, and reads it back; a key that cannot be verified is dropped for that run. The `lean` list gains exactly the keyed modules whose key was verified.
Key values never appear in logs, Notes, objects or errors. A configuration error now exits with code 2 and a readable message before the connector registers.

- `apikeys.py`, `SpiderFootClient.get_options/save_options`, `profiles.lean_modules_with`, connector and config wiring, Compose mount, `deploy/secrets/`, `docs/api-keys.md`; 463 tests, `ruff` clean
- Verified live against the real SpiderFoot with a dummy value and a simulated scan (104 -> 105 modules, stored, verified, reverted; no leak in any log, Note or reference); no real provider key and no third-party call involved
- Open source only: no dependency added

## Deviations accepted

Readable-configuration-error fix found during verification.

## Not done / next

- A real free key has not been tried (needs the owner to register with a provider); a provider rejecting a key would appear in the source-health line.
- Keyed modules' other event types (ports, vulnerabilities...) are not mapped; they are reachable through the SpiderFoot link.
