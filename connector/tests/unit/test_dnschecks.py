from spiderfoot_connector.dnschecks import (
    DnsFacts,
    check_domain,
    dmarc_policy,
    spf_all_qualifier,
)

# lookup(name, rdtype) -> list of text records; [] = confirmed absent; None = unknown


def fake(records):
    def lookup(name, rdtype):
        return records.get((name, rdtype), [])

    return lookup


FULL = {
    ("example.com", "MX"): ["10 mx1.mail.example.", "20 mx2.mail.example."],
    ("example.com", "TXT"): [
        "v=spf1 include:_spf.mail.example -all",
        "google-site-verification=abc",
    ],
    ("_dmarc.example.com", "TXT"): ["v=DMARC1; p=reject; rua=mailto:d@example.com"],
    ("example.com", "CAA"): ['0 issue "letsencrypt.org"'],
    ("example.com", "DS"): ["12345 13 2 ABCDEF"],
    ("_mta-sts.example.com", "TXT"): ["v=STSv1; id=2026"],
}


def test_everything_present_is_reported_with_values():
    f = check_domain("example.com", fake(FULL))
    assert f.mx == ["mx1.mail.example", "mx2.mail.example"]
    assert f.spf == "v=spf1 include:_spf.mail.example -all"
    assert f.dmarc == "v=DMARC1; p=reject; rua=mailto:d@example.com"
    assert f.caa == ['0 issue "letsencrypt.org"']
    assert f.ds == ["12345 13 2 ABCDEF"]
    assert f.mta_sts == "v=STSv1; id=2026"


def test_null_mx_means_the_domain_accepts_no_mail():
    # RFC 7505: "0 ." (seen on example.com) declares that the domain does not receive mail
    f = check_domain("example.com", fake({("example.com", "MX"): ["0 ."]}))
    assert f.mx == []


def test_null_mx_next_to_real_hosts_keeps_only_the_real_ones():
    f = check_domain("example.com", fake({("example.com", "MX"): ["0 .", "10 mx.mail.example."]}))
    assert f.mx == ["mx.mail.example"]


def test_everything_absent_is_confirmed_absent_not_unknown():
    f = check_domain("example.com", fake({}))
    assert f == DnsFacts(mx=[], spf="", dmarc="", caa=[], ds=[], mta_sts="")


def test_txt_answers_without_the_record_count_as_absent():
    f = check_domain(
        "example.com",
        fake(
            {("example.com", "TXT"): ["hello"], ("_dmarc.example.com", "TXT"): ["something else"]}
        ),
    )
    assert f.spf == "" and f.dmarc == "" and f.mta_sts == ""


def test_resolver_failures_are_unknown_never_absent():
    def failing(name, rdtype):
        return None

    f = check_domain("example.com", failing)
    assert f == DnsFacts(mx=None, spf=None, dmarc=None, caa=None, ds=None, mta_sts=None)


def test_unknown_for_one_record_does_not_hide_the_others():
    def lookup(name, rdtype):
        return (
            None
            if (name, rdtype) == ("_dmarc.example.com", "TXT")
            else FULL.get((name, rdtype), [])
        )

    f = check_domain("example.com", lookup)
    assert f.dmarc is None and f.spf and f.mx


def test_spf_picks_the_spf_record_among_other_txt_records():
    f = check_domain("example.com", fake({("example.com", "TXT"): ["x", "V=SPF1 -all", "y"]}))
    assert f.spf == "V=SPF1 -all"


def test_spf_qualifier():
    assert spf_all_qualifier("v=spf1 include:a -all") == "-all"
    assert spf_all_qualifier("v=spf1 ~all") == "~all"
    assert spf_all_qualifier("v=spf1 +all") == "+all"
    assert spf_all_qualifier("v=spf1 all") == "+all"  # no qualifier means pass
    assert spf_all_qualifier("v=spf1 ?all") == "?all"
    assert spf_all_qualifier("v=spf1 include:a") is None


def test_dmarc_policy():
    assert dmarc_policy("v=DMARC1; p=reject; rua=mailto:x@y") == "reject"
    assert dmarc_policy("v=DMARC1;p=none") == "none"
    assert dmarc_policy("v=DMARC1; sp=reject; p=quarantine") == "quarantine"
    assert dmarc_policy("v=DMARC1; rua=mailto:x@y") is None


def test_only_the_expected_names_are_queried():
    seen = []

    def lookup(name, rdtype):
        seen.append((name, rdtype))
        return []

    check_domain("www.example.com", lookup)
    assert sorted(seen) == sorted(
        [
            ("www.example.com", "MX"),
            ("www.example.com", "TXT"),
            ("_dmarc.www.example.com", "TXT"),
            ("www.example.com", "CAA"),
            ("www.example.com", "DS"),
            ("_mta-sts.www.example.com", "TXT"),
        ]
    )
