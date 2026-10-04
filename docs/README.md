# SpiderFoot ↔ OpenCTI enrichment connector (prototype)

An OpenCTI `INTERNAL_ENRICHMENT` connector. From a `Domain-Name` observable it runs a
**passive** SpiderFoot scan and imports the results into OpenCTI as STIX 2.1 objects with
provenance. Spec: `memory-bank/specs/SPEC-spiderfoot-connector.md`.

## Authorized use only

Run it only against domains you own or have written permission to investigate.

- `SPIDERFOOT_ALLOWED_DOMAINS` is mandatory. The connector will not start without it, and
  Compose will not start the service with it empty.
- A target must equal an allowlisted domain or be a subdomain of one. Anything else is
  refused **before** any SpiderFoot call and the work shows as failed in OpenCTI.
- `CONNECTOR_AUTO=false`: scans only run when an analyst triggers the enrichment.
- Default scope is SpiderFoot's `Passive` use case. Other use cases need an explicit
  `SPIDERFOOT_USECASE=...` **and** `SPIDERFOOT_ALLOW_ACTIVE=true`.

"Passive" is SpiderFoot's own module grouping. It means no intrusive probing modules, but
some modules still resolve DNS for the target and query third-party services with it.

## Quick start

```bash
cp deploy/.env.example deploy/.env      # replace every CHANGE_ME, set the allowlist
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d --build
```

OpenCTI: <http://localhost:8080> (admin from `.env`). SpiderFoot UI: <http://localhost:5001>
(no authentication, bound to localhost only). Needs roughly 8 GB of RAM for Docker; set
`ELASTIC_MEMORY_SIZE=2G` if you have less. SpiderFoot is built by `deploy/spiderfoot/Dockerfile`
from the unmodified upstream `v4.0` tag, because upstream's own Dockerfile no longer builds
(its `pyyaml<6` pin fails to compile on Alpine 3.12).

In OpenCTI open a `Domain-Name` observable, then enrichment → **SpiderFoot**.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `SPIDERFOOT_URL` | required | SpiderFoot base URL |
| `SPIDERFOOT_ALLOWED_DOMAINS` | required | Authorized domains, comma-separated |
| `SPIDERFOOT_USECASE` | `passive` | `passive`, `footprint`, `investigate`, `all` |
| `SPIDERFOOT_ALLOW_ACTIVE` | `false` | Required for any use case other than `passive` |
| `SPIDERFOOT_TIMEOUT_SECONDS` | `900` | On timeout the scan is stopped and partial results are imported |
| `SPIDERFOOT_POLL_SECONDS` | `10` | Status polling interval |
| `SPIDERFOOT_SCORE` | `30` | `x_opencti_score` for imported observables |
| `SPIDERFOOT_MAX_DEPTH` | `0` | Iterative expansion depth, 0-3. `0` = off |
| `SPIDERFOOT_MAX_SCANS` | `5` | Max scans per request, 1-20, root included |

## Iterative investigation (opt-in)

With `SPIDERFOOT_MAX_DEPTH` ≥ 1, one enrichment request follows its own discoveries: after
scanning a domain, the connector scans the **subdomains it found** (`INTERNET_NAME` events),
breadth-first, each at most once, and imports everything in one bundle.

Safety properties:
- Off by default; a request is a single scan unless you opt in.
- Every scan, expansions included, passes the same `SPIDERFOOT_ALLOWED_DOMAINS` check, so a
  discovery can never widen the authorized scope. Third-party or look-alike hosts are
  reported, never scanned.
- Bounded by depth (max 3) and by total scans (max 20, root included). The rest is reported
  as over budget.
- A failing sub-scan is logged and listed; results already collected are kept. A failing
  root scan still fails the work.
- Only `INTERNET_NAME` expands. IPs, emails, affiliates and co-hosts never do.

An "expansion" Note on the target lists scans run, depth reached, failed sub-scans, and what
was skipped and why. Scans run one after another, so total time can approach
`SPIDERFOOT_MAX_SCANS × SPIDERFOOT_TIMEOUT_SECONDS`.

## What is imported

| SpiderFoot event | STIX object | Relationship |
|---|---|---|
| `INTERNET_NAME` | `domain-name` | `related-to` → scanned domain |
| `AFFILIATE_INTERNET_NAME` | `domain-name` (score halved) | `related-to` → scanned domain |
| `IP_ADDRESS`, `IPV6_ADDRESS` | `ipv4-addr` / `ipv6-addr` | `resolves-to` from the host that produced it, else the scanned domain |
| `EMAILADDR` | `email-addr` | `related-to` → scanned domain |
| `NETBLOCK_MEMBER` + `BGP_AS_MEMBER` (also IPv6) | `autonomous-system` (number only) | `belongs-to` from each imported IP to its AS |

Every imported object carries `created_by` = Identity "SpiderFoot", a low score, and an
external reference naming the scan id and SpiderFoot module. One Note per scan summarizes
what was mapped, what was skipped and how many events were false positives.

### Autonomous systems

