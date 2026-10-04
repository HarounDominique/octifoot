from datetime import UTC, datetime

from spiderfoot_connector.dnschecks import DnsFacts
from spiderfoot_connector.mapper import map_events
from spiderfoot_connector.profiles import SUBDOMAIN_SOURCES

NOW = datetime(2026, 10, 4, 6, 0, 0, tzinfo=UTC)
MAIL = ["mx1.mail.example"]


def facts(**kw):
    base = {
        "mx": MAIL,
        "spf": "v=spf1 -all",
        "dmarc": "v=DMARC1; p=reject",
        "caa": [],
        "ds": [],
        "mta_sts": "",
    }
    return DnsFacts(**{**base, **kw})


def ev(etype, data, source="example.com"):
    return {
        "event_type": etype,
        "data": data,
        "source_data": source,
        "module": "sfp_x",
        "false_positive": 0,
    }


def run(dns=None, events=(), errors=()):
    return map_events(
        list(events),
        target="example.com",
        scan_id="S1",
        score=30,
        now=NOW,
        source_errors=errors,
        subdomain_sources=SUBDOMAIN_SOURCES,
        dns_facts=dns,
    )


def note(result):
    (n,) = [o for o in result.objects if o.type == "note"]
    return n.content


def items(result):
    lines = note(result).splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("Key findings"))
    out = []
    for ln in lines[start + 1 :]:
        if not ln.startswith("- "):
            break
        out.append(ln[2:])
    return out


def dns_line(result):
    found = [ln for ln in note(result).splitlines() if ln.startswith("DNS checks")]
    return found[0] if found else ""


# --- the Note line ---


def test_no_facts_means_no_line():
    assert dns_line(run(None)) == ""


def test_line_reports_every_record_with_its_state():
    line = dns_line(
        run(
            facts(
                caa=['0 issue "letsencrypt.org"'],
                ds=["1 13 2 AB"],
                mta_sts="v=STSv1; id=1",
            )
        )
    )
    assert line.startswith("DNS checks (queried by octifoot, not by SpiderFoot):")
    assert "MX: mx1.mail.example" in line
    assert "SPF: v=spf1 -all" in line
    assert "DMARC: p=reject" in line
    assert "CAA: 1 record" in line
    assert "DNSSEC: DS record present" in line
    assert "MTA-STS: present" in line


def test_absent_records_are_stated_as_none():
    line = dns_line(run(DnsFacts(mx=[], spf="", dmarc="", caa=[], ds=[], mta_sts="")))
    for part in (
        "MX: none",
        "SPF: none",
        "DMARC: none",
        "CAA: none",
        "DNSSEC: no DS record",
        "MTA-STS: none",
    ):
        assert part in line, part


def test_unknown_is_never_written_as_none():
    line = dns_line(run(DnsFacts(mx=None, spf=None, dmarc=None, caa=None, ds=None, mta_sts=None)))
    assert line.count("unknown") == 6 and "none" not in line


def test_dmarc_without_a_policy_tag_is_shown_as_present():
    assert "DMARC: present (no p= policy)" in dns_line(run(facts(dmarc="v=DMARC1; rua=mailto:x@y")))


def test_long_spf_is_capped_in_the_line():
    line = dns_line(run(facts(spf="v=spf1 " + "ip4:192.0.2.1 " * 40 + "-all")))
    assert len(line.split("SPF: ", 1)[1].split("; DMARC")[0]) <= 160


# --- findings from native facts ---


def test_healthy_mail_domain_has_no_mail_finding():
    assert items(run(facts())) == []


def test_mail_without_spf_and_without_dmarc():
    got = items(run(facts(spf="", dmarc="")))
    assert "receives mail (MX: mx1.mail.example) but publishes no SPF record" in got
    assert "receives mail but publishes no DMARC record at _dmarc.example.com" in got


def test_dmarc_policy_none_is_called_out():
    assert items(run(facts(dmarc="v=DMARC1; p=none"))) == [
        "DMARC policy is p=none (spoofed mail is only monitored, not rejected)"
    ]


def test_permissive_spf_is_called_out_but_soft_fail_is_not():
    assert items(run(facts(spf="v=spf1 +all"))) == [
        "SPF ends in +all: it does not restrict senders"
    ]
    assert items(run(facts(spf="v=spf1 ?all"))) == [
        "SPF ends in ?all: it does not restrict senders"
    ]
    assert items(run(facts(spf="v=spf1 include:a ~all"))) == []


def test_a_name_without_mx_gets_no_mail_findings_even_if_spiderfoot_saw_mail_events():
    events = [
        ev("PROVIDER_MAIL", "mx.example.net"),
        ev("RAW_DNS_RECORDS", "example.com. 1 IN NS ns.example.net."),
    ]
    assert items(run(facts(mx=[], spf="", dmarc=""), events)) == []


def test_unknown_spf_or_dmarc_produces_no_claim():
    assert items(run(facts(spf=None, dmarc=None))) == []


def test_native_facts_replace_the_event_based_spf_inference():
    events = [
        ev("PROVIDER_MAIL", "mx.example.net"),
        ev("RAW_DNS_RECORDS", "example.com. 1 IN NS ns.example.net."),
    ]
    # SpiderFoot saw no SPF, but the direct query found one: no finding
    assert items(run(facts(spf="v=spf1 -all"), events)) == []


def test_when_the_mx_lookup_failed_the_earlier_inference_still_applies_with_its_disclaimer():
    events = [
        ev("PROVIDER_MAIL", "mx.example.net"),
        ev("RAW_DNS_RECORDS", "example.com. 1 IN NS ns.example.net."),
    ]
    got = items(run(facts(mx=None, spf=None, dmarc=None), events))
    assert len(got) == 1 and "DMARC is not checked by SpiderFoot" in got[0]


def test_dns_facts_change_no_objects():
    base = {o.id for o in run(None).objects if o.type != "note"}
    assert base == {o.id for o in run(facts(spf="", dmarc="")).objects if o.type != "note"}
