import json
from unittest.mock import MagicMock

import pytest

from spiderfoot_connector.client import ScanOutcome, SpiderFootError
from spiderfoot_connector.config import load_settings
from spiderfoot_connector.connector import SpiderFootEnrichment


def settings(depth=1, scans=5):
    return load_settings(
        {
            "SPIDERFOOT_URL": "http://sf:5001",
            "SPIDERFOOT_ALLOWED_DOMAINS": "example.com",
            "SPIDERFOOT_MAX_DEPTH": str(depth),
            "SPIDERFOOT_MAX_SCANS": str(scans),
        }
    )


def names(*hosts):
    return [
        {
            "event_type": "INTERNET_NAME",
            "data": h,
            "source_data": "x",
            "module": "sfp_crt",
            "false_positive": 0,
        }
        for h in hosts
    ]


def make(graph, depth=1, scans=5, failing=()):
    """graph: target -> list of discovered hosts. Scans in `failing` raise SpiderFootError."""
    client = MagicMock()
    calls = []

    def run_scan(target, usecase, **_):
        calls.append(target)
        if target in failing:
            raise SpiderFootError(f"boom {target}")
        return ScanOutcome(f"ID-{target}", "FINISHED", names(*graph.get(target, [])))

    client.run_scan.side_effect = run_scan
    helper = MagicMock()
    return SpiderFootEnrichment(helper, settings(depth, scans), client), helper, calls


def message(value="example.com"):
    return {"enrichment_entity": {"entity_type": "Domain-Name", "observable_value": value}}


def bundle(helper):
    (b,), _ = helper.send_stix2_bundle.call_args
    return json.loads(b)["objects"]


def domain_values(helper):
    return {o["value"] for o in bundle(helper) if o["type"] == "domain-name"}


def test_depth_zero_is_a_single_scan_even_with_discoveries():
    enrichment, helper, calls = make({"example.com": ["a.example.com"]}, depth=0)
    enrichment.process_message(message())
    assert calls == ["example.com"]
    helper.send_stix2_bundle.assert_called_once()
    assert not any(
        "expansion" in o.get("abstract", "") for o in bundle(helper) if o["type"] == "note"
    )


def test_depth_one_scans_allowlisted_subdomains_breadth_first():
    graph = {"example.com": ["a.example.com", "b.example.com"]}
    enrichment, helper, calls = make(graph)
    enrichment.process_message(message())
    assert calls == ["example.com", "a.example.com", "b.example.com"]
    assert {"a.example.com", "b.example.com"} <= domain_values(helper)
    helper.send_stix2_bundle.assert_called_once()


def test_out_of_scope_discoveries_are_never_scanned_and_reported():
    graph = {"example.com": ["a.example.com", "x.partner.net", "evilexample.com"]}
    enrichment, _, calls = make(graph)
    result = enrichment.process_message(message())
    assert calls == ["example.com", "a.example.com"]
    assert "out_of_scope=2" in result


def test_no_scan_is_repeated():
    graph = {
        "example.com": ["a.example.com", "b.example.com"],
        "a.example.com": ["example.com", "b.example.com", "a.example.com"],
    }
    enrichment, _, calls = make(graph, depth=2)
    enrichment.process_message(message())
    assert sorted(calls) == ["a.example.com", "b.example.com", "example.com"]


def test_max_scans_caps_total_including_root():
    graph = {"example.com": ["a.example.com", "b.example.com", "c.example.com"]}
    enrichment, _, calls = make(graph, scans=2)
    result = enrichment.process_message(message())
    assert calls == ["example.com", "a.example.com"]
    assert "budget_skipped=2" in result


def test_depth_limit_respected_across_levels():
    graph = {"example.com": ["a.example.com"], "a.example.com": ["a2.example.com"]}
    enrichment, _, calls = make(graph, depth=1)
    enrichment.process_message(message())
    assert calls == ["example.com", "a.example.com"]
    enrichment, _, calls = make(graph, depth=2)
    enrichment.process_message(message())
    assert calls == ["example.com", "a.example.com", "a2.example.com"]


def test_sub_scan_failure_is_tolerated_and_reported():
    graph = {"example.com": ["a.example.com", "b.example.com"]}
    enrichment, helper, calls = make(graph, failing={"a.example.com"})
    result = enrichment.process_message(message())
    assert calls == ["example.com", "a.example.com", "b.example.com"]
    assert "failed=1" in result
    assert "b.example.com" in domain_values(helper)


def test_root_failure_still_raises_and_sends_nothing():
    enrichment, helper, _ = make({}, failing={"example.com"})
    with pytest.raises(SpiderFootError):
        enrichment.process_message(message())
    helper.send_stix2_bundle.assert_not_called()


def test_expansion_note_summarizes_the_run():
    graph = {"example.com": ["a.example.com", "x.partner.net"]}
    enrichment, helper, _ = make(graph)
    enrichment.process_message(message())
    notes = [o for o in bundle(helper) if o["type"] == "note" and "expansion" in o["abstract"]]
    assert len(notes) == 1
    text = notes[0]["content"]
    assert "scans run: 2" in text and "x.partner.net" in text


def test_every_scan_target_is_allowlisted():
    graph = {"example.com": ["a.example.com", "x.partner.net"], "a.example.com": ["evil.org"]}
    enrichment, _, calls = make(graph, depth=3)
    enrichment.process_message(message())
    assert all(c == "example.com" or c.endswith(".example.com") for c in calls)