SpiderFoot reports each IP's netblock and each netblock's ASN. The connector chains them
(IP → netblock → AS) and links every **imported** IP to an `autonomous-system` with
`belongs-to`. It is a fact about the IP's network, not ownership by the target: for a site
behind a CDN, every IP will point at the CDN's AS, which is how you spot shared hosting.
AS objects are created only when linked to an imported IP. AS names, netblock/CIDR objects and
any AS-to-domain link are not created. The scan Note lists the ASNs and how many IPs each covers.

### Infrastructure providers

`DOMAIN_REGISTRAR`, `PROVIDER_HOSTING`, `PROVIDER_DNS` and `PROVIDER_MAIL` appear as one line in the scan
Note, for example `Infrastructure (as reported by SpiderFoot): registrar: ...; hosting: ...; DNS: a, b; mail: c`.
Values are sorted and de-duplicated, five per kind at most. They are text, not objects or relationships:
they say who runs the target's registration, hosting, name servers and mail, and nothing more.

### Reputation signals

| SpiderFoot event | Handling |
|---|---|
| `MALICIOUS_IPADDR` | No new object. An imported IP flagged by a feed gets label `spiderfoot:malicious` and one external reference per feed (e.g. "Maltiverse"). Flags on IPs not in the import are only counted. |
| `MALICIOUS_INTERNET_NAME` | Same as IPs, for hostnames: an imported hostname, or the scanned domain itself, flagged by a feed gets the label and one reference per feed. A flagged hostname that is not imported is only counted in the Note ("Malicious flags on hostnames not in this import"); it is never imported just to carry a label. |
| `MALICIOUS_SUBNET`, `MALICIOUS_COHOST` | Listed in the scan Note (feed, value; max 20 lines, then "and N more"). Never objects. |

Why not objects: in a real scan of a domain behind Cloudflare, the "malicious subnet" was
Cloudflare's whole /20 and the "malicious co-hosts" were unrelated sites sharing the CDN IP.
Linking them to the target would present other companies' data as the target's. No STIX
`Indicator` is created either: a feed flagging a shared CDN IP would yield false positives.
Treat the label as a lead to verify, not a verdict.
`BLACKLISTED_*` events are **not** treated as the same thing as `MALICIOUS_*`: some modules emit them for
content filters (SpiderFoot's Cloudflare "Family" module flags benign adult-content or parked hosts), so
they stay unmapped and are counted in the Note.
Labels and references are additive: OpenCTI keeps them across scans, and reputation feeds are
not deterministic (the same domain was flagged in one scan and not in the next), so a later
scan without the flag does not remove an earlier one. Each feed reference carries the scan id,
so you can see which scan reported it.

### Deliberately not imported

`AFFILIATE_EMAILADDR` is unreliable: the emails come from the WHOIS of co-hosted sites, not
of the target. `AFFILIATE_IPADDR` / `AFFILIATE_IPV6_ADDRESS` are nameserver IPs. `PUBLIC_CODE_REPO`
matches repositories by name, so it would credit other people's work to the target. Open ports, banners
and technologies need active or API-key modules; the passive scans measured here produced none of those
events. Every other event type is also skipped. Skipped types are counted
in the Note and logs. False positives are dropped.
Re-running a scan does not duplicate observables (deterministic STIX ids).

## Development

```bash
cd connector && python3.13 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest && ruff check . && ruff format --check .
```

## Manual E2E checklist

Not automated in v1. Run manually on 2026-10-04 against the full stack (OpenCTI 7.261002.0,
SpiderFoot v4.0) with an owned domain: steps 1-5 passed. The scan took ~7 minutes (436
events), imported 2 IPs, 2 related domains and 1 Note; a second run created no duplicates.

1. `docker compose ... up -d --build` finishes; `connector-spiderfoot` registers in
   OpenCTI → Data → Ingestion → Connectors.
2. Create a `Domain-Name` for a domain **on your allowlist**; run SpiderFoot enrichment.
   Expect: work completes, related subdomains/IPs/emails appear, each with the SpiderFoot
   external reference, plus a summary Note.
3. Run it again. Expect: no duplicate observables.
4. Create a `Domain-Name` **not** on the allowlist; run enrichment. Expect: work fails with
   "is not in SPIDERFOOT_ALLOWED_DOMAINS" and no scan appears in the SpiderFoot UI.
5. Start with `SPIDERFOOT_ALLOWED_DOMAINS` empty. Expect: Compose refuses to start the
   connector.

## Limitations and next steps

- OpenCTI models cyber-threat entities. Persons, profiles and events need a different
  model; this prototype does not cover them.
- Iterative investigation (new scans seeded from discovered entities) is out of scope; see
  *Future* in the spec. It needs allowlist propagation, depth limits and scan dedupe.
- SpiderFoot upstream's last commit is from 2023; its HTTP API is not a stable contract.
  Versions are pinned (`v4.0`) for that reason.
- Possible next steps: ports/banners and technologies, `Indicator` objects with CDN-aware
  filtering, and the iterative investigation loop (see the spec's *Future* section).
- Only OpenCTI Community Edition features are used.
