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
| `SPIDERFOOT_TIMEOUT_SECONDS` | `900` | On timeout the scan is stopped and partial results are imported. Can be overridden from the control panel (60-7200) |
| `SPIDERFOOT_MAX_TOTAL_SECONDS` | `3600` | Bound for one whole analysis (all its scans, 60-86400). Each scan gets `min(per-scan limit, time left)`; no scan starts with less than 60 s left. Can be overridden from the control panel (60-14400) |
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
- Only `INTERNET_NAME` expands. IPs, emails, affiliates and co-hosts never do (affiliate hostnames are not imported at all).

An "expansion" Note on the target lists scans run, depth reached, failed sub-scans, and what
was skipped and why. Scans run one after another, and the whole analysis is bounded by
`SPIDERFOOT_MAX_TOTAL_SECONDS`: targets skipped for lack of time are named in the Note
(`Skipped, total time limit reached`) and counted as `deadline_skipped` in the work message,
and the snapshot is marked incomplete. While more scans are queued, each finished scan is sent
to OpenCTI right away, so a stopped or failed run keeps what was already imported; the final
bundle still carries everything (ids are deterministic, so repeats are harmless).

## What is imported

The full decision for every one of SpiderFoot's 172 event types, with the evidence, is in [event-catalogue.md](event-catalogue.md).

| SpiderFoot event | STIX object | Relationship |
|---|---|---|
| `INTERNET_NAME` | `domain-name` | `related-to` → scanned domain |
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

### Control panel (domains and maximum time)

A small web page to add or remove the domains octifoot may analyse and to change the maximum time of an analysis, without editing `deploy/.env`. **Off by default.** To turn it on put a token in `deploy/.env`
(`openssl rand -hex 24`), recreate the connector and open <http://localhost:8099>:

```bash
# deploy/.env
OCTIFOOT_UI_TOKEN=paste-the-generated-token-here
# optional: OCTIFOOT_UI_LANG=es  (Spanish)  and OCTIFOOT_UI_PORT=8099
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d connector-spiderfoot
```

- **Authorized domains.** The `.env` list is shown read-only; below it you add domains (with their subdomains) or remove the ones you added. Adding requires ticking that you own the domain or have written permission to investigate it. Names are validated:
  a bare top-level name (`com`), a public suffix (`co.uk`, `github.io`), an IP address, a wildcard, a URL or a port is refused. The same validation applies to the `.env` list, which the connector now refuses to start with if an entry is unsafe.
  A domain you add is analysable at once and removable at any time; removing it does not delete what was already imported.
- **Maximum total time.** Same idea for the whole analysis (60 to 14400 s, empty goes back to `SPIDERFOOT_MAX_TOTAL_SECONDS`).
- **Maximum time.** A whole number of seconds between 60 and 7200 applies to the next analysis (not ones already running); empty goes back to `SPIDERFOOT_TIMEOUT_SECONDS`. The Note's "stopped after N s" shows the value that was used.
- **Why it is safe to have.** This page decides what may be scanned, so it is local only (published on `127.0.0.1`), protected by the token, and refuses any request whose `Host` is not localhost; every change needs a session, a CSRF token and,
  for a domain, the ownership confirmation; failed logins are throttled; responses carry restrictive headers; every change is written to an audit log (`audit.log` in the `octifoot-state` volume: time, action, value, client address, never the token).
- **Where things live.** Settings in `settings.json` and the audit in `audit.log`, both in the `octifoot-state` Docker volume. A corrupt file falls back to the `.env` values and the page says so.
- **Do not expose it.** It has one operator and one token and no TLS. Do not publish the port on another interface; if you ever must, put a TLS reverse proxy with its own authentication in front.

### Free API keys (optional)

Keyed SpiderFoot modules (52 of them add data octifoot already imports: reputation flags, subdomains, passive DNS) run only if you give octifoot your own free keys through `SPIDERFOOT_API_KEYS_FILE`. Off by default; octifoot stays open source and adds no dependency.
Each key is written into SpiderFoot and verified by reading it back (SpiderFoot answers `SUCCESS` to a write under a wrong name and stores nothing); key values never appear in logs, Notes or errors; a key never enables an active module.
Details, the list of modules, the free tiers found and where keys are stored: [api-keys.md](api-keys.md).

### Automatic re-analysis (watch)

Off by default. Set `SPIDERFOOT_WATCH_INTERVAL_MINUTES` (5 to 10080) and the connector re-analyses, by itself, the domains you opt in: put the label **`octifoot:watch`** on a `Domain-Name` observable in OpenCTI.
A loop in the connector (a daemon thread; one cycle every quarter of the interval, between 1 and 15 minutes) reads the labelled domains and, for each one that is **on the allowlist** and **due**, asks OpenCTI to run this connector's enrichment on it,
the same request your click makes. Every automated run is therefore an ordinary work item with the usual Notes, snapshot and comparison, so the change detection finally has something to compare.

