# SPEC: asn-enrichment

Status: approved
Extends: [SPEC-spiderfoot-connector.md](SPEC-spiderfoot-connector.md) (mapper only)

## Objective

Tell the analyst **which autonomous system each imported IP belongs to**, as native OpenCTI
objects. This also makes CDN/shared hosting visible at a glance (e.g. AS13335 for Cloudflare)
without attributing anything to the target.

Evidence (real scan, domain behind Cloudflare): SpiderFoot emits `NETBLOCK_MEMBER` /
`NETBLOCKV6_MEMBER` (`data` = CIDR, `source_data` = the IP) and `BGP_AS_MEMBER`
(`data` = ASN number, `source_data` = the CIDR), all from `sfp_ripe`. Chaining them gives
IP → netblock → AS.

Success:
- Each imported IP whose netblock has a known AS gets a `belongs-to` relationship to an
  `autonomous-system` object (`number`), with provenance.
- AS objects exist only if linked to at least one imported IP; no orphans.
- The scan Note lists the ASNs found and how many IPs each covers.
- Netblocks are not imported as objects; no AS ↔ target-domain relationship is created.

Out of scope: AS names/organisations (not in the events), netblock/CIDR objects, country and
registrar data (`COUNTRY_NAME` comes from co-hosted sites' WHOIS: unreliable), technology/port events.

## Assumptions (approved by the user's standing instruction to proceed)

1. Chain: `NETBLOCK_MEMBER`/`NETBLOCKV6_MEMBER` map IP → CIDR; `BGP_AS_MEMBER` maps CIDR → ASN.
2. Only IPs in the output are linked; events about other IPs are ignored.
3. `autonomous-system` gets `number`, `x_opencti_created_by_ref`, and an external reference
   (`source_name` SpiderFoot, `external_id` = scan id, module from the event). No score, no name.
4. Relationship `belongs-to` from the IP to the AS, with provenance, deterministic id.
5. ASN must be an integer 1..4294967295; otherwise the event is counted `invalid`, never guessed.
6. Netblock and BGP events leave the `unmapped` counter (they are now consumed).
7. The Note gets one line: `Autonomous systems: AS13335 (2 IPs), ...`.
8. The relationship states a fact about the IP's network, not ownership by the target.

## Commands

```bash
cd connector && . .venv/bin/activate
pytest tests/unit/test_mapper_asn.py -q
pytest && ruff check . && ruff format --check .
```

## Structure

```
connector/src/spiderfoot_connector/mapper.py   # extended
connector/tests/fixtures/scan_events_asn.json  # anonymized events, documentation ranges
connector/tests/unit/test_mapper_asn.py        # new
docs/README.md                                 # mapping table
```

## Style

```python
def parse_asn(raw: str) -> int | None:
    """'13335' -> 13335; None unless an integer in 1..4294967295."""
    value = raw.strip()
    if not value.isdigit():
        return None
    number = int(value)
    return number if 1 <= number <= 4_294_967_295 else None
```

## Test strategy

- Unit, TDD, no network. Fixture uses documentation ranges (203.0.113.0/24, 2001:db8::/32,
  private ASNs 64496+), no real third-party data.
- Cases: IPv4 and IPv6 linked via chain; two IPs in one netblock share one AS object;
  two ASNs; IP without netblock or netblock without AS unlinked and no orphan AS; invalid ASN
  counted; events about non-output IPs ignored; Note line; BGP/NETBLOCK no longer unmapped;
  deterministic ids; every relationship carries provenance (external_id).
- Regression: all previous mapper tests green and unchanged.
- Live: import real events into OpenCTI and read the relationship back (new rule: round-trip new fields).

## Boundaries

**Always**
- Round-trip new object types through the real OpenCTI once before archiving.
- Count every skipped or invalid event.

**Ask first**
- Creating netblock/CIDR objects, AS names, or any AS ↔ domain relationship.
- Mapping `COUNTRY_NAME`, registrar, or hosting-provider events.

**Never**
- Link an AS to the target domain or to co-hosted sites.
- Commit real third-party ASNs/IPs into fixtures.
