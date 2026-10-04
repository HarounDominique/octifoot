# SPEC: spiderfoot-ui-link

Status: approved
Extends: [SPEC-spiderfoot-connector.md](SPEC-spiderfoot-connector.md) (provenance), [SPEC-event-catalogue.md](SPEC-event-catalogue.md) (what is not imported)

## Objective

Make the two tools one environment: from any object or Note in OpenCTI, one click opens the full SpiderFoot scan that produced it. octifoot imports only the part of a scan that is safe and useful (18 of 172 event types); everything else
(raw events, third-party hosts, co-hosted sites, WHOIS text) stays in SpiderFoot's own database and UI, which already runs in the stack. Without a link, "unmapped" data looks lost; with it, the curated layer in OpenCTI and the complete record in SpiderFoot are connected.

Evidence: `GET /scaninfo?id=<scan>` on the running SpiderFoot returns the scan's page (HTTP 200, the scan id appears 16 times in it). The stack publishes it on `127.0.0.1:5001`.

Success:
- New optional setting `SPIDERFOOT_UI_URL` (the address your browser uses, for example `http://localhost:5001`): http or https only, trailing slash removed; empty or unset means no links (unchanged behaviour); anything else is a `ConfigError`.
- When set, every external reference octifoot creates for a scan carries `url = <UI URL>/scaninfo?id=<scan id>`, and the first line of each scan Note ends with `Full results in SpiderFoot: <that URL>`.
- Compose passes the setting with the default `http://localhost:5001`; `.env.example` documents it.
- Nothing else changes: ids, objects, other lines.

Out of scope: deep links to individual event types or modules; proxying or embedding the SpiderFoot UI; authentication of the UI (it has none and is bound to localhost).

## Assumptions (approved by the user's standing instruction to proceed)

1. The browser-facing address differs from the internal `SPIDERFOOT_URL` (`http://spiderfoot:5001` is not resolvable from a browser), hence a separate setting.
2. A reference URL does not change the STIX id of the reference-bearing objects (external references are not id-contributing here).
3. The link is useful only while the SpiderFoot container keeps the scan; deleting scans there makes the page empty.

## Test strategy

Unit: config default, valid, trailing slash, invalid scheme; mapper references with and without the URL, Note first line; connector passes the setting; first line still starts with `SpiderFoot scan <id> for <target>` (existing consumers).
Live: rebuild, enrich, read an object's reference and the Note back, open the URL.

## Boundaries

**Always**: leave links off unless configured.
**Never**: send the UI URL to a third party; expose the SpiderFoot UI beyond localhost without authentication.
