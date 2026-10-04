from datetime import UTC, datetime

from spiderfoot_connector.mapper import map_events
from spiderfoot_connector.profiles import SUBDOMAIN_SOURCES, lean_modules, load_snapshot

NOW = datetime(2026, 10, 4, 6, 0, 0, tzinfo=UTC)


def ev(etype, data, source="example.com", module="sfp_x"):
    return {
        "event_type": etype,
        "data": data,
        "source_data": source,
        "module": module,
        "false_positive": 0,
    }


def run(events, errors=(), target="example.com"):
    return map_events(
        events,
        target=target,
        scan_id="S1",
        score=30,
        now=NOW,
        source_errors=errors,
        subdomain_sources=SUBDOMAIN_SOURCES,
    )


def note(result):
    (n,) = [o for o in result.objects if o.type == "note"]
    return n.content


def findings(result):
    lines = note(result).splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("Key findings"))
    if not lines[start].endswith(":"):
        return lines[start], []
    out = []
    for ln in lines[start + 1 :]:
        if not ln.startswith("- "):
            break
        out.append(ln[2:])
    return lines[start], out


def cert(
    cn="example.com",
    not_after="Dec 26 10:28:56 2026 GMT",
    not_before="Sep 27 09:29:10 2026 GMT",
    serial="17:db:50:1d",
):
    return (
        f"Certificate:\n    Data:\n        Serial Number:\n            {serial}\n"
        "        Issuer: C=US, O=Example Trust, CN=WE1\n        Validity\n"
        f"            Not Before: {not_before}\n            Not After : {not_after}\n"
        f"        Subject: CN={cn}\n"
    )


WHOIS = "Creation Date: {c}T00:00:00Z\nRegistry Expiry Date: {e}T00:00:00Z\n"


def mail_events(spf=None):
    out = [
        ev("PROVIDER_MAIL", "mx1.mail.example"),
        ev("RAW_DNS_RECORDS", "example.com. 300 IN MX 10 mx1.mail.example."),
    ]
    if spf:
        out.append(ev("DNS_TEXT", spf))
    return out


# --- ordering, wording, neutrality ---


def test_nothing_notable_is_stated_without_claiming_a_clean_bill_of_health():
    head, items = findings(run([ev("INTERNET_NAME", "www.example.com")]))
    assert items == []
    assert head == "Key findings: nothing notable in the data the answering sources returned."
    assert "clean" not in head.lower()


def test_block_is_the_second_line_of_the_note():
    r = run([ev("DOMAIN_WHOIS", WHOIS.format(c="2026-09-27", e="2027-09-27"))])
    lines = note(r).splitlines()
    assert lines[0].startswith("SpiderFoot scan S1")
    assert lines[1] == "Key findings (as of this scan):"


# --- individual findings ---


def test_newly_registered_domain():
    _, items = findings(run([ev("DOMAIN_WHOIS", WHOIS.format(c="2026-09-27", e="2027-09-27"))]))
    assert items == ["registered 7 days ago (2026-09-27)"]


def test_registration_age_boundary_is_thirty_days():
    old = WHOIS.format(c="2026-09-04", e="2027-09-04")  # 30 days
    assert findings(run([ev("DOMAIN_WHOIS", old)]))[1] == []
    new = WHOIS.format(c="2026-09-05", e="2027-09-05")  # 29 days
    assert len(findings(run([ev("DOMAIN_WHOIS", new)]))[1]) == 1


def test_registration_expiring_soon_and_not_when_far():
    _, soon = findings(run([ev("DOMAIN_WHOIS", WHOIS.format(c="2020-01-01", e="2026-10-20"))]))
    assert soon == ["registration expires in 16 days (2026-10-20)"]
    assert (
        findings(run([ev("DOMAIN_WHOIS", WHOIS.format(c="2020-01-01", e="2027-10-20"))]))[1] == []
    )


