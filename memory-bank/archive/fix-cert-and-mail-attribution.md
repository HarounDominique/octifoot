# Archive: fix-cert-and-mail-attribution

Closed 2026-10-04 · Spec: [SPEC-fix-cert-and-mail-attribution.md](../specs/SPEC-fix-cert-and-mail-attribution.md) · Reflection: [reflection/fix-cert-and-mail-attribution.md](../reflection/fix-cert-and-mail-attribution.md) · Corrects: [archive/x509-certificates.md](x509-certificates.md), [archive/key-findings.md](key-findings.md)

## What was built

- Certificates are the target's when SpiderFoot's event names the scanned name as the one crt.sh was queried for (or the CN covers it). Real data: 53 certificates (34 distinct serials) for zonetransfer.me had been rejected by the CN-only rule; now 10 are imported (cap), related to the domain, with the rest counted.
- The certificate expiry finding judges only the newest certificate per CN.
- The event-based mail fallback uses only records of the scanned name itself, so expansion sub-scans no longer repeat the root's finding.
- 312 tests, `ruff` clean; README and the x509 spec's boundary amended; verified live by replaying the recorded real scan through the connector and reading 10 `X509-Certificate` objects back from OpenCTI

## Deviations accepted

Spec arithmetic (43 over the cap) corrected to 24; a half-applied scripted edit re-done step by step.

## Not done / next

- The certificate expiry finding has never fired on real data.
- SANs are unavailable (SpiderFoot truncates the text at 1024 characters).
