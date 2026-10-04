import json

from spiderfoot_connector.changes import (
    Snapshot,
    latest_snapshot,
    parse_snapshot,
    render_changes,
)


def snap(**kw):
    base = {
        "scan": "S1",
        "at": "2026-10-04T06:00:00Z",
        "complete": True,
        "hosts": ["www.example.com"],
        "ips": ["203.0.113.1"],
        "emails": [],
        "certs": ["aa:aa"],
        "asn": [64500],
        "registrar": ["Example Registrar"],
        "hosting": ["examplehost"],
        "ns": ["ns1.example.net"],
        "mx": [],
        "spf": None,
        "dmarc": None,
    }
    return Snapshot(**{**base, **kw})


def text(prev, cur, **kw):
    return render_changes("example.com", prev, cur, **kw)


# --- round trip ---


def test_snapshot_survives_a_round_trip_through_note_text():
    s = snap(
        hosts=["a.example.com", "b.example.com"],
        mx=["mx.mail.example"],
        spf="present",
        dmarc="p=none",
    )
    assert parse_snapshot(text(None, s)) == s


def test_parse_ignores_text_without_a_snapshot_or_with_an_unknown_version():
    assert parse_snapshot("just a note") is None
    assert (
        parse_snapshot(
            "Snapshot (machine-readable, used to detect changes at the next scan): {not json"
        )
        is None
    )
    line = "Snapshot (machine-readable, used to detect changes at the next scan): " + json.dumps(
        {"v": 99}
    )
    assert parse_snapshot(line) is None


# --- first snapshot and no change ---


def test_first_snapshot_says_there_is_nothing_to_compare():
    out = text(None, snap())
    assert "First octifoot snapshot of example.com" in out and "nothing to compare" in out
    assert "added" not in out


def test_no_change_is_stated():
    out = text(snap(), snap(scan="S2", at="2026-10-05T06:00:00Z"))
    assert "no changes since the previous scan" in out and "S1" in out


def test_nothing_added_by_an_incomplete_scan_is_not_reported_as_no_changes():
    prev = snap(hosts=["www.example.com", "old.example.com"])
    cur = snap(scan="S2", hosts=["www.example.com"], complete=False)
    out = text(prev, cur)
    assert "no changes since" not in out
    assert (
        "no additions since the previous scan" in out and "disappearances are not assessed" in out
    )


def test_summary_of_an_incomplete_comparison_does_not_say_no_changes():
    from spiderfoot_connector.changes import summarize

    prev = snap()
    assert summarize(prev, snap(scan="S2", complete=False)) == "no additions since 2026-10-04"
    assert summarize(prev, snap(scan="S2")) == "no changes since 2026-10-04"


# --- additions and removals ---


def test_additions_are_listed_per_category():
    prev = snap()
    cur = snap(
        scan="S2",
        hosts=["www.example.com", "api.example.com"],
        ips=["203.0.113.1", "203.0.113.2"],
        emails=["a@example.com"],
        asn=[64500, 64501],
    )
    out = text(prev, cur)
    assert "hostnames added: api.example.com" in out
    assert "IPs added: 203.0.113.2" in out
    assert "emails added: a@example.com" in out
    assert "AS numbers added: 64501" in out


def test_removals_are_listed_as_not_seen_when_both_scans_are_complete():
    prev = snap(hosts=["www.example.com", "old.example.com"], ips=["203.0.113.1", "203.0.113.9"])
    cur = snap(scan="S2", hosts=["www.example.com"], ips=["203.0.113.1"])
    out = text(prev, cur)
    assert "hostnames not seen this time: old.example.com" in out
    assert "IPs not seen this time: 203.0.113.9" in out


def test_removals_are_not_reported_when_the_new_scan_is_incomplete():
    prev = snap(hosts=["www.example.com", "old.example.com"])
    cur = snap(scan="S2", hosts=["www.example.com"], complete=False)
    out = text(prev, cur)
    assert "not seen this time" not in out
    assert "disappearances are not reported" in out and "incomplete" in out


def test_removals_are_not_reported_when_the_previous_scan_was_incomplete():
    prev = snap(hosts=["www.example.com", "old.example.com"], complete=False)
    cur = snap(scan="S2", hosts=["www.example.com"])
    out = text(prev, cur)
    assert "not seen this time" not in out and "disappearances are not reported" in out


def test_additions_against_an_incomplete_previous_scan_carry_a_caveat():
    prev = snap(complete=False)
    cur = snap(scan="S2", hosts=["www.example.com", "api.example.com"])
    out = text(prev, cur)
    assert "hostnames added: api.example.com" in out and "may not be new" in out


