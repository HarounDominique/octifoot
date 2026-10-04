import json
from pathlib import Path
from urllib.parse import parse_qs

import pytest
import responses

from spiderfoot_connector.client import SpiderFootClient, SpiderFootError

BASE = "http://sf:5001"
EVENTS = json.loads((Path(__file__).parent.parent / "fixtures" / "scan_events.json").read_text())


class Clock:
    """Fake time: sleeping advances the clock, so polling tests run instantly."""

    def __init__(self):
        self.t = 0.0

    def monotonic(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def client(clock):
    return SpiderFootClient(BASE, sleep=clock.sleep, monotonic=clock.monotonic)


def status_body(status):
    return ["enrich", "example.com", "c", "s", "e", status, {}]


@responses.activate
def test_start_scan_sends_capitalized_usecase_and_json_accept(client):
    responses.add(responses.POST, f"{BASE}/startscan", json=["SUCCESS", "ABC123"])
    assert client.start_scan("example.com", "passive") == "ABC123"
    req = responses.calls[0].request
    assert req.headers["Accept"] == "application/json"
    body = req.body if isinstance(req.body, str) else req.body.decode()
    assert "usecase=Passive" in body
    assert "scantarget=example.com" in body
    assert "modulelist=" in body and "typelist=" in body


@responses.activate
def test_start_scan_all_usecase_stays_lowercase(client):
    responses.add(responses.POST, f"{BASE}/startscan", json=["SUCCESS", "X"])
    client.start_scan("example.com", "all")
    assert "usecase=all" in responses.calls[0].request.body


@responses.activate
def test_start_scan_error_response(client):
    responses.add(responses.POST, f"{BASE}/startscan", json=["ERROR", "Unrecognised target type."])
    with pytest.raises(SpiderFootError, match="Unrecognised target type"):
        client.start_scan("???", "passive")


@responses.activate
def test_http_error_raises(client):
    responses.add(responses.POST, f"{BASE}/startscan", status=500)
    with pytest.raises(SpiderFootError):
        client.start_scan("example.com", "passive")


@responses.activate
def test_connection_error_raises(client):
    # no mock registered -> requests raises ConnectionError
    with pytest.raises(SpiderFootError):
        client.start_scan("example.com", "passive")


@responses.activate
def test_run_scan_polls_until_finished(client):
    responses.add(responses.POST, f"{BASE}/startscan", json=["SUCCESS", "ABC123"])
    for st in ("STARTING", "RUNNING", "FINISHED"):
        responses.add(responses.GET, f"{BASE}/scanstatus", json=status_body(st))
    responses.add(responses.GET, f"{BASE}/scanexportjsonmulti", json=EVENTS)

    out = client.run_scan("example.com", "passive", timeout_seconds=100, poll_seconds=5)

    assert out.scan_id == "ABC123"
    assert out.status == "FINISHED"
    assert out.timed_out is False
    assert len(out.events) == len(EVENTS)
    export = next(c for c in responses.calls if "scanexportjsonmulti" in c.request.url)
    assert "ids=ABC123" in export.request.url


@responses.activate
def test_run_scan_timeout_stops_scan_and_returns_partial(client):
    responses.add(responses.POST, f"{BASE}/startscan", json=["SUCCESS", "ABC123"])
    responses.add(responses.GET, f"{BASE}/scanstatus", json=status_body("RUNNING"))
    responses.add(responses.GET, f"{BASE}/stopscan", json={})
    responses.add(responses.GET, f"{BASE}/scanexportjsonmulti", json=EVENTS[:2])

    out = client.run_scan("example.com", "passive", timeout_seconds=20, poll_seconds=5)

    assert out.timed_out is True
    assert len(out.events) == 2
    assert any("stopscan" in c.request.url for c in responses.calls)


@responses.activate
def test_run_scan_error_failed_is_reported(client):
    responses.add(responses.POST, f"{BASE}/startscan", json=["SUCCESS", "ABC123"])
    responses.add(responses.GET, f"{BASE}/scanstatus", json=status_body("ERROR-FAILED"))
    responses.add(responses.GET, f"{BASE}/scanexportjsonmulti", json=[])
    out = client.run_scan("example.com", "passive", timeout_seconds=100, poll_seconds=5)
    assert out.status == "ERROR-FAILED"
    assert out.events == []


@responses.activate
def test_status_empty_list_means_unknown_scan(client):
    responses.add(responses.GET, f"{BASE}/scanstatus", json=[])
    with pytest.raises(SpiderFootError, match="unknown scan"):
        client.status("nope")


@responses.activate
def test_start_scan_with_modules_sends_modulelist_and_no_usecase(client):
    responses.add(responses.POST, f"{BASE}/startscan", json=["SUCCESS", "M1"])
    assert client.start_scan("example.com", "passive", modules=["sfp_crt", "sfp_ripe"]) == "M1"
    body = parse_qs(responses.calls[0].request.body)
    assert body["modulelist"] == ["sfp_crt,sfp_ripe"]
    assert body.get("usecase", [""]) == [""]


@responses.activate
def test_run_scan_passes_modules_through(client):
    responses.add(responses.POST, f"{BASE}/startscan", json=["SUCCESS", "M1"])
    responses.add(responses.GET, f"{BASE}/scanstatus", json=status_body("FINISHED"))
    responses.add(responses.GET, f"{BASE}/scanexportjsonmulti", json=[])
    client.run_scan(
        "example.com", "passive", timeout_seconds=10, poll_seconds=1, modules=["sfp_crt"]
    )
    assert parse_qs(responses.calls[0].request.body)["modulelist"] == ["sfp_crt"]


@responses.activate
def test_full_profile_still_sends_usecase_and_empty_modulelist(client):
    responses.add(responses.POST, f"{BASE}/startscan", json=["SUCCESS", "F1"])
    client.start_scan("example.com", "passive")
    body = parse_qs(responses.calls[0].request.body, keep_blank_values=True)
    assert body["usecase"] == ["Passive"]
    assert body["modulelist"] == [""]


# --- scan log errors (source health) ---


def log_rows(*rows):
    return [
        [f"2026-10-04 12:00:0{i}", comp, typ, msg, i] for i, (comp, typ, msg) in enumerate(rows)
    ]


@responses.activate
def test_fetch_errors_returns_only_error_rows_decoded_in_order(client):
    responses.add(
        responses.GET,
        f"{BASE}/scanlog",
        # SpiderFoot returns the newest row first
        json=log_rows(
            ("sfp_commoncrawl", "ERROR", "CommonCrawl index doesn&#x27;t seem to be available."),
            ("sfp_x", "DEBUG", "Received event"),
            ("sfp_sublist3r", "ERROR", "Bad response code &quot;None&quot; from Sublist3r API"),
            ("sfp_crt", "STATUS", "No certificate transparency info found for example.com"),
        ),
    )
    assert client.fetch_errors("ABC") == [
        ("sfp_sublist3r", 'Bad response code "None" from Sublist3r API'),
        ("sfp_commoncrawl", "CommonCrawl index doesn't seem to be available."),
    ]
    query = parse_qs(responses.calls[0].request.url.split("?", 1)[1])
    assert query["id"] == ["ABC"] and query["limit"] == ["100000"]


@responses.activate
def test_fetch_errors_with_no_error_rows_is_empty(client):
    responses.add(responses.GET, f"{BASE}/scanlog", json=log_rows(("sfp_x", "DEBUG", "ok")))
    assert client.fetch_errors("ABC") == []


@responses.activate
def test_fetch_errors_rejects_an_unexpected_response(client):
    responses.add(responses.GET, f"{BASE}/scanlog", json={"error": "nope"})
    with pytest.raises(SpiderFootError):
        client.fetch_errors("ABC")
