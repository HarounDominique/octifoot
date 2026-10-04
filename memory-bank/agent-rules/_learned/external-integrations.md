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
_derived_from: reflection/risk-signal-mapping.md, reflection/asn-enrichment.md, reflection/reputation-and-infra-notes.md · evidence_count: 3 · last_validated: 2026-10-04_

Before writing a spec that maps third-party data, read real output from a real run; the requested field list can look right and still describe the wrong entities.

### round-trip-new-fields-through-the-real-target
_derived_from: reflection/iterative-scan-loop.md, reflection/asn-enrichment.md · evidence_count: 2 · last_validated: 2026-10-04_

When a change adds fields a downstream system ingests, import them into the real system once and read them back; asserting the generated object does not prove the system kept it (OpenCTI silently drops external references without external_id or url).

### replay-recorded-events-when-upstream-is-nondeterministic
_derived_from: reflection/iterative-scan-loop.md, reflection/reputation-and-infra-notes.md · evidence_count: 2 · last_validated: 2026-10-04_

If a third-party source gives different results per run, save the real events from a run that exhibits the case and replay them through the code into the real target, instead of waiting for a fresh run to reproduce it.

### confirm-through-the-production-path-before-concluding
_derived_from: reflection/reputation-and-infra-notes.md · evidence_count: 1 · last_validated: 2026-10-04_

When a shortcut replay (a direct API import) shows a missing result, repeat it through the path production uses (connector helper, queue, worker) before concluding the feature is broken or fine; the shortcut and the real path can disagree.
