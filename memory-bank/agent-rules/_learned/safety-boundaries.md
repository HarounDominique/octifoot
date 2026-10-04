---
topic: safety-boundaries
priority: low
---

### enforce-authorization-in-layers-and-test-the-refusal
_derived_from: reflection/spiderfoot-connector.md, reflection/iterative-scan-loop.md · evidence_count: 2 · last_validated: 2026-10-04_

For anything that touches third-party targets, enforce the allowlist at config load, at deploy (required env), and at runtime before the network call, and prove the refusal path live in E2E, including that no downstream request was made.

### never-attribute-shared-infrastructure-to-the-target
_derived_from: reflection/risk-signal-mapping.md, reflection/drop-affiliate-names.md, reflection/fix-infra-attribution.md · evidence_count: 3 · last_validated: 2026-10-04_

Data about shared hosting, CDN ranges or co-hosted sites goes in a summary note, never as objects or relationships tied to the investigated target.

### autonomous-expansion-opt-in-bounded-and-gated
_derived_from: reflection/iterative-scan-loop.md · evidence_count: 1 · last_validated: 2026-10-04_

Any feature that acts on its own discoveries must be off by default, bounded by depth and total count, restricted to discovery types that cannot leave the authorized scope, and must re-run the authorization check before every individual action.

### print-env-files-with-an-allowlist
_derived_from: reflection/live-expansion-check.md · evidence_count: 1 · last_validated: 2026-10-04_

When showing an `.env` or config file, print only an explicit allowlist of known non-secret keys; a deny-pattern on key names (`KEY|TOKEN|PASSWORD`) misses names like `*_PASS`.

### when-dropping-an-entity-audit-fallbacks-that-linked-to-it
_derived_from: reflection/drop-affiliate-names.md · evidence_count: 1 · last_validated: 2026-10-04_

When you stop importing an entity type, read every lookup that used it as a link source for a default (`get(x, target)`): a missing key can silently re-attach other parties' data to the investigated target.

### check-source-on-every-event-type-that-names-a-domains-records
_derived_from: reflection/fix-infra-attribution.md · evidence_count: 1 · last_validated: 2026-10-04_

When one scan covers several domains (a provider, a CNAME target), every event type that carries a domain's own records (MX, NS, WHOIS, TXT, registrar, certificates) must be filtered by `source_data`; when you add the filter to one type, audit all the others in the same pass.

### automation-reuses-the-manual-path-and-keeps-the-same-gates
_derived_from: reflection/watch-automation.md · evidence_count: 1 · last_validated: 2026-10-04_

An automatic trigger must go through the same request and the same authorization checks as the manual one (here the allowlist), require an explicit opt-in per target, default to off, and be capped, so automating cannot widen what is scanned.

### a-control-that-sets-scope-needs-validation-authentication-and-an-audit-trail
_derived_from: reflection/control-panel.md · evidence_count: 1 · last_validated: 2026-10-04_

When an interface can change what a tool is allowed to touch, validate every name it accepts (a bare top-level name or a public suffix would authorise strangers), keep it local with a secret, a session, CSRF and Host checks, require an explicit ownership confirmation, and write every change to an audit log.

### filter-an-external-report-against-the-existing-product
_derived_from: reflection/provenance-coverage.md · evidence_count: 1 · last_validated: 2026-10-05_

Before acting on a strategy report, list what the product already covers, what is out of its authorised scope (person-level tools, other disciplines) and what is left; build only the remainder, and treat its unverified figures as orientation.
