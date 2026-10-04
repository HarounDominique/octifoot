from datetime import UTC, datetime

from spiderfoot_connector.mapper import map_events
from spiderfoot_connector.provenance import coverage_line, events_digest, provenance_line

NOW = datetime(2026, 10, 5, 6, 0, 0, tzinfo=UTC)


def ev(module, data="a.example.com"):
    return {
        "event_type": "INTERNET_NAME",
        "data": data,
        "source_data": "example.com",
        "module": module,
        "false_positive": 0,
    }


def line(**over):
    args = {
        "octifoot_version": "0.1.0",
        "spiderfoot_version": "4.0.0",
        "profile": "lean",
        "usecase": "passive",
        "modules": ["sfp_b", "sfp_a"],
        "seconds": 900,
        "events": [ev("sfp_crt")],
    }
    return provenance_line(**{**args, **over})


# --- digest ---


def test_digest_does_not_depend_on_event_order_or_key_order():
    a, b = ev("sfp_crt", "x.example.com"), ev("sfp_dnsdb", "y.example.com")
    reordered = dict(reversed(list(a.items())))
    assert events_digest([a, b]) == events_digest([b, reordered])


def test_digest_changes_with_content_and_is_sha256_hex():
    one = events_digest([ev("sfp_crt")])
    assert len(one) == 64 and int(one, 16) >= 0
    assert one != events_digest([ev("sfp_crt", "other.example.com")])
    assert events_digest([]) == events_digest([])


# --- provenance line ---


def test_provenance_names_tools_settings_time_and_events():
    text = line()
    assert text.startswith("Provenance: ")
    for part in ("octifoot 0.1.0", "SpiderFoot 4.0.0", "profile lean", "use case passive"):
        assert part in text
    assert "modules requested: 2" in text
    assert "time applied 900 s" in text
    assert "events: 1" in text and events_digest([ev("sfp_crt")])[:16] in text


def test_module_list_digest_ignores_order():
    assert line(modules=["sfp_a", "sfp_b"]) == line(modules=["sfp_b", "sfp_a"])
    assert line(modules=["sfp_a", "sfp_c"]) != line(modules=["sfp_a", "sfp_b"])


def test_full_profile_says_the_group_not_a_count():
    text = line(profile="full", modules=None)
    assert "SpiderFoot's passive group" in text and "modules requested" not in text


def test_unknown_spiderfoot_version_is_stated():
    assert "SpiderFoot unknown" in line(spiderfoot_version="")


# --- coverage line ---


def test_coverage_counts_producing_modules_errors_and_keyed_modules():
    events = [ev("sfp_crt"), ev("sfp_crt", "b.example.com"), ev("sfp_dnsdb"), ev("SpiderFoot UI")]
    text = coverage_line(events, [("sfp_x", "boom"), ("sfp_x", "again")], frozenset({"sfp_dnsdb"}))
    assert text.startswith("Coverage: ")
    assert "2 modules produced data" in text
    assert "1 module reported errors" in text
    assert "API-keyed modules active: sfp_dnsdb" in text
    assert "cannot be told from" in text


def test_coverage_with_nothing_is_honest_and_has_no_key_clause():
    text = coverage_line([], [], frozenset())
    assert "0 modules produced data" in text and "0 modules reported errors" in text
    assert "API-keyed" not in text


def test_key_names_only_never_values():
    assert "secret" not in coverage_line([ev("sfp_crt")], [], frozenset({"sfp_dnsdb"}))


# --- in the Note ---


def note(**kw):
    result = map_events(
        [ev("sfp_crt")], target="example.com", scan_id="S1", score=30, now=NOW, **kw
    )
    (n,) = [o for o in result.objects if o.type == "note"]
    return n.content


def test_extra_lines_appear_in_the_scan_note():
    text = note(extra_lines=["Provenance: x", "Coverage: y"])
    assert "Provenance: x" in text and "Coverage: y" in text


def test_default_note_is_unchanged_without_extra_lines():
    assert "Provenance:" not in note() and "Coverage:" not in note()