A domain is due when its newest snapshot Note is at least one interval old (or it has none) and it was not already requested within the interval. Due domains go oldest first, never-scanned first, at most `SPIDERFOOT_WATCH_MAX_PER_CYCLE` (default 3) per cycle.
A domain not on the allowlist is skipped and logged; removing the label stops the runs. A failing cycle never stops the loop. `CONNECTOR_AUTO` stays `false`: nothing is scanned without the label.
The connector's OpenCTI token must be allowed to request enrichments (this stack uses the admin token; a dedicated connector user needs that capability). The "recently requested" record is in memory; after a restart the snapshot time decides.
Alerting is not implemented: the comparison Note is the record of what changed.

### Link to the full SpiderFoot scan

octifoot imports only part of a scan (the part that is safe and useful, 18 of SpiderFoot's 172 event types; the rest is counted as "unmapped"). The complete record stays in SpiderFoot's own database and UI, which runs in the same stack.
With `SPIDERFOOT_UI_URL` set (the address your **browser** uses, `http://localhost:5001` by default in Compose; not the internal `SPIDERFOOT_URL`), every external reference octifoot creates carries a link to
`<UI URL>/scaninfo?id=<scan id>` and the first line of each scan Note ends with `Full results in SpiderFoot: <that URL>`. From any object or Note in OpenCTI, one click opens the raw events, the co-hosted sites and everything the import left out.
Empty means no links. The SpiderFoot UI has no authentication and is published on `127.0.0.1` only; do not expose it further without putting authentication in front. The link works only while the scan is still in SpiderFoot.

### What changed since the last scan

Each enrichment of a root target writes a Note `octifoot snapshot for <target>: <summary>` (for example `3 changes since 2026-10-04`, `no changes since ...` or `first snapshot`). Its text lists, per category, what was
**added** and what was **not seen this time**: hostnames, IPs, emails, AS numbers, name servers, mail hosts; certificates (additions only, because the import is capped at the 10 newest); registrar and hosting changes;
SPF and DMARC state changes (only when the direct DNS check ran and both snapshots know the state). It ends with a machine-readable `Snapshot (...)` line: that line is the state, kept in OpenCTI instead of the container.
The next enrichment reads the newest snapshot Note of the same target (the abstract must start with `octifoot snapshot for <target>:`) and compares. Deleting those Notes resets the baseline.

Disappearances are reported only when **both** scans were complete (finished, not stopped by the timeout, no failed sub-scan): an incomplete scan or a failing source would make things look gone. When this scan's subdomain sources reported errors,
the not-seen hostnames carry that caveat; against an incomplete previous scan, additions carry "may not be new". Two more caveats come from a limit that cannot be removed: SpiderFoot's crt.sh module cannot report its own outages, so a scan where crt.sh did not answer looks the same as a domain with no certificates.
Hostnames added after a scan whose subdomain sources reported errors are marked "may only be newly visible", and certificates appearing where the previous scan had none are marked "crt.sh may not have answered".
In a real pair of scans of one domain, the second one found a new hostname and 13 certificates that were almost certainly not new, just visible this time.
If the previous snapshot cannot be read, the new one is still written and the Note says so.

### What OpenCTI already knows

Before sending the bundle, the connector asks OpenCTI (one read-only, batched GraphQL query with its own token) about the imported domain names, IPs and emails and adds a Note,
`OpenCTI knowledge (queried by octifoot before this import; excludes SpiderFoot's own objects)`, attached to the scanned domain. It lists what **other sources** attach to those observables:
non-revoked indicators (with the highest score), reports, labels other than `spiderfoot:*`, and a creator other than SpiderFoot. With nothing, it says `none of the N imported observables has indicators, reports or labels from other sources in OpenCTI`.
The abstract carries the counts, so the Notes list shows at a glance whether a scan touched things you already track.

This is the direction the data flows back: SpiderFoot finds, OpenCTI correlates. Objects octifoot created itself never count (a previous import is not knowledge), and nothing in the graph is modified by the lookup.
A failing lookup never fails the enrichment. Acting on the knowledge (raising scores, seeding scans from related entities) is not done.

### DNS checks

For the root target of an enrichment (not for expansion sub-scans) the connector itself asks the resolver for MX, SPF (TXT), `_dmarc` TXT, CAA, DS and `_mta-sts` TXT of the scanned name and adds
`DNS checks (queried by octifoot, not by SpiderFoot): MX: ...; SPF: ...; DMARC: p=reject; CAA: none; DNSSEC: no DS record; MTA-STS: none` to the Note. These are ordinary recursive lookups for a name you
authorised, the same kind SpiderFoot's DNS module issues. SpiderFoot never asks for `_dmarc`, CAA, DS or `_mta-sts`, so this is data neither SpiderFoot nor OpenCTI would give you.

Each answer is *found*, *none* (NXDOMAIN or an empty answer) or *unknown* (timeout, SERVFAIL): unknown is never reported as none. A null MX (`0 .`, RFC 7505) means the name accepts no mail. Only the scanned name is checked,
so DMARC inherited from an organisational domain is not modelled. A failing check never fails the enrichment.

With these facts the mail findings rest on the target's own MX: `receives mail but publishes no SPF record`, `no DMARC record at _dmarc.<name>`, `DMARC policy is p=none`, `SPF ends in +all/?all`; a name with no MX gets none of them.
If the MX lookup itself fails, the earlier inference from scan events applies, with its disclaimer; it uses only records of the scanned name itself, never a parent zone's, so expansion sub-scans do not repeat the root's finding.

### Key findings

The scan Note opens with a `Key findings (as of this scan)` block: what is notable in the data, by fixed rules, each tied to evidence in the same Note.
It appears right after the first line; with nothing notable it reads `Key findings: nothing notable in the data the answering sources returned.` (never "clean").

| Finding | Rule |
|---|---|
| Flagged | the target or an imported hostname/IP carries the malicious label |
| Mail without SPF | mail hosts known, DNS answered for the target, no `v=spf1` record (DMARC is not checked by SpiderFoot, so it is never claimed) |
| Certificate | the newest imported certificate per subject CN is expired, or expires within 14 days (older ones are rotation history) |
| Newly registered | created less than 30 days before the scan |
| Registration expiring | expires within 30 days, or already expired |
| Shared infrastructure listed | reputation listings on subnets or co-hosts (not the target's own) |
| Coverage | subdomain-enumerating sources that reported errors, so "no subdomains" may not be true |
| Scan incomplete | always first: the scan was stopped by `SPIDERFOOT_TIMEOUT_SECONDS` (`scan incomplete: stopped after N s, results are partial`) or ended with a status other than FINISHED |

A scan can be cut by the timeout on domains with many certificates: `sfp_crt` fetches them one by one and every certificate's names flood the other modules (a real scan of 53 certificates ran 15 minutes).
When that happens the first finding says so; raise `SPIDERFOOT_TIMEOUT_SECONDS` if you want complete scans of such domains.

No object, label or score is derived from findings (a label such as "newly registered" would go stale). Thresholds are constants in `mapper.py`.

### TLS certificates

`SSL_CERTIFICATE_RAW` (certificates found through crt.sh) becomes a STIX `x509-certificate` with serial number, issuer, subject, validity and signature algorithm,
`related-to` the scanned domain. A certificate is the target's when SpiderFoot's event names the scanned name as the one crt.sh was queried for (`source_data`: every returned certificate has that name in its subject or SAN)
or when its CN is the target, a wildcard of it, a name under it, or its parent. The subject can therefore be another domain of the same owner (in a real scan all 53 certificates had CN `digi.ninja` and the target only as a SAN).
Certificates returned for any other queried name are counted under Unmapped as "not the target's". Names inside certificates never become domain objects (a shared certificate can list other customers).
At most 10 are imported (most recent `Not Before` first) and the Note says how many were left out (`TLS certificates: N imported, M over the cap of 10, K not issued for the target`).
SpiderFoot truncates the certificate text at 1024 characters, so the SAN list and extensions are not available. The object id comes from the serial number.
crt.sh is frequently unavailable (HTTP 502), in which case there are simply no certificates; see Source health above.

### WHOIS and DNS TXT

Two more lines in the scan Note, both text only (no objects), both only from events whose source is the scanned domain or a parent of it
(WHOIS or TXT of a provider's domain is counted under Unmapped as "not the target's"):

- `WHOIS (as reported by SpiderFoot): created 2026-09-27 (7 days before this scan); updated ...; expires ...; status: clientTransferProhibited, ...; DNSSEC: unsigned`.
  Domain age is useful CTI context; STIX has no field for it. Only dates, EPP status and DNSSEC are read: registrant, contact, phone and email lines are never copied.
  SpiderFoot truncates the WHOIS text at 1024 characters, so later fields (name servers, DNSSEC) are sometimes missing and the line shows only what parsed.
- `DNS TXT (as reported by SpiderFoot): SPF: v=spf1 ... ; DMARC: p=quarantine; verification tokens: google (1); other records: N`.
  SPF is shown verbatim (capped at 160 characters), DMARC only as its policy, verification tokens only as the issuing service (values are never printed).
  In the three domains tested only verification tokens appeared, so the SPF and DMARC parsers are proven on synthetic data.

### Source health

After each scan the connector reads SpiderFoot's scan log and adds one line to the scan Note naming the modules
that logged errors, most errors first, with a count and the first message (eight modules, then "and N more"), for example
`Sources that reported errors (13 modules; ...): sflib: Failed to connect to https://api.bgpview.io/... (47); sfp_sublist3r: Bad response code "None" from Sublist3r API (2); ...`.
Read it before concluding that a target has no subdomains or no reputation hits: those findings depend on third-party sources that fail often
(HTTP 401/403/404, API changes, unreachable hosts). The line is a diagnostic only; it never changes which objects are imported,
and a failure to read the log never fails the enrichment.

**Limit:** it only sees what SpiderFoot logs as an error. A module that reports an outage as "no information" is invisible here;
the clearest case is `sfp_crt` (crt.sh), which logs HTTP 502 and "no certificates" identically. Some errors are also constant
configuration noise (`sfp_customfeed` without a URL, `sfp_flickr` without a key). Absence of the line does not prove every source answered.

### Infrastructure providers

`DOMAIN_REGISTRAR`, `PROVIDER_HOSTING`, `PROVIDER_DNS` and `PROVIDER_MAIL` appear as one line in the scan
Note, for example `Infrastructure (as reported by SpiderFoot): registrar: ...; hosting: ...; DNS: a, b; mail: c`.
Only records whose source is the scanned domain (or a parent of it) count; hosting counts only for an IP that was imported for the target. Records from a provider's domain
seen in the same scan (for example the MX of the domain a CNAME points to) are counted under Unmapped as "not the target's". Values are sorted and de-duplicated, five per kind at most. They are text, not objects or relationships:
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

`AFFILIATE_INTERNET_NAME` is not imported (since the `drop-affiliate-names` task): in real scans 2 of 2, 5 of 6 and 17 of 17 extra
domain objects were other parties' hostnames (Google's mail servers, reverse DNS of someone else's IPs, name servers) related to the target at half score.
The mail and name servers are already summarised in the `Infrastructure` Note line. An IP whose source host is such a name is not linked to the target either.
`AFFILIATE_EMAILADDR` is unreliable: the emails come from the WHOIS of co-hosted sites, not
of the target. `AFFILIATE_IPADDR` / `AFFILIATE_IPV6_ADDRESS` are nameserver IPs. `PUBLIC_CODE_REPO`
matches repositories by name, so it would credit other people's work to the target. Open ports, banners
and technologies need active or API-key modules; the passive scans measured here produced none of those
events. Every other event type is also skipped. Skipped types are counted
in the Note and logs. False positives are dropped.
Re-running a scan does not duplicate observables (deterministic STIX ids).

## Provenance and coverage

Every scan Note (the root scan and each sub-scan) carries two lines:

- `Provenance: octifoot <version>; SpiderFoot <version>; profile lean, use case passive; modules requested: N (list sha256 …); time applied N s; events: N (sha256 …)`.
  The event digest is the SHA-256 of SpiderFoot's exported events (sorted, so order does not matter); the first 16 hex characters are shown. It lets you show later that an import matches what SpiderFoot returned (recompute it from the scan's JSON export). It proves the content did not change, not that the sources were authentic. `SpiderFoot unknown` means `/ping` could not be read.
- `Coverage: N modules produced data; N modules reported errors; API-keyed modules active: …`. Key names only, never values. A source that answers "no information" cannot be told from silence, so a missing finding is not proof of absence.

## Data handling

- **What can reach OpenCTI:** hostnames, IPs, AS numbers, certificates (as Note lines), email addresses (`email-addr`) and Note text. Email addresses are the only personal data imported.
- **What is never copied:** WHOIS registrant, contact, phone and email lines (only dates, EPP status and DNSSEC are read).
- **Purpose and scope:** only domains in the allowlist can be analysed; the control panel records who changed it and when.
- **Retention and removal:** octifoot does not delete anything by itself. Delete observables and Notes in OpenCTI, and scans in SpiderFoot (its UI), when the purpose ends. The control panel's audit log never contains the token.
- **Raw data:** SpiderFoot keeps the raw events; OpenCTI keeps the mapped objects and the scan Note with the digest above.
- This is operator guidance, not legal advice: the lawful basis, retention period and rights handling depend on your organisation and jurisdiction.

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
