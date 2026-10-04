from datetime import UTC, datetime

from spiderfoot_connector.mapper import IMPORTED_EVENTS, map_events

NOW = datetime(2026, 10, 4, 6, 0, 0, tzinfo=UTC)
LABEL = "spiderfoot:malicious"


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


def objs(result, type_):
    return [o for o in result.objects if o.type == type_]


def domain(result, value):
    (found,) = [o for o in objs(result, "domain-name") if o.value == value]
    return found


def note(result):
    (n,) = objs(result, "note")
    return n.content


def labels(obj):
    return list(getattr(obj, "x_opencti_labels", []))


def refs(obj):
    return list(getattr(obj, "x_opencti_external_references", []))


# --- flagged hostnames ---


def test_flagged_imported_hostname_gets_label_and_feed_reference():
    r = run(
        [
            ev("INTERNET_NAME", "www.example.com", module="sfp_crt"),
            ev(
                "MALICIOUS_INTERNET_NAME",
                "Comodo Secure DNS [www.example.com]",
                module="sfp_comodo",
            ),
        ]
    )
    d = domain(r, "www.example.com")
    assert labels(d) == [LABEL]
    flag_refs = [x for x in refs(d) if x["source_name"] == "Comodo Secure DNS"]
    assert len(flag_refs) == 1
    assert flag_refs[0]["external_id"] == "S1"
    assert "sfp_comodo" in flag_refs[0]["description"]


def test_label_is_applied_regardless_of_event_order():
    flag = ev("MALICIOUS_INTERNET_NAME", "Comodo Secure DNS [www.example.com]")
    name = ev("INTERNET_NAME", "www.example.com")
    assert labels(domain(run([flag, name]), "www.example.com")) == [LABEL]
    assert labels(domain(run([name, flag]), "www.example.com")) == [LABEL]


def test_two_feeds_give_one_label_and_two_references():
    r = run(
        [
            ev("INTERNET_NAME", "www.example.com"),
            ev("MALICIOUS_INTERNET_NAME", "Comodo Secure DNS [www.example.com]"),
            ev("MALICIOUS_INTERNET_NAME", "OpenDNS [www.example.com]", module="sfp_opendns"),
        ]
    )
    d = domain(r, "www.example.com")
    assert labels(d) == [LABEL]
    assert sorted(x["source_name"] for x in refs(d) if "Flagged" in x["description"]) == [
        "Comodo Secure DNS",
        "OpenDNS",
    ]


def test_hostname_match_is_case_and_trailing_dot_insensitive():
    r = run(
        [
            ev("INTERNET_NAME", "WWW.Example.com."),
            ev("MALICIOUS_INTERNET_NAME", "Comodo Secure DNS [www.example.com]"),
        ]
    )
    assert labels(domain(r, "www.example.com")) == [LABEL]


def test_flagged_target_is_labelled_in_place_without_a_score():
    r = run([ev("MALICIOUS_INTERNET_NAME", "Comodo Secure DNS [example.com]")])
    t = domain(r, "example.com")
    assert labels(t) == [LABEL]
    assert not hasattr(t, "x_opencti_score")


def test_unflagged_target_stays_plain():
    t = domain(run([ev("INTERNET_NAME", "www.example.com")]), "example.com")
    assert labels(t) == []


def test_flagged_hostname_not_in_import_is_counted_never_imported():
    r = run(
        [
            ev("INTERNET_NAME", "www.example.com"),
            ev("MALICIOUS_INTERNET_NAME", "Comodo Secure DNS [elsewhere.example.net]"),
        ]
    )
    assert "elsewhere.example.net" not in {o.value for o in objs(r, "domain-name")}
    assert r.name_flags_skipped == 1
    assert "Malicious flags on hostnames not in this import: 1" in note(r)


def test_unparsable_or_invalid_flagged_hostname_counts_as_invalid():
    r = run(
        [
            ev("MALICIOUS_INTERNET_NAME", "no brackets"),
            ev("MALICIOUS_INTERNET_NAME", "Comodo Secure DNS [not a domain]"),
        ]
    )
    assert r.invalid == 2
    assert r.name_flags_skipped == 0


