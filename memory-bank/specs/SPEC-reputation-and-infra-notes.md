# SPEC: reputation-and-infra-notes

Status: approved
Extends: [SPEC-risk-signal-mapping.md](SPEC-risk-signal-mapping.md) (labels, Note lines), [SPEC-spiderfoot-connector.md](SPEC-spiderfoot-connector.md)

## Objective

Import the two kinds of signal that real passive scans produce, that the mapper still throws
away, and that are useful CTI context, without adding any object type OpenCTI would have to model
differently:

1. **Hostnames flagged malicious.** `MALICIOUS_INTERNET_NAME` ("Comodo Secure DNS [host]") is the
   same signal as `MALICIOUS_IPADDR` but for a hostname. A flagged hostname that is part of the
   import gets the `spiderfoot:malicious` label and a feed reference, exactly like a flagged IP.
2. **Infrastructure providers.** `DOMAIN_REGISTRAR`, `PROVIDER_HOSTING`, `PROVIDER_DNS` and
   `PROVIDER_MAIL` become one line in the scan Note. They describe who runs the target's registration,
   hosting, name servers and mail; they are not objects and never relationships.

Evidence (events exported from real scans `635DE72C`, bugoverflow.com, and `A0852CDD`,
registrolineas.com, 2026-10-04):
- `MALICIOUS_INTERNET_NAME`: 1 event (Comodo, `redirecciones.dinaserver.com`), currently counted as unmapped.
- Registrar `Dinahosting s.l.`; hosting `dinahosting` / `Cloudflare Inc`; DNS `ns.dinahosting.com`,
  `*.ns.cloudflare.com`; mail `mail.dinaserver.com`. All were unmapped.
- `BLACKLISTED_*` is **not** a duplicate of `MALICIOUS_*`: `sfp_cloudflaredns` emits
  `BLACKLISTED_COHOST` (its "Family" content filter) with no `MALICIOUS_COHOST`. Treating it as
  malicious would label benign hosts, so it stays unmapped.

Success:
- A flagged hostname that is imported, or is the target itself, carries the label and one feed reference per flagging feed.
- A flagged hostname that is not imported is counted in the Note, never imported just to carry a label.
- The Note has one `Infrastructure` line with sorted, de-duplicated, capped values per kind; none of these events appear under "Unmapped".
- `BLACKLISTED_*`, `PUBLIC_CODE_REPO`, `AFFILIATE_*` flags and every other type stay unmapped and counted.
- Imported object ids for existing event types are unchanged (no regression in earlier mappings).

Out of scope, with the reason found while investigating:
- Ports, banners, technologies: the passive scans produced **no** `TCP_PORT_OPEN`/`WEBSERVER_*`
  events at all (those come from active or API-key modules), so there is nothing to map.
- AS names: not present in the events (already recorded in SPEC-asn-enrichment).
- `Indicator` objects with CDN-aware filtering: needs a false-positive policy for shared
  infrastructure; needs its own spec and data.
- `PUBLIC_CODE_REPO`: name matches on GitHub repos by unrelated people; would attribute others' work to the target.
- Non-CTI entities (persons, profiles, events) and an OpenCTI-triggered bidirectional loop: need their own specs; the loop also first needs the multi-scan expansion verified live.

## Assumptions (approved by the user's standing instruction to proceed)

1. Hostname values are normalised and validated with the existing domain rules; invalid ones are counted as invalid.
2. The label and reference reuse `MALICIOUS_LABEL` and the existing reference wording ("Flagged malicious by <feed> (SpiderFoot module <m>)").
3. The target is labelled in place (same STIX id, no score change) when it is itself flagged.
4. Infrastructure values: hosting `name: url` keeps only `name`; DNS/mail hostnames are lower-cased without trailing dot; at most 5 per kind then "and N more".
5. These providers are facts about the target's own records (NS, MX, WHOIS, hosting of its IPs), reported as text, so the shared-infrastructure rule (never create ownership objects) is respected.

## Commands

```bash
cd connector && . .venv/bin/activate
pytest && ruff check . && ruff format --check .
```

## Test strategy

- Unit, TDD, with synthetic events on `example.com`/`example.net`: label on imported flagged hostname,
  label on the target, two feeds → two references, not-imported counted, invalid counted, determinism,
  infrastructure line (dedupe, cap, sort, parsing of the hosting `name: url` form), unmapped list no longer
  contains the four infrastructure types, `BLACKLISTED_*` still unmapped, ids of existing objects unchanged.
- Live: rebuild the connector, enrich bugoverflow.com, read the Note and the labels back from OpenCTI.

## Boundaries

**Always**: keep every scan-derived value out of ownership claims about the target; count what is not imported.
**Ask first**: new STIX object types; mapping `BLACKLISTED_*` or `PUBLIC_CODE_REPO`.
**Never**: import a hostname only to label it; label a host from a family/content filter as malicious.
