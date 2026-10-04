from datetime import UTC, datetime

from spiderfoot_connector.mapper import DOMAIN_EVENTS, IMPORTED_EVENTS, map_events

NOW = datetime(2026, 10, 4, 6, 0, 0, tzinfo=UTC)


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


def domains(result):
    return sorted(o.value for o in result.objects if o.type == "domain-name")


def test_affiliate_names_produce_no_objects_and_are_counted():
    r = run(
        [
            ev("INTERNET_NAME", "www.example.com"),
            ev("AFFILIATE_INTERNET_NAME", "aspmx.l.google.com"),
            ev("AFFILIATE_INTERNET_NAME", "ns1.partner.net"),
        ]
    )
    assert domains(r) == ["example.com", "www.example.com"]
    assert r.unmapped["AFFILIATE_INTERNET_NAME"] == 2
    assert not [o for o in r.objects if o.type == "relationship" and "google" in str(o)]


def test_note_lists_affiliate_names_under_unmapped():
    r = run([ev("AFFILIATE_INTERNET_NAME", "aspmx.l.google.com")])
    (n,) = [o for o in r.objects if o.type == "note"]
    assert "AFFILIATE_INTERNET_NAME=1" in n.content


def test_own_names_are_unchanged():
    own = run([ev("INTERNET_NAME", "www.example.com", module="sfp_crt")])
    mixed = run(
        [
            ev("INTERNET_NAME", "www.example.com", module="sfp_crt"),
            ev("AFFILIATE_INTERNET_NAME", "aspmx.l.google.com"),
        ]
    )
    assert {o.id for o in own.objects if o.type != "note"} == {
        o.id for o in mixed.objects if o.type != "note"
    }
    (www,) = [o for o in mixed.objects if o.type == "domain-name" and o.value == "www.example.com"]
    assert www.x_opencti_score == 30


def test_a_name_that_is_also_an_own_internet_name_is_still_imported():
    r = run(
        [
            ev("AFFILIATE_INTERNET_NAME", "api.example.com"),
            ev("INTERNET_NAME", "api.example.com"),
        ]
    )
    assert "api.example.com" in domains(r)


def test_ip_from_an_unimported_affiliate_host_is_not_linked_to_the_target():
    r = run(
        [
            ev("AFFILIATE_INTERNET_NAME", "mx.partner.net"),
            ev("IP_ADDRESS", "203.0.113.9", source="mx.partner.net"),
        ]
    )
    assert not [o for o in r.objects if o.type == "ipv4-addr"]
    assert not [o for o in r.objects if o.type == "relationship"]
    assert r.unmapped["IP_ADDRESS (affiliate host)"] == 1


def test_ip_from_the_target_or_an_own_host_is_still_linked():
    r = run(
        [
            ev("INTERNET_NAME", "www.example.com"),
            ev("IP_ADDRESS", "203.0.113.9", source="www.example.com"),
            ev("IP_ADDRESS", "203.0.113.10", source="example.com"),
        ]
    )
    assert sorted(o.value for o in r.objects if o.type == "ipv4-addr") == [
        "203.0.113.10",
        "203.0.113.9",
    ]
    assert len([o for o in r.objects if o.type == "relationship"]) == 3  # www related + 2 resolves


def test_flagged_affiliate_hostname_is_counted_as_not_imported():
    r = run(
        [
            ev("AFFILIATE_INTERNET_NAME", "bad.partner.net"),
            ev("MALICIOUS_INTERNET_NAME", "Comodo Secure DNS [bad.partner.net]"),
        ]
    )
    assert "bad.partner.net" not in domains(r)
    assert r.name_flags_skipped == 1


def test_event_sets_no_longer_include_affiliate_names():
    assert DOMAIN_EVENTS == {"INTERNET_NAME"}
    assert "AFFILIATE_INTERNET_NAME" not in IMPORTED_EVENTS
