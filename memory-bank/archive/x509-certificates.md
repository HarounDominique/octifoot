# Archive: x509-certificates

Closed 2026-10-04 · Spec: [SPEC-x509-certificates.md](../specs/SPEC-x509-certificates.md) · Reflection: [reflection/x509-certificates.md](../reflection/x509-certificates.md) · Builds on: [archive/whois-dns-notes.md](whois-dns-notes.md)

## What was built

`SSL_CERTIFICATE_RAW` (certificates from crt.sh) becomes a STIX `x509-certificate` (serial number, issuer, subject, validity, signature algorithm) `related-to` the scanned domain, only when the subject CN is the
target, a wildcard of it, a name under it, or its parent. Other certificates are counted as "not the target's"; names inside certificates never become domain objects; at most 10 (most recent first) are imported and the
Note line states imported / over the cap / not the target's. The catalogue is regenerated (no planned slice remains).

- 247 tests, `ruff` clean
- Real data: the one recorded certificate maps correctly; verified live by replaying the recorded scan through the connector path: certificate, reference and relationship read back from OpenCTI

## Deviations accepted

Live check was a replay because crt.sh was down; a parser bug (`Not After :` spacing) found and fixed during the build.

## Not done / next

- A fresh scan once crt.sh answers, to see several certificates and the cap on real data.
- SAN names are unavailable (SpiderFoot truncates the text at 1024 characters).
