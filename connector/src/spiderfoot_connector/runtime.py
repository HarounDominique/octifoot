"""Settings the operator can change at run time from the control panel: extra authorised domains and the maximum time of an analysis.

State lives in a JSON file (plus an audit log) in a Docker volume. The ``.env`` allowlist is never edited here: the effective
allowlist is that list plus the domains added from the panel, recomputed at every use, so a removal takes effect for the next analysis.
Anything unreadable falls back to the ``.env`` values; this module never raises into an enrichment.
"""

import json
import os
import re
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from spiderfoot_connector.allowlist import validate_domain

MAX_UI_DOMAINS = 100
MIN_TIMEOUT, MAX_TIMEOUT = 60, 7200
MIN_TOTAL, MAX_TOTAL = 60, 14400  # whole-enrichment time
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def _now() -> datetime:
    return datetime.now(UTC)


def _stamp(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


class RuntimeStore:
    def __init__(self, directory: str | Path, clock: Callable[[], datetime] = _now) -> None:
        self.directory = Path(directory)
        self._clock = clock
        self._lock = threading.Lock()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.problem: str | None = None
        self._state = self._read()

    # --- reading ---

    @property
    def _settings_path(self) -> Path:
        return self.directory / "settings.json"

    def _read(self) -> dict[str, Any]:
        empty: dict[str, Any] = {
            "domains": [],
            "timeout_seconds": None,
            "total_timeout_seconds": None,
        }
        path = self._settings_path
        if not path.exists():
            self.problem = None
            return empty
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            domains = data["domains"]
            if not isinstance(data, dict) or not isinstance(domains, list):
                raise TypeError("wrong shape")
            clean = []
            for item in domains:
                try:
                    clean.append(
                        {
                            "value": validate_domain(str(item["value"])),
                            "added_at": str(item["added_at"]),
                        }
                    )
                except (ValueError, KeyError, TypeError):
                    continue  # a hand-edited invalid entry is ignored, never authorised
            timeout = data.get("timeout_seconds")
            if timeout is not None and not (
                isinstance(timeout, int)
                and not isinstance(timeout, bool)
                and MIN_TIMEOUT <= timeout <= MAX_TIMEOUT
            ):
                timeout = None
            self.problem = None
            total = data.get("total_timeout_seconds")
            if total is not None and not (
                isinstance(total, int)
                and not isinstance(total, bool)
                and MIN_TOTAL <= total <= MAX_TOTAL
            ):
                total = None
            return {"domains": clean, "timeout_seconds": timeout, "total_timeout_seconds": total}
        except (OSError, ValueError, KeyError, TypeError):
            self.problem = f"{path.name} could not be read; the .env values apply"
            return empty

    def _refresh(self) -> dict[str, Any]:
        with self._lock:
            self._state = self._read()
            return self._state

    def domains(self) -> list[dict[str, str]]:
        return list(self._refresh()["domains"])

    def timeout_override(self) -> int | None:
        return self._refresh()["timeout_seconds"]

    def effective_allowlist(self, base: frozenset[str]) -> frozenset[str]:
        return frozenset(base) | frozenset(d["value"] for d in self._refresh()["domains"])

    def total_timeout_override(self) -> int | None:
        return self._refresh()["total_timeout_seconds"]

    def effective_total_timeout(self, base: int) -> int:
        override = self.total_timeout_override()
        return override if override is not None else base

    def effective_timeout(self, base: int) -> int:
        override = self.timeout_override()
        return override if override is not None else base

    # --- changing ---

    def _write(self) -> None:
        tmp = self.directory / "settings.json.tmp"
        tmp.write_text(json.dumps(self._state, indent=1), encoding="utf-8")
        os.replace(tmp, self._settings_path)

    def _audit(self, action: str, detail: str, by: str) -> None:
        by = _CONTROL.sub("_", by)[:80]
        line = f"{_stamp(self._clock())} {action} {detail} by={by}\n"
        with open(self.directory / "audit.log", "a", encoding="utf-8") as handle:
            handle.write(line)

    def add_domain(self, value: str, *, by: str) -> str:
        domain = validate_domain(value)
        with self._lock:
            self._state = self._read()
            if domain in {d["value"] for d in self._state["domains"]}:
                raise ValueError(f"{domain} is already in the list")
            if len(self._state["domains"]) >= MAX_UI_DOMAINS:
                raise ValueError(f"limit of {MAX_UI_DOMAINS} domains added from the panel reached")
            self._state["domains"].append({"value": domain, "added_at": _stamp(self._clock())})
            self._write()
            self._audit("add", f"domain={domain}", by)
        return domain

    def remove_domain(self, value: str, *, by: str) -> None:
        try:
            domain = validate_domain(value)
        except ValueError as exc:
            raise ValueError(f"{value!r} is not in the list") from exc
        with self._lock:
            self._state = self._read()
            kept = [d for d in self._state["domains"] if d["value"] != domain]
            if len(kept) == len(self._state["domains"]):
                raise ValueError(f"{domain} is not in the list of domains added from the panel")
            self._state["domains"] = kept
            self._write()
            self._audit("remove", f"domain={domain}", by)

    def set_timeout(self, seconds: object, *, by: str) -> None:
        if seconds is None:
            value = None
        else:
            text = str(seconds).strip()
            if (
                isinstance(seconds, (bool, float))
                or not text.isdigit()
                or not MIN_TIMEOUT <= int(text) <= MAX_TIMEOUT
            ):
                raise ValueError(
                    f"the maximum time must be a whole number of seconds between {MIN_TIMEOUT} and {MAX_TIMEOUT}"
                )
            value = int(text)
        with self._lock:
            self._state = self._read()
            self._state["timeout_seconds"] = value
            self._write()
            self._audit("timeout", "seconds=" + ("default" if value is None else str(value)), by)

    def set_total_timeout(self, seconds: object, *, by: str) -> None:
        if seconds is None:
            value = None
        else:
            text = str(seconds).strip()
            if (
                isinstance(seconds, (bool, float))
                or not text.isdigit()
                or not MIN_TOTAL <= int(text) <= MAX_TOTAL
            ):
                raise ValueError(
                    f"the maximum total time must be a whole number of seconds between {MIN_TOTAL} and {MAX_TOTAL}"
                )
            value = int(text)
        with self._lock:
            self._state = self._read()
            self._state["total_timeout_seconds"] = value
            self._write()
            self._audit("total", "seconds=" + ("default" if value is None else str(value)), by)
