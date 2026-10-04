---
topic: external-integrations
priority: low
---

### read-upstream-source-for-api-contracts
_derived_from: reflection/spiderfoot-connector.md · evidence_count: 1 · last_validated: 2026-10-04_

Before writing a client or fixtures for a third-party HTTP API, read the upstream handler source at the pinned tag (parameter values, casing, response shape, terminal states) instead of relying on docs or memory.

### mapper-fixtures-from-real-payloads
_derived_from: reflection/spiderfoot-connector.md · evidence_count: 1 · last_validated: 2026-10-04_

Build mapper test fixtures from the field names the upstream code actually emits, and count and report unmapped input types instead of dropping them silently.

### inspect-real-output-before-specifying-a-mapping
_derived_from: reflection/risk-signal-mapping.md · evidence_count: 1 · last_validated: 2026-10-04_

Before writing a spec that maps third-party data, read real output from a real run; the requested field list can look right and still describe the wrong entities.
