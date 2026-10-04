# Is octifoot as valuable as SpiderFoot and OpenCTI used separately?

An honest assessment, written 2026-10-04 from what was measured while building and verifying the connector (the evidence is in `memory-bank/archive/`). It states what holds, what does not, and how each claim was verified.

**Short answer.** For assessing a domain passively: **yes, it is at least as valuable as running the two tools separately, and it adds things neither has.** Free API keys are supported but unproven with a real provider key, and active modules stay off unless you opt in;
for some of its newest features the proof is still a fixture or a recorded scan, not months of use.

## What the user gets, side by side

| Question an analyst asks | SpiderFoot alone | OpenCTI alone | Both, by hand | octifoot |
|---|---|---|---|---|
| Discover hosts, IPs, AS, emails, WHOIS, TXT and certificates of a domain (passive, keyless) | Yes, raw event lists | No discovery | Yes, after exporting and importing by hand | Yes, automatically, as attributed STIX objects with provenance |
| See *everything* the scan found | Yes (172 event types) | n/a | Yes | Yes: 18 types are imported; every scan links to the full SpiderFoot record (`SPIDERFOOT_UI_URL`) |
| Know which findings belong to the target and which to a provider, partner or co-hosted site | No: one flat list | n/a | Manual, error-prone | Yes: records are attributed by their source; third-party data is counted, not imported (see the limits below: this was wrong three times and fixed) |
| Persist and correlate with other intelligence | No memory between scans | Yes | Manual | Yes: deterministic STIX ids, relationships, labels |
| Say what is notable | No | No | Manual reading | `Key findings`: newly registered, expiring, flagged, mail without SPF/DMARC, expired certificate, incomplete scan, coverage gaps |
| Check DMARC, CAA, DNSSEC, MTA-STS | No | No | Manual `dig` | Yes, queried directly, with found / none / unknown kept apart |
| Say what OpenCTI already knows about what was just found | No | Only if you search each value | Manual | Yes: a Note listing indicators, reports and labels from other sources |
| Say what changed since the last scan | No | No | Manual diff | Yes, with caveats when scans were incomplete or sources failed |
| Say whether the scan itself was complete and its sources healthy | Logs only | n/a | Logs only | Yes, in the Note |
| Use API-keyed sources | Yes, if keys are configured | n/a | Yes | **Yes, optional, with your own free keys** (`docs/api-keys.md`): the 52 keyed modules that add data octifoot already imports. Plumbing verified against the real SpiderFoot; **never run with a real provider key**. The 28 event types only keyed modules produce for things octifoot does not import (ports, vulnerabilities...) stay unmapped but reachable through the SpiderFoot link |
| Run active modules (port scans, zone transfers) | Yes | n/a | Yes | **Only by explicit opt-in** (`SPIDERFOOT_ALLOW_ACTIVE`); never by default |
| Change which domains may be analysed, or the maximum time, without editing files | Not applicable | Not applicable | Not applicable | **Yes, opt-in**: a local control panel (token, ownership confirmation, validation, audit log); see `docs/README.md` |
| Re-scan on a schedule | No (open-source edition) | No | No | **Yes, opt-in**: label a domain `octifoot:watch` and set an interval; proven live with two automatic runs. **No alerting**: the comparison Note is the record |

## What was measured

- **Same objects, faster.** The default `lean` profile imports identical objects to the full passive scan and ran 64.8 % and 87.2 % faster on two real domains (all runs finished, none timed out). Typical lean scan: about 3 minutes; a domain with many certificates can exceed the 15-minute default timeout.
- **Coverage is a property of the sources, not the mapper.** Of SpiderFoot's 172 event types, 46 ever appeared across 21 real passive scans of 3 domains; octifoot imports 17 of those 46 and declines most of the rest on purpose (they describe third parties). The other 126 need API keys (28), active modules (6) or never occurred.
- **Tests and checks.** 383 unit and integration tests; every feature was also checked against the real stack (OpenCTI, worker, connector, SpiderFoot) and, where possible, against ground truth (`dig`, upstream source, a positive control).

## Where it is weaker, and the evidence

- **Silent third-party failures.** On the day of testing crt.sh returned HTTP 502 for hours, Sublist3r, CommonCrawl and Crobat failed, and `sfp_crt` cannot report its own outages. A scan can finish "successfully" with no subdomains. The Note names the modules that reported errors, flags incomplete scans, and caveats comparisons, but an undetectable crt.sh outage remains possible.
- **It was wrong three times about attribution, and found out late.** A provider's mail, DNS and registrar records were shown as the target's; certificates were rejected by a rule fitted to one sample; a parent zone's mail finding was repeated on sub-scans. Each was found by checking real data against an independent source (`dig`, a second scan), not by the tests, and fixed with the correction recorded in the project notes. The lesson (compare imported values with ground truth, not just that the pipeline finished) is now a standing rule.
- **Partial scans.** A 15-minute scan was cut at the 900 s limit and its Note read as complete until a defect fix made incompleteness the first finding.
- **Knowledge feedback is proven on a fixture.** The local OpenCTI holds no real intelligence, so the "what OpenCTI already knows" feature was verified with a labelled test indicator that was then removed. Its value on real overlaps is unproven until the platform is fed.
- **Change detection compares scans that disagree for reasons unrelated to the world** (a source answering one time and not the next). The caveats say so; a real second scan was shown to report 13 certificates and a hostname that were almost certainly not new.
- **Verified live vs unit-tested only.** Live: infrastructure, WHOIS, TXT, certificates, DNS checks, key findings, source health, partial-scan flag, knowledge, changes, UI link, multi-scan expansion. Unit-tested only: SPF and DMARC parsing on real domains with those records, `p=none`/`+all` findings, certificate and registration expiry findings, unknown DNS states.

## How to read this

If you assess domains you are authorised to investigate, passively, today: octifoot gives you SpiderFoot's findings with attribution, an analyst summary, DNS checks, a memory of the last scan and a link to the full record, inside OpenCTI where they correlate.
Treat the findings as leads to verify, not verdicts, and read the source-health and completeness lines first. If you want keyed sources, give octifoot your own free keys (it verifies each one by reading it back and never logs it); if you want active scanning, opt in explicitly on a domain you own, or use SpiderFoot directly for that part.
