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
_derived_from: reflection/risk-signal-mapping.md, reflection/asn-enrichment.md, reflection/reputation-and-infra-notes.md, reflection/source-health-note.md, reflection/event-catalogue.md, reflection/opencti-knowledge.md · evidence_count: 6 · last_validated: 2026-10-04_

Before writing a spec that maps third-party data, read real output from a real run; the requested field list can look right and still describe the wrong entities.

### round-trip-new-fields-through-the-real-target
_derived_from: reflection/iterative-scan-loop.md, reflection/asn-enrichment.md, reflection/whois-dns-notes.md · evidence_count: 3 · last_validated: 2026-10-04_

When a change adds fields a downstream system ingests, import them into the real system once and read them back; asserting the generated object does not prove the system kept it (OpenCTI silently drops external references without external_id or url).

### replay-recorded-events-when-upstream-is-nondeterministic
_derived_from: reflection/iterative-scan-loop.md, reflection/reputation-and-infra-notes.md, reflection/x509-certificates.md, reflection/fix-cert-and-mail-attribution.md, reflection/scan-changes.md · evidence_count: 5 · last_validated: 2026-10-04_

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

### validate-absence-claims-against-ground-truth
_derived_from: reflection/key-findings.md, reflection/fix-additions-may-be-visibility.md · evidence_count: 2 · last_validated: 2026-10-04_

Before a rule says something is missing ("no SPF"), check with an independent tool that the upstream would have reported it if present, and never assert absence of something the upstream does not look for (here DMARC).

### compare-imported-values-with-ground-truth-in-live-checks
_derived_from: reflection/fix-infra-attribution.md, reflection/dns-checks.md, reflection/fix-cert-and-mail-attribution.md · evidence_count: 3 · last_validated: 2026-10-04_

A live check must compare the imported values, and the inputs of any rule built on them, with an independent source for the real target (`dig`, `whois`); "the line appeared and the work completed" does not show the values belong to the target.

### use-a-positive-control-and-an-independent-ground-truth-reading
_derived_from: reflection/dns-checks.md · evidence_count: 1 · last_validated: 2026-10-04_

When validating a parser against ground truth, include a subject that actually has the feature (the real targets may all be empty) and read the ground truth without reusing the parser's own normalisation, or a shared flaw will make them agree.

### a-rule-fitted-to-one-sample-is-a-hypothesis
_derived_from: reflection/fix-cert-and-mail-attribution.md · evidence_count: 1 · last_validated: 2026-10-04_

An attribution or filter rule designed from a single real sample is a hypothesis: ship it behind a count of what it rejects ("N not the target's") and re-check it the first time richer real data arrives, because 100 % rejection is as wrong as 100 % acceptance.

### check-the-end-status-of-the-scan-behind-any-evidence
_derived_from: reflection/partial-scan-visibility.md · evidence_count: 1 · last_validated: 2026-10-04_

Before using a recorded scan as evidence, check that it finished (status and duration against the timeout); a run cut by the limit looks like a normal result and silently supports wrong conclusions.

### a-diff-of-runs-of-an-unreliable-pipeline-reports-its-flakiness-as-change
_derived_from: reflection/fix-additions-may-be-visibility.md · evidence_count: 1 · last_validated: 2026-10-04_

When comparing two runs of a pipeline whose sources fail silently, an "addition" can be a source that answered this time; mark additions as possibly newly visible when the earlier run recorded source gaps, and test the diff on two real consecutive runs, not only on constructed ones.
