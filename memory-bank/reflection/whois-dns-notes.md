# Reflection: whois-dns-notes

Date: 2026-10-04 · Spec: SPEC-whois-dns-notes.md (approved) · Plan: 2 phases DONE · Live check: fresh scan read back from OpenCTI, plus old-vs-new on recorded real events

## Implementation vs spec

| Spec requirement | Result |
|---|---|
| `WHOIS` line: dates, age in days, EPP status, DNSSEC, only what parsed | Met; live: domain created 7 days before the scan |
| `DNS TXT` line: SPF, DMARC policy, verification services, other count | Met for verification tokens live; SPF and DMARC on synthetic data only |
| Only the target's or a parent's WHOIS/TXT; others counted | Met; real case: `dinaserver.com` excluded and counted for bugoverflow.com |
| No registrant/contact data, no token values | Met (tests and live leak check) |
| Invalid WHOIS counted, no objects added, ids unchanged | Met |

Deviations: `WEB_ANALYTICS_ID` declined (the spec said so up front, correcting the catalogue); a connection-retry fix added; one test arithmetic error corrected.

## What the data showed

- `registrolineas.com` was registered 7 days before the scan. That is the first piece of real CTI context octifoot has added that `dig` and `whois` do not hand an analyst
  already summarised inside the platform: age, expiry and status are now one line in the Note, next to the infrastructure and reputation lines.
- SpiderFoot truncates WHOIS text at 1024 characters, so the parser had to be tolerant of partial text from the start.
- None of the three test domains had SPF or DMARC in the events SpiderFoot returned, so two of the four TXT classes remain proven on synthetic data.

## Workflow evaluation

- The live check found a defect no unit test could: a single dropped keep-alive connection during polling aborted a 3-minute scan. Earlier runs had passed by luck. The fix is small
  but the class of failure (polling a long job over a connection the server drops) is general.
- Restricting WHOIS and TXT to the target's own or parent domains came from reading real events: a provider's domain appeared in the same scan and would have been mixed in.
- Computing expected values by hand in a test produced an off-by-one; checking with `datetime` before touching the code avoided "fixing" correct code.

## Rules extracted

- New `retry-only-idempotent-requests-when-polling-a-long-job` (external-integrations).
- Reinforced: `round-trip-new-fields-through-the-real-target` (evidence 3): the live round trip exposed the retry defect.

## Follow-ups (not blocking)

- SPF/DMARC should be re-checked live on a domain that publishes them.
- `x509-certificates` is the remaining planned slice.
