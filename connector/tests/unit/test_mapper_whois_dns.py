from datetime import UTC, datetime

from spiderfoot_connector.mapper import IMPORTED_EVENTS, map_events

NOW = datetime(2026, 10, 4, 6, 0, 0, tzinfo=UTC)

WHOIS = (
    "   Domain Name: EXAMPLE.COM\r\n"
    "   Registry Domain ID: 123_DOMAIN_COM-VRSN\r\n"
    "   Registrar WHOIS Server: whois.registrar.example\r\n"
    "   Updated Date: 2026-03-18T06:14:24Z\r\n"
    "   Creation Date: 2025-03-25T11:36:17Z\r\n"
    "   Registry Expiry Date: 2027-03-25T11:36:17Z\r\n"
    "   Registrar: Example Registrar Ltd.\r\n"
    "   Registrar Abuse Contact Email: abuse@registrar.example\r\n"
    "   Registrar Abuse Contact Phone: +00.1234567\r\n"
    "   Domain Status: clientDeleteProhibited https://icann.org/epp#clientDeleteProhibited\r\n"
    "   Domain Status: clientTransferProhibited https://icann.org/epp#clientTransferProhibited\r\n"
    "   Registrant Name: Jane Roe\r\n"
    "   Registrant Email: jane@example.net\r\n"
    "   Name Server: NS1.EXAMPLE.NET\r\n"
    "   DNSSEC: unsigned\r\n"
)


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


def line(result, prefix):
    found = [ln for ln in note(result).splitlines() if ln.startswith(prefix)]
    assert len(found) == 1, note(result)
    return found[0]


# --- WHOIS ---


def test_whois_line_has_dates_age_status_and_dnssec():
    out = line(run([ev("DOMAIN_WHOIS", WHOIS)]), "WHOIS (as reported by SpiderFoot)")
    assert "created 2025-03-25 (558 days before this scan)" in out
    assert "updated 2026-03-18" in out
    assert "expires 2027-03-25" in out
    assert "status: clientDeleteProhibited, clientTransferProhibited" in out
    assert "DNSSEC: unsigned" in out
    assert "icann.org" not in out


def test_no_registrant_or_contact_data_reaches_the_note():
    text = note(run([ev("DOMAIN_WHOIS", WHOIS)]))
    for leaked in (
        "Jane Roe",
        "jane@example.net",
        "abuse@registrar",
        "+00.1234567",
        "NS1.EXAMPLE.NET",
    ):
        assert leaked not in text, leaked


def test_recently_created_domain_reports_its_age_in_days():
    text = WHOIS.replace(
        "2025-03-25T11:36:17Z\r\n   Registry", "2026-09-27T09:48:08Z\r\n   Registry"
    )
    assert "created 2026-09-27 (7 days before this scan)" in line(
        run([ev("DOMAIN_WHOIS", text)]), "WHOIS"
    )


def test_future_creation_date_omits_the_age():
    text = "Creation Date: 2030-01-01T00:00:00Z\r\n"
    out = line(run([ev("DOMAIN_WHOIS", text)]), "WHOIS")
    assert "created 2030-01-01" in out and "days before" not in out


def test_truncated_text_reports_only_what_parsed():
    out = line(
        run([ev("DOMAIN_WHOIS", "Creation Date: 2020-01-02T00:00:00Z\r\n   Regis")]), "WHOIS"
    )
    assert "created 2020-01-02" in out and "expires" not in out and "status" not in out


def test_alternative_key_names_are_understood():
    out = line(
        run([ev("DOMAIN_WHOIS", "Registered On: 2019-05-06\nExpiry Date: 2029-05-06\n")]), "WHOIS"
    )
    assert "created 2019-05-06" in out and "expires 2029-05-06" in out


def test_several_whois_events_merge_first_wins_per_field():
    a = ev("DOMAIN_WHOIS", "Creation Date: 2020-01-01T00:00:00Z\n")
    b = ev(
        "DOMAIN_WHOIS",
        "Creation Date: 2021-01-01T00:00:00Z\nRegistry Expiry Date: 2030-01-01T00:00:00Z\n",
    )
    out = line(run([a, b]), "WHOIS")
    assert "created 2020-01-01" in out and "expires 2030-01-01" in out