def test_expired_registration_is_reported():
    _, items = findings(run([ev("DOMAIN_WHOIS", WHOIS.format(c="2020-01-01", e="2026-09-01"))]))
    assert items == ["registration expired on 2026-09-01"]


def test_only_the_newest_certificate_per_cn_is_judged():
    old_expired = cert(
        not_before="Sep 27 09:29:10 2024 GMT", not_after="Sep 01 00:00:00 2025 GMT", serial="11:11"
    )
    healthy_new = cert(serial="99:99")
    # same CN, newer and healthy: the old expired one is rotation history, not a finding
    events = [ev("SSL_CERTIFICATE_RAW", old_expired), ev("SSL_CERTIFICATE_RAW", healthy_new)]
    assert findings(run(events))[1] == []


def test_the_newest_certificate_being_expired_is_a_finding():
    older = cert(
        not_before="Sep 27 09:29:10 2024 GMT", not_after="Sep 01 00:00:00 2025 GMT", serial="11:11"
    )
    newest = cert(not_after="Sep 01 00:00:00 2026 GMT", serial="99:99")
    events = [ev("SSL_CERTIFICATE_RAW", older), ev("SSL_CERTIFICATE_RAW", newest)]
    assert findings(run(events))[1] == ["certificate for example.com expired on 2026-09-01"]


def test_each_cn_is_judged_on_its_own_newest_certificate():
    a = cert(cn="a.example.com", not_after="Sep 01 00:00:00 2026 GMT", serial="aa:aa")
    b = cert(cn="b.example.com", serial="bb:bb")
    got = findings(run([ev("SSL_CERTIFICATE_RAW", a), ev("SSL_CERTIFICATE_RAW", b)]))[1]
    assert got == ["certificate for a.example.com expired on 2026-09-01"]


def test_certificate_expired_and_expiring_and_healthy():
    expired = findings(
        run([ev("SSL_CERTIFICATE_RAW", cert(not_after="Sep 01 00:00:00 2026 GMT"))])
    )[1]
    assert expired == ["certificate for example.com expired on 2026-09-01"]
    soon = findings(run([ev("SSL_CERTIFICATE_RAW", cert(not_after="Oct 10 00:00:00 2026 GMT"))]))[1]
    assert soon == ["certificate for example.com expires in 6 days (2026-10-10)"]
    assert findings(run([ev("SSL_CERTIFICATE_RAW", cert())]))[1] == []


def test_flagged_hostnames_and_ips_are_listed_with_their_feeds():
    r = run(
        [
            ev("INTERNET_NAME", "www.example.com"),
            ev("MALICIOUS_INTERNET_NAME", "Comodo Secure DNS [www.example.com]"),
            ev("IP_ADDRESS", "203.0.113.9", source="www.example.com"),
            ev("MALICIOUS_IPADDR", "Maltiverse [203.0.113.9]"),
        ]
    )
    (item,) = findings(r)[1]
    assert item.startswith("2 hostnames/IPs flagged malicious (Comodo Secure DNS, Maltiverse): ")
    assert "203.0.113.9" in item and "www.example.com" in item


def test_a_flag_on_a_host_that_is_not_imported_is_not_a_finding():
    r = run([ev("MALICIOUS_INTERNET_NAME", "Comodo Secure DNS [elsewhere.example.net]")])
    assert findings(r)[1] == []


def test_listings_on_shared_infrastructure_are_counted_and_labelled_as_not_the_targets():
    r = run(
        [
            ev("MALICIOUS_SUBNET", "VoIP Blacklist (VoIPBL) [203.0.113.0/24]"),
            ev("MALICIOUS_COHOST", "Comodo Secure DNS [other.example.net]"),
        ]
    )
    assert findings(r)[1] == [
        "2 reputation listings on shared infrastructure (not the target's own)"
    ]


# --- mail without SPF ---


def test_mail_without_spf_is_reported_when_dns_answered():
    (item,) = findings(run(mail_events()))[1]
    assert item.startswith("receives mail (MX: mx1.mail.example) but publishes no SPF record")
    assert "DMARC is not checked" in item


