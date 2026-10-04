import json
from unittest.mock import MagicMock

import pytest

from spiderfoot_connector.client import ScanOutcome, SpiderFootError
from spiderfoot_connector.config import load_settings
from spiderfoot_connector.connector import SpiderFootEnrichment


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


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


def build(
    graph, *, total="3600", durations=None, failing=(), crash=(), depth=1, scans=5, timeout="900"
):
    settings = load_settings(
        {
            "SPIDERFOOT_URL": "http://sf:5001",
            "SPIDERFOOT_ALLOWED_DOMAINS": "example.com",
            "SPIDERFOOT_PROFILE": "full",
            "SPIDERFOOT_MAX_DEPTH": str(depth),
            "SPIDERFOOT_MAX_SCANS": str(scans),
            "SPIDERFOOT_TIMEOUT_SECONDS": timeout,
            "SPIDERFOOT_MAX_TOTAL_SECONDS": total,
        }
    )
    clock, events, timeouts = Clock(), [], {}
    durations = durations or {}

    def run_scan(target, usecase, **kw):
        events.append(("scan", target))
        timeouts[target] = kw["timeout_seconds"]
        clock.now += durations.get(target, 0)
        if target in failing:
            raise SpiderFootError(f"boom {target}")
        if target in crash:
            raise RuntimeError(f"killed {target}")
        cut = durations.get(target, 0) >= kw["timeout_seconds"]
        return ScanOutcome(
            f"ID-{target}",
            "ABORTED" if cut else "FINISHED",
            names(*graph.get(target, [])),
            timed_out=cut,
        )

    client = MagicMock()
    client.run_scan.side_effect = run_scan
    client.fetch_errors.return_value = []
    helper = MagicMock()
    helper.send_stix2_bundle.side_effect = lambda bundle: events.append(
        ("send", json.loads(bundle))
    )
    enrichment = SpiderFootEnrichment(helper, settings, client, clock=clock)
    return enrichment, helper, events, timeouts


def message(value="example.com"):
    return {"enrichment_entity": {"entity_type": "Domain-Name", "observable_value": value}}


def sends(events):
    return [e[1] for e in events if e[0] == "send"]


def note_texts(bundle):
    return [o["content"] for o in bundle["objects"] if o["type"] == "note"]


GRAPH = {"example.com": ["www.example.com", "api.example.com"]}


# --- results as they finish ---


def test_a_finished_scan_is_sent_before_the_next_one_starts():
    enrichment, _, events, _ = build(GRAPH)
    enrichment.process_message(message())
    kinds = [(e[0], e[1] if e[0] == "scan" else "") for e in events]
    assert kinds[:2] == [("scan", "example.com"), ("send", "")]
    assert kinds[2][0] == "scan" and kinds[2][1] in ("www.example.com", "api.example.com")


def test_the_early_bundle_holds_that_scans_objects_and_its_note():
    enrichment, _, events, _ = build(GRAPH)
    enrichment.process_message(message())
    early = sends(events)[0]
    values = {o["value"] for o in early["objects"] if "value" in o}
    assert "www.example.com" in values and "api.example.com" in values
    assert any(t.startswith("SpiderFoot scan ID-example.com") for t in note_texts(early))


def test_the_early_bundle_does_not_resend_objects_that_were_already_sent():
    enrichment, _, events, _ = build(GRAPH)
    enrichment.process_message(message())
    first_ids = {o["id"] for o in sends(events)[0]["objects"]}
    second_ids = {o["id"] for o in sends(events)[1]["objects"]}
    domain_ids = {o["id"] for o in sends(events)[0]["objects"] if o["type"] == "domain-name"}
    assert domain_ids <= first_ids and len(sends(events)) == 3  # root, www early; final last
    assert not (second_ids & {i for i in first_ids if i in domain_ids})


def test_the_final_bundle_still_carries_everything_and_the_summary_notes():
    enrichment, _, events, _ = build(GRAPH)
    enrichment.process_message(message())
    final = sends(events)[-1]
    values = {o["value"] for o in final["objects"] if "value" in o}
    assert {"www.example.com", "api.example.com", "example.com"} <= values
    texts = " ".join(note_texts(final))
    assert "Expansion from example.com" in texts


def test_a_single_scan_still_sends_exactly_one_bundle():
    enrichment, _, events, _ = build({"example.com": []})
    enrichment.process_message(message())
    assert len(sends(events)) == 1


def test_without_expansion_nothing_is_sent_early():
    enrichment, _, events, _ = build(GRAPH, depth=0)
    enrichment.process_message(message())
    assert len(sends(events)) == 1 and [e for e in events if e[0] == "scan"] == [
        ("scan", "example.com")
    ]


