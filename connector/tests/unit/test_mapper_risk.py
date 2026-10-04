import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from spiderfoot_connector.mapper import map_events, parse_feed_event

NOW = datetime(2026, 10, 4, 6, 0, 0, tzinfo=UTC)
FIXTURE = Path(__file__).parent.parent / "fixtures" / "scan_events_risk.json"


def run(events):
    return map_events(events, target="example.com", scan_id="S1", score=30, now=NOW)


def ev(etype, data, source="example.com", module="sfp_x"):
    return {
        "event_type": etype,
        "data": data,
        "source_data": source,
        "module": module,
        "false_positive": 0,
    }


def by_type(result, type_):
    return [o for o in result.objects if o.type == type_]


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ("Maltiverse [104.21.14.125]\n", ("Maltiverse", "104.21.14.125")),
        (
            "VoIP Blacklist (VoIPBL) [10.0.0.0/20]\nhttps://x/check",
            ("VoIP Blacklist (VoIPBL)", "10.0.0.0/20"),
        ),
        (
            "  Comodo Secure DNS [cohost-1.example.net]",
            ("Comodo Secure DNS", "cohost-1.example.net"),
        ),
        ("no brackets here", None),
        ("[only value]", None),
        ("", None),
    ],
)
def test_parse_feed_event(data, expected):
    assert parse_feed_event(data) == expected


def test_ipv6_mapped_with_relationship():
    r = run(
        [
            ev("IPV6_ADDRESS", "2606:4700:3032::ac43:cb5a", source="www.example.com"),
            ev("INTERNET_NAME", "www.example.com"),
        ]
    )
    (ip,) = by_type(r, "ipv6-addr")
    assert ip.value == "2606:4700:3032::ac43:cb5a"
    domains = {o.value: o.id for o in by_type(r, "domain-name")}
    rel = [x for x in by_type(r, "relationship") if x.target_ref == ip.id]
    assert rel[0].relationship_type == "resolves-to"
    assert rel[0].source_ref == domains["www.example.com"]
    assert not r.unmapped.get("IPV6_ADDRESS")


def test_ipv6_invalid_counted():
    assert run([ev("IPV6_ADDRESS", "not-an-ip")]).invalid == 1


@pytest.fixture
def risk():
    return run(json.loads(FIXTURE.read_text()))


def ips(result):
    return {o.value: o for o in by_type(result, "ipv4-addr") + by_type(result, "ipv6-addr")}


def test_flagged_ip_gets_label_and_feed_reference(risk):
    ip = ips(risk)["203.0.113.10"]
    assert ip.x_opencti_labels == ["spiderfoot:malicious"]
    sources = [r["source_name"] for r in ip.x_opencti_external_references]
    assert sources == ["SpiderFoot", "Maltiverse"]


def test_unflagged_ip_has_no_label(risk):
    assert not hasattr(ips(risk)["2001:db8::10"], "x_opencti_labels")


def test_two_feeds_one_label_two_references():
    r = run(
        [
            ev("IP_ADDRESS", "203.0.113.10", module="sfp_dnsresolve"),
            ev("MALICIOUS_IPADDR", "Maltiverse [203.0.113.10]"),
            ev("MALICIOUS_IPADDR", "OtherFeed [203.0.113.10]"),
        ]
    )
    ip = ips(r)["203.0.113.10"]
    assert ip.x_opencti_labels == ["spiderfoot:malicious"]
    assert [x["source_name"] for x in ip.x_opencti_external_references] == [
        "SpiderFoot",
        "Maltiverse",
        "OtherFeed",
    ]


def test_flagged_ip_not_in_output_is_skipped_and_counted():
    r = run([ev("MALICIOUS_IPADDR", "Maltiverse [198.51.100.99]")])
    assert ips(r) == {}
    assert r.flags_skipped == 1


def test_subnet_and_cohost_only_in_note_never_objects(risk):
    values = {o.value for o in risk.objects if hasattr(o, "value")}
    assert not any("cohost" in v or "/24" in v for v in values)
    note = by_type(risk, "note")[0].content
    assert "VoIP Blacklist (VoIPBL): 203.0.113.0/24" in note
    assert "Comodo Secure DNS: cohost-1.example.net" in note


def test_note_lists_at_most_20_then_counts_the_rest():
    events = [ev("MALICIOUS_COHOST", f"Feed [h{i:02d}.example.net]") for i in range(23)]
    note = by_type(run(events), "note")[0].content
    assert note.count("Feed: h") == 20
    assert "and 3 more" in note


def test_affiliate_events_never_produce_objects(risk):
    values = {o.value for o in risk.objects if hasattr(o, "value")}
    assert "owner@cohost-1.example.net" not in values
    assert "198.51.100.5" not in values
    assert "2001:db8:ffff::5" not in values
    assert risk.unmapped["AFFILIATE_EMAILADDR"] == 2
    assert risk.unmapped["AFFILIATE_IPADDR"] == 1
    assert risk.unmapped["AFFILIATE_IPV6_ADDRESS"] == 1


def test_unparsable_feed_data_counted_invalid():
    r = run([ev("MALICIOUS_SUBNET", "garbage"), ev("MALICIOUS_IPADDR", "garbage")])
    assert r.invalid == 2


def test_risk_output_is_deterministic():
    events = json.loads(FIXTURE.read_text())
    assert [o.id for o in run(events).objects] == [o.id for o in run(events).objects]


def test_discovered_domains_only_internet_names_excluding_target_and_noise():
    r = run(
        [
            ev("INTERNET_NAME", "www.example.com"),
            ev("INTERNET_NAME", "WWW.example.com."),  # duplicate after normalization
            ev("INTERNET_NAME", "example.com"),  # the target itself
            ev("INTERNET_NAME", "api.example.com"),
            ev("AFFILIATE_INTERNET_NAME", "cdn.partner.net"),
            ev("INTERNET_NAME", "not a domain"),
            {**ev("INTERNET_NAME", "old.example.com"), "false_positive": 1},
        ]
    )
    assert r.discovered_domains == ["www.example.com", "api.example.com"]


def test_no_discoveries_yields_empty_list():
    assert run([]).discovered_domains == []


def test_feed_references_carry_external_id_so_opencti_keeps_them(risk):
    # OpenCTI silently drops external references that have neither url nor external_id.
    for ip in ips(risk).values():
        for ref in getattr(ip, "x_opencti_external_references", []):
            assert ref.get("external_id") or ref.get("url"), ref
