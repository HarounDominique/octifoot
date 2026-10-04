"""Automatic re-analysis of watched domains.

An analyst puts the label ``octifoot:watch`` on a Domain-Name observable. A loop in the connector reads the watched
domains and, for each one that is due and on the allowlist, asks OpenCTI to run this connector's own enrichment on it:
the same request an analyst's click makes, so every automated run is an ordinary, auditable work item with the normal
Notes, snapshot and comparison. Nothing is scanned without the label AND the allowlist.
"""

import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from spiderfoot_connector.allowlist import is_allowed
from spiderfoot_connector.changes import latest_snapshot

WATCH_LABEL = "octifoot:watch"

_WATCHED_QUERY = """
query($labels: [Any!]!) {
  stixCyberObservables(first: 100, types: ["Domain-Name"],
      filters: {mode: and, filters: [{key: "objectLabel", values: $labels}], filterGroups: []}) {
    edges { node { id observable_value } }
  }
}
"""
_ASK_MUTATION = """
mutation($id: ID!, $connector: ID!) {
  stixCoreObjectEdit(id: $id) { askEnrichment(connectorId: $connector) { id } }
}
"""

RunQuery = Callable[[str, dict[str, Any]], dict[str, Any]]
Log = Callable[[str, str, dict[str, Any]], None]


def query_watched(run_query: RunQuery) -> list[tuple[str, str]]:
    """(id, value) of the Domain-Name observables labelled for watching; read-only."""
    data = run_query(_WATCHED_QUERY, {"labels": [WATCH_LABEL]})
    return [
        (e["node"]["id"], e["node"]["observable_value"])
        for e in data["data"]["stixCyberObservables"]["edges"]
    ]


def ask_enrichment(run_query: RunQuery, object_id: str, connector_id: str) -> str:
    """Ask OpenCTI to run this connector's enrichment on the observable; returns the work id."""
    data = run_query(_ASK_MUTATION, {"id": object_id, "connector": connector_id})
    if data.get("errors"):
        raise RuntimeError(str(data["errors"][0].get("message", data["errors"]))[:200])
    return data["data"]["stixCoreObjectEdit"]["askEnrichment"]["id"]


def snapshot_time(run_query: RunQuery, value: str) -> datetime | None:
    """When the newest snapshot Note of the domain was written, i.e. when it was last scanned."""
    snap = latest_snapshot(run_query, value)
    if snap is None:
        return None
    return datetime.fromisoformat(snap.at)


def _normalise(value: str) -> str:
    return value.strip().lower().rstrip(".")


class Watcher:
    def __init__(
        self,
        *,
        interval_seconds: float,
        max_per_cycle: int,
        allowlist: frozenset[str],
        list_watched: Callable[[], list[tuple[str, str]]],
        last_scan: Callable[[str], datetime | None],
        ask: Callable[[str], Any],
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        log: Log = lambda level, message, meta: None,
    ) -> None:
        self._interval = interval_seconds
        self._cap = max_per_cycle
        self._allowlist = allowlist
        self._list = list_watched
        self._last_scan = last_scan
        self._ask = ask
        self._clock = clock
        self._log = log
        self._asked: dict[str, datetime] = {}  # value -> when we last asked (lost on restart)

    def run_cycle(self) -> list[str]:
        """Ask for the due watched domains (oldest first, capped); never raises."""
        try:
            watched = self._list()
        except Exception as exc:  # noqa: BLE001  the loop must survive any platform failure
            self._log("warning", "Watch: could not list watched domains", {"error": str(exc)})
            return []
        now = self._clock()
        due: list[tuple[datetime, str, str]] = []
        for object_id, raw in watched:
            value = _normalise(raw)
            if not is_allowed(value, self._allowlist):
                self._log("warning", "Watch: skipped, not on the allowlist", {"target": value})
                continue
            asked_at = self._asked.get(value)
            if asked_at is not None and (now - asked_at).total_seconds() < self._interval:
                continue
            try:
                last = self._last_scan(value)
            except Exception as exc:  # noqa: BLE001  unknown history: do not guess, try next cycle
                self._log(
                    "warning",
                    "Watch: could not read the last scan",
                    {"target": value, "error": str(exc)},
                )
                continue
            if last is not None and (now - last).total_seconds() < self._interval:
                continue
            due.append((last or datetime.min.replace(tzinfo=UTC), value, object_id))
        started = []
        for _, value, object_id in sorted(due)[: self._cap]:
            try:
                self._ask(object_id)
            except Exception as exc:  # noqa: BLE001  one refused request must not stop the others
                self._log(
                    "warning",
                    "Watch: enrichment request failed",
                    {"target": value, "error": str(exc)},
                )
                continue
            self._asked[value] = now
            started.append(value)
            self._log("info", "Watch: requested a scheduled enrichment", {"target": value})
        return started

    def serve(self, stop: threading.Event, cycle_seconds: float) -> None:
        while not stop.is_set():
            try:
                self.run_cycle()
            except Exception as exc:  # noqa: BLE001  belt and braces: run_cycle already isolates failures
                self._log("warning", "Watch: cycle failed", {"error": str(exc)})
            stop.wait(cycle_seconds)
