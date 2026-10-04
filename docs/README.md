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

## What is imported

| SpiderFoot event | STIX object | Relationship |
|---|---|---|
| `INTERNET_NAME` | `domain-name` | `related-to` → scanned domain |
| `AFFILIATE_INTERNET_NAME` | `domain-name` (score halved) | `related-to` → scanned domain |
| `IP_ADDRESS` | `ipv4-addr` / `ipv6-addr` | `resolves-to` from the host that produced it, else the scanned domain |
| `EMAILADDR` | `email-addr` | `related-to` → scanned domain |

Every imported object carries `created_by` = Identity "SpiderFoot", a low score, and an
external reference naming the scan id and SpiderFoot module. One Note per scan summarizes
what was mapped, what was skipped and how many events were false positives.

Not imported in v1: all other event types (open ports, banners, technologies, …), IPv6
events (`IPV6_ADDRESS`), false positives. Skipped types are counted in the Note and logs.
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
- Next iteration: map `MALICIOUS_IPADDR`, `MALICIOUS_COHOST`, `MALICIOUS_SUBNET` (real CTI
  signals seen in the E2E scan), then `AFFILIATE_EMAILADDR` and `IPV6_ADDRESS`.
- Only OpenCTI Community Edition features are used.
