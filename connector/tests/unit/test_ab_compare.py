from datetime import UTC, datetime

from spiderfoot_connector.abcompare import compare_events, speedup

NOW = datetime(2026, 10, 4, 6, 0, 0, tzinfo=UTC)


def ev(etype, data, source="example.com", module="sfp_x"):
    return {
        "event_type": etype,
        "data": data,
        "source_data": source,
        "module": module,
        "false_positive": 0,
    }


BASE = [
    ev("INTERNET_NAME", "www.example.com", module="sfp_crt"),
    ev("IP_ADDRESS", "203.0.113.10", module="sfp_dnsresolve"),
    ev("EMAILADDR", "admin@example.com"),
]


def cmp(a, b):
    return compare_events(a, b, target="example.com", scan_a="A1", scan_b="B1", score=30, now=NOW)


def test_identical_event_sets_are_identical():
    result = cmp(BASE, list(reversed(BASE)))
    assert result.identical
    assert result.only_a == [] and result.only_b == []


def test_scan_ids_and_modules_do_not_count_as_differences():
    other = [{**e, "module": "sfp_other"} for e in BASE]
    assert cmp(BASE, other).identical


def test_missing_object_is_reported_with_its_side():
    result = cmp(BASE, BASE[:2])
    assert not result.identical
    assert result.only_a == [
        "email-addr:admin@example.com",
        "relationship:related-to:email-addr:admin@example.com>domain-name:example.com",
    ]
    assert result.only_b == []


def test_extra_object_in_b_is_reported():
    extra = [*BASE, ev("INTERNET_NAME", "api.example.com")]
    result = cmp(BASE, extra)
    assert "domain-name:api.example.com" in result.only_b
    assert result.only_a == []


def test_malicious_flag_difference_reported_separately_and_does_not_break_identity():
    flagged = [*BASE, ev("MALICIOUS_IPADDR", "Maltiverse [203.0.113.10]", "203.0.113.10")]
    result = cmp(flagged, BASE)
    assert result.identical
    assert result.flag_diffs == [
        "ipv4-addr:203.0.113.10: A has labels ['spiderfoot:malicious'], B has []"
    ]


def test_unmapped_counts_are_returned_for_each_side():
    a = [*BASE, ev("COUNTRY_NAME", "China")]
    result = cmp(a, BASE)
    assert result.unmapped_a == {"COUNTRY_NAME": 1}
    assert result.unmapped_b == {}


def test_note_only_differences_do_not_count():
    a = [*BASE, ev("MALICIOUS_COHOST", "Comodo Secure DNS [cohost-1.example.net]")]
    result = cmp(a, BASE)
    assert result.identical
    assert result.listed_a == 1 and result.listed_b == 0


def test_speedup():
    assert speedup(375.0, 150.0) == 0.6
    assert speedup(100.0, 100.0) == 0.0
    assert speedup(0.0, 10.0) == 0.0
