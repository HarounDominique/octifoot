import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from spiderfoot_connector.mapper import map_events, parse_asn

NOW = datetime(2026, 10, 4, 6, 0, 0, tzinfo=UTC)
FIXTURE = Path(__file__).parent.parent / "fixtures" / "scan_events_asn.json"


def run(events):
    return map_events(events, target="example.com", scan_id="S1", score=30, now=NOW)


def ev(etype, data, source="example.com", module="sfp_ripe"):
    return {
        "event_type": etype,
        "data": data,
        "source_data": source,
        "module": module,
        "false_positive": 0,
    }


@pytest.fixture
def asn():
    return run(json.loads(FIXTURE.read_text()))


def by_type(result, type_):
    return [o for o in result.objects if o.type == type_]


def links(result):
    """(ip value, AS number) for every belongs-to relationship."""
    objs = {o.id: o for o in result.objects}
    return sorted(
        (objs[r.source_ref].value, objs[r.target_ref].number)
        for r in by_type(result, "relationship")
        if r.relationship_type == "belongs-to"
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("13335", 13335), (" 64496 ", 64496), ("4294967295", 4294967295)],
)
def test_parse_asn_valid(raw, expected):
    assert parse_asn(raw) == expected


@pytest.mark.parametrize("raw", ["", "AS13335", "0", "-5", "4294967296", "1.5", "abc"])
def test_parse_asn_invalid(raw):
    assert parse_asn(raw) is None


def test_ips_linked_to_their_as_via_netblock(asn):
    assert links(asn) == [
        ("2001:db8:1::10", 64497),
        ("203.0.113.10", 64496),
        ("203.0.113.77", 64496),
    ]


def test_ips_share_one_as_object(asn):
    assert sorted(o.number for o in by_type(asn, "autonomous-system")) == [64496, 64497]


def test_no_orphan_as_for_ips_not_in_output(asn):
    # 64499 belongs to a netblock whose IP (192.0.2.44) was never imported
    assert 64499 not in [o.number for o in by_type(asn, "autonomous-system")]


def test_ip_without_as_stays_unlinked(asn):
    assert "198.51.100.9" not in [ip for ip, _ in links(asn)]
    assert "198.51.100.9" in [o.value for o in by_type(asn, "ipv4-addr")]


def test_invalid_asn_counted_not_guessed():
    r = run(
        [
            ev("IP_ADDRESS", "203.0.113.10", module="sfp_dnsresolve"),
            ev("NETBLOCK_MEMBER", "203.0.113.0/24", "203.0.113.10"),
            ev("BGP_AS_MEMBER", "AS64496", "203.0.113.0/24"),
        ]
    )
    assert by_type(r, "autonomous-system") == []
    assert r.invalid == 1


def test_as_has_provenance_and_no_score(asn):
    system = by_type(asn, "autonomous-system")[0]
    assert system.x_opencti_created_by_ref == by_type(asn, "identity")[0].id
    ref = system.x_opencti_external_references[0]
    assert (ref["source_name"], ref["external_id"]) == ("SpiderFoot", "S1")
    assert "sfp_ripe" in ref["description"]
    assert not hasattr(system, "x_opencti_score")


def test_relationships_carry_provenance(asn):
    for rel in by_type(asn, "relationship"):
        assert rel.external_references[0]["external_id"] == "S1"


def test_as_never_linked_to_the_target_domain(asn):
    systems = {o.id for o in by_type(asn, "autonomous-system")}
    for rel in by_type(asn, "relationship"):
        if rel.source_ref in systems or rel.target_ref in systems:
            assert rel.relationship_type == "belongs-to"
            assert rel.source_ref not in {o.id for o in by_type(asn, "domain-name")}


def test_netblock_and_bgp_events_are_consumed_not_unmapped(asn):
    for key in ("NETBLOCK_MEMBER", "NETBLOCKV6_MEMBER", "BGP_AS_MEMBER"):
        assert key not in asn.unmapped


def test_note_lists_asns_with_ip_counts(asn):
    note = by_type(asn, "note")[0].content
    assert "Autonomous systems: AS64496 (2 IPs), AS64497 (1 IP)" in note


def test_deterministic(asn):
    again = run(json.loads(FIXTURE.read_text()))
    assert [o.id for o in asn.objects] == [o.id for o in again.objects]
