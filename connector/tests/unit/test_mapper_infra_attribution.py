from datetime import UTC, datetime

from spiderfoot_connector.mapper import map_events

NOW = datetime(2026, 10, 4, 6, 0, 0, tzinfo=UTC)


def run(events, target="example.com"):
    return map_events(events, target=target, scan_id="S1", score=30, now=NOW)


def ev(etype, data, source="example.com", module="sfp_x"):
    return {
        "event_type": etype,
        "data": data,
        "source_data": source,
        "module": module,
        "false_positive": 0,
    }


def note(result):
    (n,) = [o for o in result.objects if o.type == "note"]
    return n.content


def infra(result):
    found = [ln for ln in note(result).splitlines() if ln.startswith("Infrastructure")]
    return found[0] if found else ""


# Real case (bugoverflow.com): the scan also resolves a provider's domain; its MX, name servers and
# registrar come back as events whose source is that provider, not the target.


def test_mail_host_of_a_third_party_domain_is_not_the_targets():
    r = run([ev("PROVIDER_MAIL", "mail.provider.net", source="provider.net")])
    assert "mail:" not in infra(r)
    assert r.unmapped["PROVIDER_MAIL (not the target's)"] == 1
    assert not r.infra


def test_name_servers_of_a_third_party_domain_are_not_the_targets():
    r = run(
        [
            ev("PROVIDER_DNS", "ns1.example.net", source="example.com"),
            ev("PROVIDER_DNS", "ns9.other.net", source="provider.net"),
        ]
    )
    assert "ns1.example.net" in infra(r) and "ns9.other.net" not in infra(r)
    assert r.unmapped["PROVIDER_DNS (not the target's)"] == 1


def test_registrar_of_a_third_party_domain_is_not_the_targets():
    r = run(
        [
            ev("DOMAIN_REGISTRAR", "Other Registrar", source="provider.net"),
            ev("DOMAIN_REGISTRAR", "Example Registrar", source="example.com"),
        ]
    )
    assert "registrar: Example Registrar" in infra(r) and "Other Registrar" not in infra(r)


def test_parent_domain_records_count_for_a_subdomain_target_but_siblings_do_not():
    own = run([ev("PROVIDER_MAIL", "mx.example.net", source="example.com")], "www.example.com")
    sibling = run(
        [ev("PROVIDER_MAIL", "mx.example.net", source="api.example.com")], "www.example.com"
    )
    assert "mail: mx.example.net" in infra(own)
    assert not sibling.infra


def test_hosting_counts_only_for_an_ip_that_was_imported_for_the_target():
    r = run(
        [
            ev("INTERNET_NAME", "www.example.com"),
            ev("IP_ADDRESS", "203.0.113.9", source="www.example.com"),
            ev("PROVIDER_HOSTING", "examplehost: https://www.example.net/", source="203.0.113.9"),
            ev("PROVIDER_HOSTING", "foreignhost: https://www.foreign.net/", source="198.51.100.7"),
        ]
    )
    assert "hosting: examplehost" in infra(r) and "foreignhost" not in infra(r)
    assert r.unmapped["PROVIDER_HOSTING (not the target's)"] == 1


def test_hosting_event_order_does_not_matter():
    events = [
        ev("PROVIDER_HOSTING", "examplehost: https://www.example.net/", source="203.0.113.9"),
        ev("IP_ADDRESS", "203.0.113.9", source="example.com"),
    ]
    assert "hosting: examplehost" in infra(run(events))
    assert "hosting: examplehost" in infra(run(list(reversed(events))))


def test_third_party_mail_does_not_trigger_the_mail_without_spf_finding():
    r = run(
        [
            ev("PROVIDER_MAIL", "mail.provider.net", source="provider.net"),
            ev("RAW_DNS_RECORDS", "example.com. 300 IN NS ns1.example.net."),
        ]
    )
    assert "receives mail" not in note(r)
