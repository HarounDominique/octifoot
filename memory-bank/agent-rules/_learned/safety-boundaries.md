---
topic: safety-boundaries
priority: low
---

### enforce-authorization-in-layers-and-test-the-refusal
_derived_from: reflection/spiderfoot-connector.md, reflection/iterative-scan-loop.md · evidence_count: 2 · last_validated: 2026-10-04_

For anything that touches third-party targets, enforce the allowlist at config load, at deploy (required env), and at runtime before the network call, and prove the refusal path live in E2E, including that no downstream request was made.

### never-attribute-shared-infrastructure-to-the-target
_derived_from: reflection/risk-signal-mapping.md · evidence_count: 1 · last_validated: 2026-10-04_

Data about shared hosting, CDN ranges or co-hosted sites goes in a summary note, never as objects or relationships tied to the investigated target.

### autonomous-expansion-opt-in-bounded-and-gated
_derived_from: reflection/iterative-scan-loop.md · evidence_count: 1 · last_validated: 2026-10-04_

Any feature that acts on its own discoveries must be off by default, bounded by depth and total count, restricted to discovery types that cannot leave the authorized scope, and must re-run the authorization check before every individual action.

### print-env-files-with-an-allowlist
_derived_from: reflection/live-expansion-check.md · evidence_count: 1 · last_validated: 2026-10-04_

When showing an `.env` or config file, print only an explicit allowlist of known non-secret keys; a deny-pattern on key names (`KEY|TOKEN|PASSWORD`) misses names like `*_PASS`.
