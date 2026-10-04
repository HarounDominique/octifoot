---
topic: safety-boundaries
priority: low
---

### enforce-authorization-in-layers-and-test-the-refusal
_derived_from: reflection/spiderfoot-connector.md · evidence_count: 1 · last_validated: 

For anything that touches third-party targets, enforce the allowlist at config load, at deploy (required env), and at runtime before the network call, and prove the refusal path live in E2E, including that no downstream request was made.