def test_blacklisted_events_are_not_treated_as_malicious():
    # sfp_cloudflaredns emits BLACKLISTED_* for its content ("Family") filter, not for malware.
    r = run(
        [
            ev("INTERNET_NAME", "www.example.com"),
            ev("BLACKLISTED_INTERNET_NAME", "CloudFlare - Family [www.example.com]"),
        ]
    )
    assert labels(domain(r, "www.example.com")) == []
    assert r.unmapped["BLACKLISTED_INTERNET_NAME"] == 1


# --- infrastructure providers ---


def infra_line(result):
    (line,) = [ln for ln in note(result).splitlines() if ln.startswith("Infrastructure")]
    return line


def test_infrastructure_line_collects_registrar_hosting_dns_and_mail():
    r = run(
        [
            ev("DOMAIN_REGISTRAR", "Example Registrar Ltd."),
            ev("PROVIDER_HOSTING", "examplehost: https://www.example.net/"),
            ev("PROVIDER_DNS", "NS2.example.net."),
            ev("PROVIDER_DNS", "ns1.example.net"),
            ev("PROVIDER_MAIL", "mail.example.net"),
        ]
    )
    line = infra_line(r)
    assert "registrar: Example Registrar Ltd." in line
    assert "hosting: examplehost" in line and "https" not in line
    assert "DNS: ns1.example.net, ns2.example.net" in line
    assert "mail: mail.example.net" in line


def test_infrastructure_values_are_deduplicated_and_sorted():
    r = run(
        [
            ev("PROVIDER_DNS", "ns2.example.net"),
            ev("PROVIDER_DNS", "ns1.example.net"),
            ev("PROVIDER_DNS", "NS1.example.net"),
        ]
    )
    assert infra_line(r).count("ns1.example.net") == 1
    assert infra_line(r).index("ns1.example.net") < infra_line(r).index("ns2.example.net")


def test_infrastructure_values_are_capped_with_a_remainder():
    r = run([ev("PROVIDER_DNS", f"ns{i}.example.net") for i in range(8)])
    line = infra_line(r)
    assert "ns0.example.net" in line and "ns4.example.net" in line
    assert "ns5.example.net" not in line
    assert "and 3 more" in line


def test_no_infrastructure_events_means_no_infrastructure_line():
    assert "Infrastructure" not in note(run([ev("INTERNET_NAME", "www.example.com")]))


def test_empty_infrastructure_value_counts_as_invalid():
    r = run([ev("PROVIDER_DNS", "   "), ev("DOMAIN_REGISTRAR", "")])
    assert r.invalid == 2
    assert "Infrastructure" not in note(r)


def test_infrastructure_events_are_no_longer_reported_as_unmapped():
    r = run(
        [
            ev("DOMAIN_REGISTRAR", "Example Registrar Ltd."),
            ev("PROVIDER_HOSTING", "examplehost: https://www.example.net/"),
            ev("PROVIDER_DNS", "ns1.example.net"),
            ev("PROVIDER_MAIL", "mail.example.net"),
            ev("PUBLIC_CODE_REPO", "Name: x\nURL: https://github.com/someone/x"),
        ]
    )
    assert set(r.unmapped) == {"PUBLIC_CODE_REPO"}


def test_infrastructure_creates_no_objects_beyond_the_baseline():
    base = run([ev("INTERNET_NAME", "www.example.com")])
    more = run(
        [
            ev("INTERNET_NAME", "www.example.com"),
            ev("DOMAIN_REGISTRAR", "Example Registrar Ltd."),
            ev("PROVIDER_DNS", "ns1.example.net"),
        ]
    )
    assert {o.id for o in more.objects if o.type != "note"} == {
        o.id for o in base.objects if o.type != "note"
    }


# --- regression and bookkeeping ---


def test_new_event_types_are_declared_as_imported():
    assert {
        "MALICIOUS_INTERNET_NAME",
        "DOMAIN_REGISTRAR",
        "PROVIDER_HOSTING",
        "PROVIDER_DNS",
        "PROVIDER_MAIL",
    } <= IMPORTED_EVENTS
    assert "BLACKLISTED_INTERNET_NAME" not in IMPORTED_EVENTS


def test_output_is_deterministic():
    events = [
        ev("INTERNET_NAME", "www.example.com"),
        ev("MALICIOUS_INTERNET_NAME", "Comodo Secure DNS [www.example.com]"),
        ev("PROVIDER_DNS", "ns1.example.net"),
    ]
    a, b = run(events), run(list(reversed(events)))
    assert sorted(o.id for o in a.objects) == sorted(o.id for o in b.objects)
    assert note(a) == note(b)
