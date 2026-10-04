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
