---
topic: deployment
priority: low
---

### build-every-image-in-its-phase
_derived_from: reflection/spiderfoot-connector.md · evidence_count: 1 · last_validated: 2026-10-04_

A phase that adds a Dockerfile or Compose service is not done until each image has actually built; `docker compose config` only validates syntax. If the daemon is down, start it or stop and say so rather than checking the phase off.

### do-not-trust-old-upstream-dockerfiles
_derived_from: reflection/spiderfoot-connector.md · evidence_count: 1 · last_validated: 2026-10-04_

Pinning an old upstream git tag does not make its build reproducible today; verify it builds, and if not, keep an own Dockerfile in the repo that uses the same unmodified source and document the delta.

### e2e-scripts-select-by-id
_derived_from: reflection/spiderfoot-connector.md · evidence_count: 1 · last_validated: 2026-10-04_

Verification and polling scripts must select the job they just created by its id, never "the latest"; a stale match reports a false result.
