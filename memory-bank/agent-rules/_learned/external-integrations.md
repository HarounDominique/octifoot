---
topic: external-integrations
priority: low
---

### read-upstream-source-for-api-contracts
_derived_from: reflection/spiderfoot-connector.md · evidence_count: 1 · last_validated: 

Before writing a client or fixtures for a third-party HTTP API, read the upstream handler source at the pinned tag (parameter values, casing, response shape, terminal states) instead of relying on docs or memory.

### mapper-fixtures-from-real-payloads
_derived_from: reflection/spiderfoot-connector.md · evidence_count: 1 · last_validated: 

Build mapper test fixtures from the field names the upstream code actually emits, and count and report unmapped input types instead of dropping them silently.
