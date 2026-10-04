---
slug: x509-certificates
spec: SPEC-x509-certificates.md
status: approved
---

## Implementation Roadmap

Routing: standard.

- [x] Phase 1 — Mapper: parse certificate text, `x509-certificate` objects and relationship, cap, Note line, `IMPORTED_EVENTS`, catalogue regenerated, tests (satisfies: SPEC-x509-certificates.md#objective, SPEC-x509-certificates.md#boundaries)
- [x] Phase 2 — Docs + live check: README, recorded real event through the connector path, read the certificate back from OpenCTI (satisfies: SPEC-x509-certificates.md#test-strategy)

## Execution State

**Build Status**: COMPLETE
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {1: 1, 2: 1}
**Last Block Rule**: none
**Can Resume**: NO

## Deviations

- Bug found by the tests and fixed before any commit of the feature: `openssl` prints `Not After : ...` with a space before the colon; the first parser compared the raw key and lost
  the expiry date. The test fixture had copied the real text shape, which is why it failed. Also a missing `UTC` import and lint (naive `strptime`) fixed.
- The live check used a replay of the recorded real scan, not a fresh scan, because crt.sh was still down (HTTP 502) and a new scan would have produced no certificates. Accepted, stated here.
- A first attempt to print the replay's result lost its output (`os._exit` does not flush a piped stdout); the replay itself was unaffected and the result was read back from OpenCTI.

**Real data:** the one recorded certificate (scan DF50665A, registrolineas.com) maps to serial `17:db:50:1d:...:f3:8f`, issuer `C=US, O=Google Trust Services, CN=WE1`, subject `CN=registrolineas.com`,
valid 2026-09-27 to 2026-12-26; previous object ids are a subset of the new ones (adds the certificate, its relationship and the Note).

**Live check (2026-10-04, connector rebuilt from this branch):** replay of the recorded scan through `process_message` with the real helper, queue and worker. Read back from OpenCTI:
one `X509-Certificate` with those fields, external reference `SpiderFoot DF50665A`, relationship `related-to registrolineas.com`, and the Note line
`TLS certificates: 1 imported, 0 over the cap of 10, 0 not issued for the target`.
Not seen live: more than one certificate, the 10-certificate cap, a certificate for another name (unit-tested only); a fresh scan with working crt.sh.