def test_spf_present_means_no_finding():
    assert findings(run(mail_events(spf="v=spf1 include:_spf.mail.example ~all")))[1] == []


def test_no_mail_hosts_means_no_spf_finding():
    assert (
        findings(run([ev("RAW_DNS_RECORDS", "example.com. 300 IN NS ns1.example.net.")]))[1] == []
    )


def test_no_dns_answer_for_the_target_means_no_spf_finding():
    assert findings(run([ev("PROVIDER_MAIL", "mx1.mail.example")]))[1] == []


def test_mail_fallback_ignores_parent_domain_records_for_a_subdomain_target():
    events = [
        ev("PROVIDER_MAIL", "mx1.mail.example", source="example.com"),
        ev("RAW_DNS_RECORDS", "example.com. 300 IN MX 10 mx1.mail.example.", source="example.com"),
    ]
    assert findings(run(events, target="www.example.com"))[1] == []


def test_mail_fallback_uses_records_of_the_scanned_name_itself():
    events = [
        ev("PROVIDER_MAIL", "mx1.mail.example", source="www.example.com"),
        ev(
            "RAW_DNS_RECORDS",
            "www.example.com. 300 IN MX 10 mx1.mail.example.",
            source="www.example.com",
        ),
    ]
    assert len(findings(run(events, target="www.example.com"))[1]) == 1


def test_raw_dns_of_a_third_party_does_not_count_as_the_targets_answer():
    events = [
        ev("PROVIDER_MAIL", "mx1.mail.example"),
        ev("RAW_DNS_RECORDS", "other.net. 300 IN MX 10 mx.other.net.", source="other.net"),
    ]
    assert findings(run(events))[1] == []


def test_findings_never_claim_dmarc_or_dkim_absence():
    text = note(run(mail_events()))
    assert "no DMARC" not in text and "DKIM" not in text


# --- coverage ---


def test_failing_subdomain_sources_produce_a_coverage_warning():
    errors = [
        ("sfp_sublist3r", "Bad response"),
        ("sfp_crobat_api", "Failed"),
        ("sfp_flickr", "no key"),
    ]
    (item,) = findings(run([], errors))[1]
    assert item == (
        "subdomain discovery may be incomplete: sfp_crobat_api, sfp_sublist3r reported errors "
        "(sfp_crt does not report outages)"
    )


def test_errors_in_unrelated_modules_are_not_a_coverage_warning():
    assert findings(run([], [("sfp_flickr", "no key"), ("sfp_koodous", "404")]))[1] == []


# --- ordering and bookkeeping ---


def test_findings_are_ordered_flagged_first_then_mail_then_certificate_then_registration():
    events = [
        ev("INTERNET_NAME", "www.example.com"),
        ev("MALICIOUS_INTERNET_NAME", "Comodo Secure DNS [www.example.com]"),
        ev("DOMAIN_WHOIS", WHOIS.format(c="2026-09-27", e="2027-09-27")),
        ev("SSL_CERTIFICATE_RAW", cert(not_after="Sep 01 00:00:00 2026 GMT")),
        *mail_events(),
    ]
    order = [item.split(" ", 1)[0] for item in findings(run(events))[1]]
    assert order == ["1", "receives", "certificate", "registered"]


def test_findings_change_no_objects_and_are_deterministic():
    base = {o.id for o in run([ev("INTERNET_NAME", "www.example.com")]).objects if o.type != "note"}
    events = [ev("INTERNET_NAME", "www.example.com"), *mail_events()]
    more = run(events)
    assert base <= {o.id for o in more.objects}
    assert note(more) == note(run(list(reversed(events))))


def test_subdomain_sources_are_real_lean_modules_that_produce_hostnames():
    snapshot, lean = load_snapshot(), set(lean_modules())
    for name in SUBDOMAIN_SOURCES:
        assert name in lean, name
        assert "INTERNET_NAME" in snapshot[name]["produced"], name
