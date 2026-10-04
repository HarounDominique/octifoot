# Third-party notices

octifoot's own code is Apache-2.0 (see [LICENSE](LICENSE) and [NOTICE](NOTICE)). It works with, and
depends on, the software below. Licenses were checked against each project's own repository or
package metadata on 2026-10-04; the license that applies to you is the one shipped with the exact
version you install, so check it again when you upgrade.

## 1. SpiderFoot — the scanner (separate program, GPL-2.0 at the pinned version)

| | |
|---|---|
| Project | SpiderFoot, by Steve Micallef — <https://github.com/smicallef/spiderfoot> |
| Pinned version | `v4.0` (`SPIDERFOOT_REF` in `deploy/spiderfoot/Dockerfile`) |
| License at `v4.0` | **GNU GPL v2** (the `LICENSE` file and the module headers at that tag say GPL) |
| License today | MIT on upstream `master` (relicensed after v4.0; the pin does **not** get that license) |

How octifoot uses it:

- SpiderFoot runs as its **own container** and octifoot talks to it only over its HTTP API.
  octifoot imports no SpiderFoot code. It is a separate program, not a derivative of it.
- `deploy/spiderfoot/Dockerfile` downloads the **unmodified** upstream `v4.0` source at build time.
  The only change applied inside the image is relaxing the `pyyaml` pin in `requirements.txt` so a
  prebuilt wheel is used. This repository does not redistribute SpiderFoot's source or any built image.
- `connector/src/spiderfoot_connector/data/sf_modules_v4.0.json` is a snapshot of module metadata
  (module names, `flags`, `useCases`, `watched` and `produced` event types) read from SpiderFoot
  v4.0, and `lean_modules.json` is a list generated from it. They hold interface facts, not SpiderFoot
  code, but they originate from a GPL-2.0 work. Treat them as derived from SpiderFoot v4.0 and
  Copyright (c) Steve Micallef; they are the one part of this repository whose licensing you
  may want to review before reusing it outside this project.
- **If you build and publish a SpiderFoot image** (for example to a public registry), you are
  distributing GPL-2.0 software and must meet its terms, including offering the corresponding source.

SpiderFoot's modules query many third-party services. Each service has its own terms, rate limits,
and sometimes keys or licensing for the data it returns. Using them is your responsibility.

## 2. OpenCTI — the platform (Apache-2.0 Community Edition)

- OpenCTI, Copyright (c) 2021-2026 Filigran SAS — <https://github.com/OpenCTI-Platform/opencti>.
- The Community Edition is Apache-2.0. The Enterprise Edition is under a separate license:
  do not enable Enterprise Edition features unless you hold that license.
- `deploy/docker-compose.yml` pulls `opencti/platform` and `opencti/worker` `7.261002.0` from
  their registry. They are not redistributed here.
- The connector depends on `pycti==7.261002.0` (Apache-2.0).

## 3. Services started by `deploy/docker-compose.yml`

These images are pulled from their publishers' registries; nothing below is redistributed here.
Their licenses differ a lot, so read them before deploying beyond a local test.

| Service | Image | License (per upstream repository) |
|---|---|---|
| Redis | `redis:8.10.1` | Redis 8: your choice of RSALv2, SSPLv1 or AGPLv3 (Redis 7.2 and earlier: BSD-3-Clause) |
| Elasticsearch | `docker.elastic.co/elasticsearch/elasticsearch:8.19.21` | Default: your choice of AGPL-3.0, SSPL-1.0 or Elastic License 2.0; some code Apache-2.0-compatible or ELv2 only |
| Object storage | `pgsty/silo:RELEASE.2026-09-16T00-00-00Z` | AGPL-3.0 (a MinIO fork maintained by PGSTY) |
| RabbitMQ | `rabbitmq:4.3-management` | MPL-2.0 (some files Apache-2.0) |

## 4. Python runtime dependencies of the connector

Resolved in the development environment on 2026-10-04. All are permissive except `certifi`
(MPL-2.0, file-level copyleft; used unmodified).

| License | Packages |
|---|---|
| Apache-2.0 | pycti, requests, boto3, botocore, s3transfer, deprecation, importlib-metadata, opentelemetry-api, opentelemetry-sdk, opentelemetry-semantic-conventions, prometheus-client (Apache-2.0 AND BSD-2-Clause), packaging (Apache-2.0 OR BSD-2-Clause), python-dateutil (Apache-2.0 / BSD dual), regex (Apache-2.0 AND CNRI-Python) |
| MIT | annotated-doc, annotated-types, anyio, cachetools, charset-normalizer, datefinder, fastapi, filigran-sseclient, h11, jmespath, pydantic, pydantic-core, pyjwt, pytz, pyyaml, setuptools, six, typing-inspection, urllib3, zipp, simplejson (MIT OR AFL-2.1) |
| BSD | antlr4-python3-runtime, click (BSD-3-Clause), idna (BSD-3-Clause), pika (BSD-3-Clause), python-json-logger (BSD-2-Clause), starlette (BSD-3-Clause), stix2, stix2-patterns, uvicorn (BSD-3-Clause) |
| MPL-2.0 | certifi |
| PSF-2.0 | typing-extensions |

Development only (not shipped): pytest (MIT), responses (Apache-2.0), ruff (MIT).

The container images are built on `python:3.13-slim` (connector) and `python:3.11-slim` (SpiderFoot);
Debian and Python's own licenses apply to those base layers.

## 5. Standard

The objects the connector produces follow **STIX 2.1** (see the citation in the README). The OASIS
standard is © OASIS Open; the connector implements it and does not reproduce the specification text.

## 6. Test data

`connector/tests/fixtures/*.json` are synthetic: they use `example.com`, `example.net` and similar
reserved names. No real third-party scan data is included.
