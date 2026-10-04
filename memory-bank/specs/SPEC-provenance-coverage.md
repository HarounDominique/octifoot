# SPEC: provenance-coverage

Status: approved
Extends: [SPEC-spiderfoot-connector.md](SPEC-spiderfoot-connector.md) (the per-scan Note), [SPEC-partial-scan-visibility.md](SPEC-partial-scan-visibility.md)

## Objective

Make each imported scan reproducible and say what it could not see. Origin: an OSINT state-of-the-art report (2019-2026, pasted by the owner on 2026-10-04) stresses provenance, evidence integrity, coverage ("absence of evidence is not evidence of absence") and data governance. octifoot already records scan id and module per object; two gaps remain: the raw data stays only in SpiderFoot, and the Note does not say which tools and settings produced the result nor how much of the source space answered.

Success:
- **Provenance line** in every scan Note: octifoot version, SpiderFoot version (from `/ping`, `unknown` if unreadable, never fatal), profile and use case, number of modules requested with a short digest of the sorted list (lean profile; `SpiderFoot's passive group` for full), the time applied to the scan, and the event count with a SHA-256 digest of the exported events (order-independent). The digest lets an analyst show later that an import matches what SpiderFoot returned.
- **Coverage line**: how many modules produced events, how many reported errors, how many API-keyed modules were active (names only, never values), and the reminder that a source that answers "no information" cannot be told from silence.
- Both lines appear in every scan's Note, including sub-scans (each sub-scan has its own scan id and events).
- **Data handling documentation** (README): which personal data can reach OpenCTI (email addresses from `EMAILADDR`), what is never copied (WHOIS registrant, contact, phone, email text), that "public" does not remove legal duties (GDPR: purpose, minimisation, retention, rights), how to remove data, and that scanning is limited to authorised domains.

Out of scope: storing the raw events in OpenCTI or elsewhere (SpiderFoot keeps them); signing evidence; username/person search tools (outside the authorised-domain boundary); a second discovery source (to be measured separately).

## Assumptions (approved by the user's standing instruction to proceed)

1. SHA-256 over the canonical JSON of the events (sorted keys, events sorted) is enough as an integrity reference; it proves identity of content, not authenticity of the source.
2. A module counts as "produced data" when an event carries its `sfp_*` name; internal sources (the root event) are ignored.
3. `/ping` is the cheapest stable way to read SpiderFoot's version (`["SUCCESS", "4.0.0"]` on the pinned image).

## Commands

```bash
cd connector && . .venv/bin/activate
pytest && ruff check . && ruff format --check .
```

## Test strategy

Unit: digest stability (order-independent, changes with content), both lines (lean/full, unknown version, keyed modules, errors, empty events), client version read, connector passing the values and applying the applied time of each scan, Note contains the lines. Live: analyse a domain and read the Note.

## Boundaries

**Always**: names only for keys, never values; a failing version read never fails the enrichment.
**Ask first**: storing raw event data in OpenCTI; adding person-level tools.
**Never**: claim authenticity from a digest; copy registrant or contact data.
