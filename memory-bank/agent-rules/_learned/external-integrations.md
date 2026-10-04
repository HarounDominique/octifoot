---
topic: external-integrations
priority: low
---

### read-upstream-source-for-api-contracts
_derived_from: reflection/spiderfoot-connector.md · evidence_count: 1 · last_validated: 2026-10-04_

Before writing a client or fixtures for a third-party HTTP API, read the upstream handler source at the pinned tag (parameter values, casing, response shape, terminal states) instead of relying on docs or memory.

### mapper-fixtures-from-real-payloads
_derived_from: reflection/spiderfoot-connector.md, reflection/x509-certificates.md · evidence_count: 2 · last_validated: 2026-10-04_

Build mapper test fixtures from the field names the upstream code actually emits, and count and report unmapped input types instead of dropping them silently.

### inspect-real-output-before-specifying-a-mapping
_derived_from: reflection/risk-signal-mapping.md, reflection/asn-enrichment.md, reflection/reputation-and-infra-notes.md, reflection/source-health-note.md, reflection/event-catalogue.md · evidence_count: 5 · last_validated: 2026-10-04_

Before writing a spec that maps third-party data, read real output from a real run; the requested field list can look right and still describe the wrong entities.

### round-trip-new-fields-through-the-real-target
_derived_from: reflection/iterative-scan-loop.md, reflection/asn-enrichment.md, reflection/whois-dns-notes.md · evidence_count: 3 · last_validated: 2026-10-04_

When a change adds fields a downstream system ingests, import them into the real system once and read them back; asserting the generated object does not prove the system kept it (OpenCTI silently drops external references without external_id or url).

### replay-recorded-events-when-upstream-is-nondeterministic
_derived_from: reflection/iterative-scan-loop.md, reflection/reputation-and-infra-notes.md, reflection/x509-certificates.md · evidence_count: 3 · last_validated: 2026-10-04_

If a third-party source gives different results per run, save the real events from a run that exhibits the case and replay them through the code into the real target, instead of waiting for a fresh run to reproduce it.

### confirm-through-the-production-path-before-concluding
_derived_from: reflection/reputation-and-infra-notes.md · evidence_count: 1 · last_validated: 2026-10-04_

When a shortcut replay (a direct API import) shows a missing result, repeat it through the path production uses (connector helper, queue, worker) before concluding the feature is broken or fine; the shortcut and the real path can disagree.

### empty-live-result-check-source-health
_derived_from: reflection/live-expansion-check.md, reflection/source-health-note.md · evidence_count: 2 · last_validated: 2026-10-04_

When a live scan returns less than the target is known to have, read the upstream modules' error rows and probe their sources before concluding the target has nothing; third-party sources fail silently (HTTP 502 reported as "no information").

### a-log-derived-diagnostic-must-say-what-the-log-cannot-show
_derived_from: reflection/source-health-note.md · evidence_count: 1 · last_validated: 2026-10-04_

When a user-facing diagnostic is built from an upstream log, state inside it what the log cannot reveal (here: modules that report an outage as "no information"), so its absence is never read as proof of health.

### measure-coverage-against-observed-output
_derived_from: reflection/event-catalogue.md · evidence_count: 1 · last_validated: 2026-10-04_

Report integration coverage against what real runs actually emitted (15 of the 46 types seen), not against what the tool could emit (15 of 172), and mark per type whether the mapper has been proven on real data or only on fixtures.

### retry-only-idempotent-requests-when-polling-a-long-job
_derived_from: reflection/whois-dns-notes.md · evidence_count: 1 · last_validated: 2026-10-04_

When a client polls a long-running remote job, retry transient connection errors on idempotent GETs (a few attempts, injected sleep) so one dropped keep-alive connection does not abort minutes of work, and never retry the request that starts the job.
