from datetime import UTC, datetime

from spiderfoot_connector.mapper import map_events

NOW = datetime(2026, 10, 4, 6, 0, 0, tzinfo=UTC)
EVENTS = [
    {
        "event_type": "INTERNET_NAME",
        "data": "www.example.com",
        "source_data": "example.com",
        "module": "sfp_crt",
        "false_positive": 0,
    },
    {
        "event_type": "IP_ADDRESS",
        "data": "203.0.113.9",
        "source_data": "www.example.com",
        "module": "sfp_dnsresolve",
        "false_positive": 0,
    },
    {
        "event_type": "MALICIOUS_IPADDR",
        "data": "Maltiverse [203.0.113.9]",
        "source_data": "203.0.113.9",
        "module": "sfp_maltiverse",
        "false_positive": 0,
    },
]


def run(ui_url=None):
    kwargs = {} if ui_url is None else {"ui_url": ui_url}
    return map_events(EVENTS, target="example.com", scan_id="ABC123", score=30, now=NOW, **kwargs)


def refs(result):
    out = []
    for o in result.objects:
        out += list(getattr(o, "x_opencti_external_references", []) or [])
    return out


def note(result):
    (n,) = [o for o in result.objects if o.type == "note"]
    return n.content


URL = "http://localhost:5001/scaninfo?id=ABC123"


def test_without_a_ui_url_nothing_changes():
    assert all("url" not in r for r in refs(run()))
    assert "Full results" not in note(run())


def test_every_reference_of_the_scan_links_to_the_spiderfoot_page():
    got = refs(run("http://localhost:5001"))
    assert got and all(r["url"] == URL for r in got)
    assert any("Flagged malicious" in r["description"] for r in got)  # feed references too


def test_first_line_of_the_note_ends_with_the_link_and_still_starts_as_before():
    first = note(run("http://localhost:5001")).splitlines()[0]
    assert first.startswith("SpiderFoot scan ABC123 for example.com.")
    assert first.endswith(f"Full results in SpiderFoot: {URL}")


def test_links_do_not_change_object_ids():
    plain = {o.id for o in run().objects if o.type != "note"}
    linked = {o.id for o in run("http://localhost:5001").objects if o.type != "note"}
    assert plain == linked