def test_a_crash_after_the_first_scan_keeps_what_was_already_sent():
    enrichment, _, events, _ = build(GRAPH, crash=("www.example.com", "api.example.com"))
    with pytest.raises(RuntimeError):
        enrichment.process_message(message())
    early = sends(events)
    assert len(early) == 1 and "www.example.com" in {o.get("value") for o in early[0]["objects"]}


def test_a_failing_sub_scan_does_not_lose_the_scans_already_sent():
    enrichment, _, events, _ = build(GRAPH, failing=("www.example.com",))
    enrichment.process_message(message())
    assert any("example.com" in str(s) for s in sends(events)[:1])
    assert sends(events)[-1]["objects"]


# --- the total deadline ---


def test_the_root_scan_never_gets_more_than_the_total():
    enrichment, _, _, timeouts = build(GRAPH, total="100", timeout="900")
    enrichment.process_message(message())
    assert timeouts["example.com"] == 100


def test_a_sub_scan_gets_only_the_time_that_is_left():
    enrichment, _, _, timeouts = build(GRAPH, total="300", durations={"example.com": 120})
    enrichment.process_message(message())
    assert timeouts["example.com"] == 300
    assert timeouts["www.example.com"] == 180


def test_the_per_scan_limit_still_applies_when_the_total_is_larger():
    enrichment, _, _, timeouts = build(GRAPH, total="3600", timeout="900")
    enrichment.process_message(message())
    assert set(timeouts.values()) == {900}


def test_no_scan_is_started_with_less_than_sixty_seconds_left_and_the_skip_is_reported():
    enrichment, _, events, timeouts = build(GRAPH, total="130", durations={"example.com": 100})
    result = enrichment.process_message(message())
    assert list(timeouts) == ["example.com"]  # nothing else started
    final = sends(events)[-1]
    texts = " ".join(note_texts(final))
    assert "Skipped, total time limit reached (130 s)" in texts
    assert "www.example.com" in texts.split("total time limit reached")[1]
    assert "deadline_skipped=2" in result


def test_the_scan_that_ran_out_of_time_says_how_long_it_was_given():
    enrichment, _, events, _ = build(
        {"example.com": []}, total="100", durations={"example.com": 100}
    )
    enrichment.process_message(message())
    texts = " ".join(note_texts(sends(events)[-1]))
    assert "stopped after 100 s" in texts


def test_skipping_for_time_marks_the_snapshot_incomplete():
    enrichment, _, events, _ = build(GRAPH, total="130", durations={"example.com": 100})
    enrichment._snapshot_lookup = lambda target: None
    enrichment.process_message(message())
    snapshot = next(t for t in note_texts(sends(events)[-1]) if "Snapshot (machine-readable" in t)
    assert '"complete": false' in snapshot


def test_a_complete_expansion_marks_the_snapshot_complete():
    enrichment, _, events, _ = build(GRAPH)
    enrichment._snapshot_lookup = lambda target: None
    enrichment.process_message(message())
    snapshot = next(t for t in note_texts(sends(events)[-1]) if "Snapshot (machine-readable" in t)
    assert '"complete": true' in snapshot


def test_the_expansion_note_has_no_deadline_line_when_nothing_was_skipped_for_time():
    enrichment, _, events, _ = build(GRAPH)
    enrichment.process_message(message())
    assert "total time limit" not in " ".join(note_texts(sends(events)[-1]))


# --- provenance and coverage lines in each scan's Note ---


def test_every_scan_note_carries_provenance_and_coverage_with_the_applied_time():
    enrichment, _, events, _ = build(GRAPH, total="300", durations={"example.com": 120})
    helper_client = enrichment._client
    helper_client.version.return_value = "4.0.0"
    enrichment.process_message(message())
    texts = note_texts(sends(events)[-1])
    scans = [t for t in texts if t.startswith("SpiderFoot scan ID-")]
    assert len(scans) == 3
    for text in scans:
        assert "Provenance: octifoot " in text and "SpiderFoot 4.0.0" in text
        assert "Coverage: " in text
    root = next(t for t in scans if t.startswith("SpiderFoot scan ID-example.com"))
    sub = next(t for t in scans if t.startswith("SpiderFoot scan ID-www.example.com"))
    assert "time applied 300 s" in root and "time applied 180 s" in sub


def test_an_unreadable_spiderfoot_version_does_not_fail_the_enrichment():
    enrichment, _, events, _ = build({"example.com": []})
    enrichment._client.version.side_effect = RuntimeError("down")
    enrichment.process_message(message())
    assert "SpiderFoot unknown" in " ".join(note_texts(sends(events)[-1]))