def test_not_seen_hostnames_carry_a_caveat_when_subdomain_sources_failed():
    prev = snap(hosts=["www.example.com", "old.example.com"])
    cur = snap(scan="S2", hosts=["www.example.com"])
    out = text(prev, cur, subdomain_sources_failed=True)
    assert (
        "hostnames not seen this time: old.example.com (subdomain sources reported errors: they may not be gone)"
        in out
    )


def test_certificates_report_only_additions():
    prev = snap(certs=["aa:aa", "bb:bb"])
    cur = snap(scan="S2", certs=["aa:aa", "cc:cc"])
    out = text(prev, cur)
    assert "certificates added: 1 (cc:cc)" in out
    assert "bb:bb" not in out


def test_infrastructure_changes_are_reported_both_ways_when_complete():
    prev = snap(
        registrar=["Old Registrar"],
        hosting=["oldhost"],
        ns=["ns1.example.net"],
        mx=["mx1.mail.example"],
    )
    cur = snap(
        scan="S2", registrar=["New Registrar"], hosting=["oldhost"], ns=["ns9.example.net"], mx=[]
    )
    out = text(prev, cur)
    assert "registrar changed: Old Registrar -> New Registrar" in out
    assert (
        "name servers added: ns9.example.net" in out
        and "name servers not seen this time: ns1.example.net" in out
    )
    assert "mail hosts not seen this time: mx1.mail.example" in out


def test_mail_authentication_state_changes_are_reported_only_when_both_are_known():
    out = text(snap(spf="none", dmarc="none"), snap(scan="S2", spf="present", dmarc="p=reject"))
    assert "SPF: none -> present" in out and "DMARC: none -> p=reject" in out
    unknown = text(snap(spf=None, dmarc=None), snap(scan="S2", spf="present", dmarc="p=reject"))
    assert "SPF:" not in unknown and "DMARC:" not in unknown


def test_lists_are_capped():
    cur = snap(scan="S2", hosts=[f"h{i:02d}.example.com" for i in range(15)])
    out = text(snap(hosts=[]), cur).split("Snapshot (")[0]  # the snapshot line keeps the full list
    assert "h09.example.com" in out and "h10.example.com" not in out and "and 5 more" in out


def test_text_is_deterministic_regardless_of_input_order():
    a = snap(scan="S2", hosts=["b.example.com", "a.example.com"])
    b = snap(scan="S2", hosts=["a.example.com", "b.example.com"])
    assert text(snap(hosts=[]), a) == text(snap(hosts=[]), b)


# --- retrieving the previous snapshot ---


def note_row(abstract, content, created):
    return {"node": {"created": created, "attribute_abstract": abstract, "content": content}}


def fake_notes(rows):
    def run(query, variables):
        assert "mutation" not in query
        prefix = variables["prefix"][0]
        return {
            "data": {
                "notes": {
                    "edges": [r for r in rows if r["node"]["attribute_abstract"].startswith(prefix)]
                }
            }
        }

    return run


def test_latest_snapshot_picks_the_newest_matching_note():
    old = text(None, snap(scan="OLD"))
    new = text(None, snap(scan="NEW"))
    rows = [
        note_row("octifoot snapshot for example.com: first", old, "2026-10-01T00:00:00Z"),
        note_row("octifoot snapshot for example.com: later", new, "2026-10-03T00:00:00Z"),
        note_row(
            "octifoot snapshot for other.com: x",
            text(None, snap(scan="OTHER")),
            "2026-10-04T00:00:00Z",
        ),
    ]
    assert latest_snapshot(fake_notes(rows), "example.com").scan == "NEW"


def test_latest_snapshot_skips_notes_it_cannot_read():
    rows = [
        note_row(
            "octifoot snapshot for example.com: a",
            text(None, snap(scan="GOOD")),
            "2026-10-01T00:00:00Z",
        ),
        note_row("octifoot snapshot for example.com: b", "garbled", "2026-10-03T00:00:00Z"),
    ]
    assert latest_snapshot(fake_notes(rows), "example.com").scan == "GOOD"


def test_no_previous_snapshot_returns_none():
    assert latest_snapshot(fake_notes([]), "example.com") is None


def test_the_prefix_cannot_match_a_longer_domain():
    rows = [
        note_row(
            "octifoot snapshot for example.com.evil.net: x",
            text(None, snap(scan="EVIL")),
            "2026-10-04T00:00:00Z",
        )
    ]
    assert latest_snapshot(fake_notes(rows), "example.com") is None
