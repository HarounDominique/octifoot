# SPEC: source-health-note

Status: approved
Extends: [SPEC-spiderfoot-connector.md](SPEC-spiderfoot-connector.md) (scan Note), [SPEC-live-expansion-check.md](SPEC-live-expansion-check.md) (finding that motivated it)

## Objective

Make a scan whose sources failed distinguishable, in OpenCTI, from a scan of a target that simply has nothing.
Today both finish "successfully" with the same Note.

Evidence (SpiderFoot log of scan `0115B5B0`, zonetransfer.me, 2026-10-04): 61 `ERROR` rows from 13 components:
HTTP 401 (ThreatFox), 403 (CoinBlocker, Talos), 404 (Koodous, searchcode), "Bad response code None" (Sublist3r), CommonCrawl
index unavailable, Crobat failure, a parse error (psbdmp), and 47 "Failed to connect" rows logged by `sflib` (e.g. phishstats.info).
`crt.sh`, our main subdomain source, answered HTTP 502 for 6+ minutes but `sfp_crt` logged only a `STATUS` row
("No certificate transparency info found"): upstream `sfp_crt` does not look at the HTTP code, so that outage is
indistinguishable from a domain without certificates inside SpiderFoot's own log.

Success:
- The connector reads the scan's `ERROR` log rows and the scan Note gets one line naming the modules that reported errors
  (module, count, first message), most errors first then by name, capped at 8 modules then "and N more", messages cut at 80 characters, HTML entities decoded.
- The line states its own limit: an outage that a module reports as "no information" is not detectable here.
- No error rows, no line. The line never changes which objects are imported.
- A failure to read the log never fails the enrichment (it is a diagnostic, not data).
- With expansion, each scan reads the log of its own scan id.

Out of scope: probing third-party sources from the connector (extra outbound requests, a new dependency on them);
retrying or replacing failing modules; deciding which failures matter; reading `WARNING` rows.

## Assumptions (approved by the user's standing instruction to proceed)

1. SpiderFoot's `/scanlog?id=<scan>&limit=<n>` returns rows `[time, component, type, message, rowid]`; verified live on v4.0.
2. Only `type == "ERROR"` rows count; module-config noise (e.g. `sfp_customfeed` without a URL, `sfp_flickr` without a key) is reported like any other
   error because filtering it would hide real regressions; the count and cap keep it readable.
3. `limit` is large (100000); a scan produces about 2,700 rows.
4. Messages are decoded with `html.unescape`; SpiderFoot HTML-escapes them (`&quot;`).
5. The extra request happens after the scan has finished, so it adds no scan time.

## Commands

```bash
cd connector && . .venv/bin/activate
pytest && ruff check . && ruff format --check .
```

## Test strategy

- Unit, pure: Note line (absent, sorted, counted, capped, truncated, objects unchanged).
- Client (`responses`): only ERROR rows, decoded, ids/limit passed, bad response raises `SpiderFootError`.
- Connector: errors from each scan reach its Note; a failing log read does not fail the work.
- Live: rebuild, enrich a real domain, read the Note back from OpenCTI.

## Boundaries

**Always**: keep the diagnostic out of the object set; state what the line cannot detect.
**Ask first**: probing sources directly; failing or retrying a scan because of source errors.
**Never**: claim all sources were healthy because the line is absent.
