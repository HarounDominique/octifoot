import threading
from datetime import UTC, datetime, timedelta

from spiderfoot_connector.allowlist import parse_allowlist
from spiderfoot_connector.watch import Watcher, ask_enrichment, query_watched

NOW = datetime(2026, 10, 4, 12, 0, 0, tzinfo=UTC)
HOUR = 3600


class Clock:
    def __init__(self, now=NOW):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)


def build(
    watched, last=None, *, interval_minutes=60, cap=3, allow="example.com", fail=None, clock=None
):
    clock = clock or Clock()
    asked, log = [], []
    last = last or {}

    def list_watched():
        if fail == "list":
            raise RuntimeError("platform unreachable")
        return watched

    def ask(object_id):
        if fail == object_id:
            raise RuntimeError("refused")
        asked.append(object_id)

    w = Watcher(
        interval_seconds=interval_minutes * 60,
        max_per_cycle=cap,
        allowlist=parse_allowlist(allow),
        list_watched=list_watched,
        last_scan=lambda value: last.get(value),
        ask=ask,
        clock=clock,
        log=lambda level, message, meta: log.append((level, message, meta)),
    )
    return w, asked, log, clock


# --- when a domain is due ---


def test_a_watched_domain_never_scanned_is_asked():
    w, asked, _, _ = build([("id1", "example.com")])
    assert w.run_cycle() == ["example.com"] and asked == ["id1"]


def test_a_recently_scanned_domain_is_not_asked():
    w, asked, _, _ = build([("id1", "example.com")], {"example.com": NOW - timedelta(minutes=30)})
    assert w.run_cycle() == [] and asked == []


def test_an_old_scan_makes_the_domain_due():
    w, _, _, _ = build([("id1", "example.com")], {"example.com": NOW - timedelta(hours=2)})
    assert w.run_cycle() == ["example.com"]


def test_a_domain_just_asked_is_not_asked_again_within_the_interval_even_before_its_scan_finishes():
    w, asked, _, clock = build([("id1", "example.com")])
    w.run_cycle()
    clock.advance(10 * 60)
    assert w.run_cycle() == [] and asked == ["id1"]


def test_it_is_asked_again_once_the_interval_has_passed():
    w, asked, _, clock = build([("id1", "example.com")])
    w.run_cycle()
    clock.advance(HOUR + 1)
    assert w.run_cycle() == ["example.com"] and asked == ["id1", "id1"]


# --- authorization ---


def test_a_watched_domain_outside_the_allowlist_is_never_asked_and_is_logged():
    w, asked, log, _ = build([("id1", "other.net"), ("id2", "example.com")])
    assert w.run_cycle() == ["example.com"] and asked == ["id2"]
    assert any(level == "warning" and "allowlist" in message for level, message, _ in log)


def test_subdomains_of_an_allowlisted_domain_are_allowed():
    w, _, _, _ = build([("id1", "www.example.com")])
    assert w.run_cycle() == ["www.example.com"]


def test_lookalike_domains_are_not_allowed():
    w, asked, _, _ = build([("id1", "notexample.com"), ("id2", "example.com.evil.net")])
    assert w.run_cycle() == [] and asked == []


def test_values_are_normalised_before_the_checks():
    w, _, _, _ = build([("id1", "WWW.Example.com.")])
    assert w.run_cycle() == ["www.example.com"]


# --- cap and order ---


def test_never_scanned_first_then_oldest_and_the_cap_applies():
    last = {"b.example.com": NOW - timedelta(hours=5), "c.example.com": NOW - timedelta(hours=9)}
    watched = [
        ("1", "b.example.com"),
        ("2", "c.example.com"),
        ("3", "new.example.com"),
        ("4", "d.example.com"),
    ]
    last["d.example.com"] = NOW - timedelta(hours=2)
    w, asked, _, _ = build(watched, last, cap=3)
    assert w.run_cycle() == ["new.example.com", "c.example.com", "b.example.com"]
    assert asked == ["3", "2", "1"]


def test_the_skipped_due_domains_are_picked_up_in_the_next_cycle():
    watched = [("1", "a.example.com"), ("2", "b.example.com"), ("3", "c.example.com")]
    w, _, _, clock = build(watched, cap=2)
    first = w.run_cycle()
    clock.advance(60)
    second = w.run_cycle()
    assert len(first) == 2 and len(second) == 1 and set(first + second) == {v for _, v in watched}


# --- failures never stop the loop ---


def test_a_failing_listing_returns_nothing_and_does_not_raise():
    w, _, log, _ = build([], fail="list")
    assert w.run_cycle() == [] and any(level == "warning" for level, _, _ in log)


def test_one_refused_request_does_not_stop_the_others_and_is_retried_next_cycle():
    watched = [("bad", "a.example.com"), ("ok", "b.example.com")]
    w, asked, _, clock = build(watched, fail="bad")
    assert w.run_cycle() == ["b.example.com"] and asked == ["ok"]
    clock.advance(60)
    assert (
        w.run_cycle() == []
    )  # "bad" keeps failing, "ok" was just asked; nothing recorded for the failure
    assert asked == ["ok"]


def test_the_loop_stops_when_asked_and_survives_a_failing_cycle():
    w, _, _, _ = build([], fail="list")
    stop = threading.Event()
    calls = []
    original = w.run_cycle

    def counting():
        calls.append(1)
        if len(calls) == 2:
            stop.set()
        return original()

    w.run_cycle = counting
    w.serve(stop, cycle_seconds=0.01)
    assert len(calls) == 2


# --- the two OpenCTI helpers ---


def test_query_watched_reads_domain_names_with_the_watch_label_and_nothing_else():
    seen = {}

    def run(query, variables):
        seen["query"], seen["variables"] = query, variables
        return {
            "data": {
                "stixCyberObservables": {
                    "edges": [{"node": {"id": "id1", "observable_value": "Example.COM"}}]
                }
            }
        }

    assert query_watched(run) == [("id1", "Example.COM")]
    assert "mutation" not in seen["query"] and "octifoot:watch" in str(seen["variables"])


def test_ask_enrichment_requests_this_connectors_enrichment_on_the_observable():
    seen = {}

    def run(query, variables):
        seen["query"], seen["variables"] = query, variables
        return {"data": {"stixCoreObjectEdit": {"askEnrichment": {"id": "work-1"}}}}

    assert ask_enrichment(run, "obs-1", "connector-1") == "work-1"
    assert "askEnrichment" in seen["query"]
    assert seen["variables"] == {"id": "obs-1", "connector": "connector-1"}
