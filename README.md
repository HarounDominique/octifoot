# octifoot

**OpenCTI + SpiderFoot.** An [OpenCTI](https://github.com/OpenCTI-Platform/opencti) internal-enrichment
connector. From a `Domain-Name` observable it runs a **passive** [SpiderFoot](https://github.com/smicallef/spiderfoot)
scan and imports what it finds into OpenCTI as STIX 2.1 objects with provenance.

> *The name:* **octi** reads as *octopus* (eight arms) and is also short for **OpenCTI**; **foot** is the
> tail of **SpiderFoot**, and spiders have eight legs too.

What it imports: subdomains, IPs (v4/v6) and their autonomous systems, email addresses, and a Note
summarising the scan, including risk signals (blacklist and malicious-host hits). Third-party data that
SpiderFoot finds about *other* sites (co-hosted domains, affiliates) is deliberately not attributed to your target.

```
OpenCTI analyst ──enrich──▶ octifoot ──HTTP API──▶ SpiderFoot (passive modules) ──▶ internet sources
        ▲                       │
        └──── STIX 2.1 bundle ──┘
```

## Is it worth it?

See [docs/value-assessment.md](docs/value-assessment.md): an honest, evidence-based comparison with using SpiderFoot and OpenCTI separately, including where octifoot is weaker and how each claim was verified.

## Authorized use only

Run it only against domains **you own or have written permission to investigate**. "Passive" is
SpiderFoot's own grouping: no intrusive probing, but modules still resolve DNS for the target and query
third-party services with it, so the target and your IP are visible to those services.

- `SPIDERFOOT_ALLOWED_DOMAINS` is mandatory; without it the connector and Compose refuse to start.
- Targets outside the allowlist are refused **before** any SpiderFoot call.
- Scans only run when an analyst triggers them (`CONNECTOR_AUTO=false`).
- Non-passive use cases need `SPIDERFOOT_USECASE=...` **and** `SPIDERFOOT_ALLOW_ACTIVE=true`.

You are responsible for complying with the law and with the terms of every service SpiderFoot queries.

## Quick start

```bash
cp deploy/.env.example deploy/.env      # replace every CHANGE_ME, set the allowlist
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d --build
```

OpenCTI: <http://localhost:8080>. Open a `Domain-Name` observable → enrichment → **SpiderFoot**.
Needs about 8 GB of RAM for Docker. Full configuration, the event-to-STIX mapping, the speed profiles
(`lean` is the default for passive scans) and the verification notes are in [docs/README.md](docs/README.md).

Development:

```bash
cd connector && python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
pytest && ruff check . && ruff format --check .
```

## License

octifoot is licensed under the **Apache License 2.0** — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
Copyright 2026 Dominique Haroun.

## Attribution and third-party licenses

octifoot is independent and **not affiliated with or endorsed by** Filigran (OpenCTI), the SpiderFoot
authors or OASIS. Names are used only to identify the software it works with.

| Component | Role | License |
|---|---|---|
| [SpiderFoot](https://github.com/smicallef/spiderfoot) © Steve Micallef, pinned at `v4.0` | scanner, separate container, unmodified source built at deploy time | **GPL-2.0** at `v4.0` (upstream `master` is MIT) |
| [OpenCTI](https://github.com/OpenCTI-Platform/opencti) © Filigran SAS, `7.261002.0` | platform | Apache-2.0 (Community Edition) |
| [pycti](https://github.com/OpenCTI-Platform/opencti) `7.261002.0` | client library | Apache-2.0 |
| Redis, Elasticsearch, object storage (MinIO fork), RabbitMQ | services pulled by Compose | differ, some AGPL/SSPL/source-available — see below |

Points that matter if you reuse or redistribute this:

- **SpiderFoot v4.0 is GPL-2.0.** octifoot talks to it over HTTP and imports none of its code; this
  repository does not redistribute it. If *you* publish a SpiderFoot image, you take on GPL-2.0 obligations
  (including offering source). Two data files here, `connector/src/spiderfoot_connector/data/sf_modules_v4.0.json` and `sf_event_types_v4.0.json`,
  are snapshots of module and event-type metadata read from SpiderFoot v4.0; `lean_modules.json`, `event_catalogue.json` and `docs/event-catalogue.md` are generated from them.
- **OpenCTI Enterprise Edition** has a separate license. Do not enable it without one.
- The Compose stack pulls images with **different licenses** (Redis 8: RSALv2/SSPLv1/AGPLv3 choice;
  Elasticsearch: AGPL-3.0/SSPL/ELv2; the object store: AGPL-3.0; RabbitMQ: MPL-2.0). Read them before
  deploying beyond a local test.

The complete list, with Python dependencies and how each license was checked, is in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). This is a good-faith summary, not legal advice.

## How to cite

If you use octifoot in research or a report, cite it with [CITATION.cff](CITATION.cff) (GitHub's
"Cite this repository" button reads it), or:

```bibtex
@software{haroun_octifoot_2026,
  author  = {Haroun, Dominique},
  title   = {octifoot: an OpenCTI internal-enrichment connector backed by SpiderFoot},
  year    = {2026},
  version = {0.1.0},
  url     = {https://github.com/HarounDominique/octifoot},
  license = {Apache-2.0}
}
```

Please also cite the works it builds on:

- Micallef, S. *SpiderFoot* (v4.0). <https://github.com/smicallef/spiderfoot>
- Filigran SAS. *OpenCTI* (7.261002.0). <https://github.com/OpenCTI-Platform/opencti>
- Jordan, B., Piazza, R., Darley, T. (eds.). *STIX Version 2.1*. OASIS Standard, 10 June 2021.
  <https://docs.oasis-open.org/cti/stix/v2.1/os/stix-v2.1-os.html>

## About this repository

`memory-bank/` holds the specifications, task plans, reflections and archived decisions the connector was
built from (a spec-driven workflow). They explain *why* it works the way it does, including the measured
A/B results behind the default profile and the places where a decision overrode a spec's acceptance rule.
