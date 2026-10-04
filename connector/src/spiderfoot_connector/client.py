"""Minimal client for the SpiderFoot open-source web UI HTTP API (CherryPy).

Endpoints used (verified against SpiderFoot's ``sfwebui.py``): ``startscan``,
``scanstatus``, ``stopscan`` and ``scanexportjsonmulti``.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field

import requests

TERMINAL_STATES = frozenset({"FINISHED", "ABORTED", "ERROR-FAILED"})
# SpiderFoot matches ``usecase`` against module groups, which are capitalized; only
# "all" is lowercase. Our config uses lowercase names, so translate here.
_USECASE_NAMES = {
    "passive": "Passive",
    "footprint": "Footprint",
    "investigate": "Investigate",
    "all": "all",
}
HTTP_TIMEOUT = 30


class SpiderFootError(RuntimeError):
    """Raised for transport errors and error responses from SpiderFoot."""


@dataclass
class ScanOutcome:
    scan_id: str
    status: str
    events: list[dict] = field(default_factory=list)
    timed_out: bool = False


class SpiderFootClient:
    def __init__(
        self,
        base_url: str,
        *,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._session = session or requests.Session()
        self._sleep = sleep
        self._monotonic = monotonic

    def _request(self, method: str, path: str, **kwargs):
        try:
            resp = self._session.request(
                method,
                f"{self._base}/{path}",
                headers={"Accept": "application/json"},
                timeout=HTTP_TIMEOUT,
                **kwargs,
            )
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as exc:
            raise SpiderFootError(f"SpiderFoot request to /{path} failed: {exc}") from exc

    def start_scan(self, target: str, usecase: str) -> str:
        sf_usecase = _USECASE_NAMES.get(usecase.lower())
        if sf_usecase is None:
            raise SpiderFootError(f"unsupported usecase {usecase!r}")
        data = self._request(
            "POST",
            "startscan",
            data={
                "scanname": f"opencti-enrich {target}",
                "scantarget": target,
                "modulelist": "",
                "typelist": "",
                "usecase": sf_usecase,
            },
        )
        if not (isinstance(data, list) and len(data) == 2):
            raise SpiderFootError(f"unexpected startscan response: {data!r}")
        kind, value = data
        if kind != "SUCCESS":
            raise SpiderFootError(f"SpiderFoot refused scan: {value}")
        return str(value)

    def status(self, scan_id: str) -> str:
        data = self._request("GET", "scanstatus", params={"id": scan_id})
        if not data:
            raise SpiderFootError(f"unknown scan {scan_id}")
        return str(data[5])

    def stop_scan(self, scan_id: str) -> None:
        self._request("GET", "stopscan", params={"id": scan_id})

    def fetch_events(self, scan_id: str) -> list[dict]:
        data = self._request("GET", "scanexportjsonmulti", params={"ids": scan_id})
        if not isinstance(data, list):
            raise SpiderFootError(f"unexpected export response: {type(data).__name__}")
        return data

    def run_scan(
        self, target: str, usecase: str, *, timeout_seconds: int, poll_seconds: int
    ) -> ScanOutcome:
        """Start a scan, wait for it, and return its events (partial on timeout)."""
        scan_id = self.start_scan(target, usecase)
        deadline = self._monotonic() + timeout_seconds
        status = self.status(scan_id)
        while status not in TERMINAL_STATES:
            if self._monotonic() >= deadline:
                try:
                    self.stop_scan(scan_id)
                except SpiderFootError:
                    pass  # best effort: partial results are still collected below
                return ScanOutcome(scan_id, status, self.fetch_events(scan_id), timed_out=True)
            self._sleep(poll_seconds)
            status = self.status(scan_id)
        return ScanOutcome(scan_id, status, self.fetch_events(scan_id))
