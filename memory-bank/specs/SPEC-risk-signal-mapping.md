# SPEC: risk-signal-mapping

Status: draft
Extends: [SPEC-spiderfoot-connector.md](SPEC-spiderfoot-connector.md) (mapper only; allowlist, config and scan flow unchanged)

## Objective

Extend `connector/src/spiderfoot_connector/mapper.py` so reputation signals and IPv6
addresses found by SpiderFoot reach OpenCTI **without polluting the graph**.

Evidence (real scan of an owner-provided domain behind Cloudflare, 436 events):
`MALICIOUS_SUBNET` was Cloudflare's whole /20, `MALICIOUS_COHOST` were unrelated sites
sharing the CDN IP, and `AFFILIATE_EMAILADDR` (56) came from the WHOIS of those co-hosted
sites. Importing them as objects related to the target would present other companies'
data as the target's.

Success:
- IPv6 addresses of the target are imported like IPv4 (`ipv6-addr`, `resolves-to`).
- An already-imported IP flagged by a `MALICIOUS_IPADDR` event carries a label and a
  per-feed external reference.
- Subnet and co-host reputation hits appear in the scan Note, not as objects.
- Nothing from `AFFILIATE_EMAILADDR`, `AFFILIATE_IPADDR`, `AFFILIATE_IPV6_ADDRESS` is imported.

## Assumptions (approved)

1. `IPV6_ADDRESS` joins the IP path: `ipv6-addr` + `resolves-to` from the source host.
2. `MALICIOUS_IPADDR` creates no new object. A flagged IP that is part of the output gets
   label `spiderfoot:malicious` (`x_opencti_labels`) and one external reference per feed
   (`source_name` = feed name, e.g. "Maltiverse"). A flagged IP not in the output is
   skipped and counted.
3. `MALICIOUS_SUBNET` and `MALICIOUS_COHOST` are listed in the Note (feed + value, max 20
   lines then "and N more"); never objects.
4. `AFFILIATE_EMAILADDR` stays unmapped; documented as unreliable (WHOIS of co-hosted sites).
5. `AFFILIATE_IPADDR` and `AFFILIATE_IPV6_ADDRESS` stay unmapped (nameserver IPs).
6. Score unchanged; label + reference carry the signal.
7. No STIX `Indicator`: flags on shared CDN IPs would create false-positive indicators.
8. Event data format is `"<Feed name> [<value>]\n<optional url>"`; unparsable values are
   counted as invalid, never guessed.

## Commands

Unchanged from SPEC-spiderfoot-connector#commands. Relevant:

```bash
cd connector && . .venv/bin/activate
pytest tests/unit/test_mapper.py -q
pytest && ruff check . && ruff format --check .
```

## Structure

```
connector/src/spiderfoot_connector/mapper.py     # extended
connector/tests/fixtures/scan_events_risk.json   # anonymized events from the real scan
connector/tests/unit/test_mapper_risk.py         # new
docs/README.md                                   # mapping table + rationale updated
```

## Style

Pure functions, no I/O. Feed parsing isolated and tested on its own:

```python
_FEED_RE = re.compile(r"^(?P<feed>[^\[\n]+?)\s*\[(?P<value>[^\]\n]+)\]")


def parse_feed_event(data: str) -> tuple[str, str] | None:
    """'Maltiverse [1.2.3.4]\\n...' -> ('Maltiverse', '1.2.3.4'); None if unparsable."""
    m = _FEED_RE.match(data.strip())
    return (m["feed"].strip(), m["value"].strip()) if m else None
```

## Test strategy

- Unit, TDD, no network. Fixture: real event shapes with the target domain replaced by
  `example.com` and co-hosted domains by `cohost-N.example.net`.
- Cases: IPv6 mapped + relationship; flagged IP gets label and reference per feed; two
  feeds on one IP → two references, one label; flagged IP absent from output → skipped and
  counted; subnet/co-host only in Note, truncated at 20; affiliate events never produce
  objects; unparsable feed data counted invalid; output deterministic.
- Regression: existing `test_mapper.py` stays green unchanged.
- Live check (manual, optional): re-enrich an owned domain and confirm the label shows on
  the IPs in OpenCTI.

## Boundaries

**Always**
- Keep third-party/shared-infrastructure data out of the graph; report it in the Note.
- Count every skipped or unparsable event so nothing disappears silently.
- Keep mapping pure and deterministic.

**Ask first**
- Creating `Indicator`, `Infrastructure` or CIDR objects.
- Importing any `AFFILIATE_*` or `CO_HOSTED_*` event as an object.
- Changing scores based on reputation feeds.

**Never**
- Link co-hosted sites, shared subnets or their WHOIS emails to the target as relationships.
- Touch the allowlist, config or scan flow in this iteration.
- Commit real third-party domains or emails from the scan into fixtures.