def test_whois_without_dates_or_status_is_invalid_and_adds_no_line():
    r = run([ev("DOMAIN_WHOIS", "Domain Name: EXAMPLE.COM\r\nRegistrar: X\r\n")])
    assert "WHOIS (as reported" not in note(r)
    assert r.invalid == 1


def test_whois_of_a_third_party_domain_is_not_used_and_is_counted():
    r = run([ev("DOMAIN_WHOIS", WHOIS, source="provider.net")])
    assert "WHOIS (as reported" not in note(r)
    assert r.unmapped["DOMAIN_WHOIS (not the target's)"] == 1


def test_whois_of_the_parent_domain_is_used_for_a_subdomain_target():
    r = run([ev("DOMAIN_WHOIS", WHOIS, source="example.com")], target="www.example.com")
    assert "created 2025-03-25" in line(r, "WHOIS")


def test_whois_of_a_sibling_domain_is_not_used():
    r = run([ev("DOMAIN_WHOIS", WHOIS, source="other.example.com")], target="www.example.com")
    assert "WHOIS (as reported" not in note(r)


# --- TXT ---


def txt(*values, source="example.com"):
    return [ev("DNS_TEXT", v, source=source) for v in values]


def test_txt_line_reports_spf_dmarc_verification_and_others():
    out = line(
        run(
            txt(
                "v=spf1 include:_spf.mail.example ~all",
                "v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com",
                "google-site-verification=SECRETTOKEN123",
                "facebook-domain-verification=ANOTHERTOKEN",
                "some arbitrary text",
            )
        ),
        "DNS TXT (as reported by SpiderFoot)",
    )
    assert "SPF: v=spf1 include:_spf.mail.example ~all" in out
    assert "DMARC: p=quarantine" in out
    assert "verification tokens: facebook-domain (1), google (1)" in out
    assert "other records: 1" in out
    assert "SECRETTOKEN123" not in out and "ANOTHERTOKEN" not in out
    assert "dmarc@example.com" not in out


def test_long_spf_is_capped():
    out = line(run(txt("v=spf1 " + "ip4:192.0.2.1 " * 40 + "-all")), "DNS TXT")
    assert len(out.split("SPF: ", 1)[1].split(";")[0]) <= 160


def test_txt_of_a_third_party_zone_is_not_used_and_is_counted():
    r = run(txt("google-site-verification=TOKEN", source="provider.net"))
    assert "DNS TXT (as reported" not in note(r)
    assert r.unmapped["DNS_TEXT (not the target's)"] == 1


def test_txt_with_only_unrecognised_records_reports_the_count_only():
    out = line(run(txt("hello", "world")), "DNS TXT")
    assert out.endswith("other records: 2")


def test_no_whois_or_txt_means_no_lines():
    text = note(run([ev("INTERNET_NAME", "www.example.com")]))
    assert "WHOIS (as reported" not in text and "DNS TXT (as reported" not in text


# --- bookkeeping ---


def test_new_lines_add_no_objects_and_change_no_ids():
    base = {o.id for o in run([ev("INTERNET_NAME", "www.example.com")]).objects if o.type != "note"}
    more = run(
        [ev("INTERNET_NAME", "www.example.com"), ev("DOMAIN_WHOIS", WHOIS), *txt("v=spf1 -all")]
    )
    assert {o.id for o in more.objects if o.type != "note"} == base


def test_output_is_deterministic():
    events = [ev("DOMAIN_WHOIS", WHOIS), *txt("v=spf1 -all", "google-site-verification=T")]
    assert note(run(events)) == note(run(list(reversed(events))))


def test_declared_as_imported_and_web_analytics_id_is_not():
    assert {"DOMAIN_WHOIS", "DNS_TEXT"} <= IMPORTED_EVENTS
    assert "WEB_ANALYTICS_ID" not in IMPORTED_EVENTS
