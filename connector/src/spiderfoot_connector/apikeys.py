"""Free API keys for the SpiderFoot modules that use them.

The owner supplies a JSON file ``{"sfp_virustotal": "KEY", "sfp_abstractapi:ipgeolocation_api_key": "KEY"}``. Before an
enrichment the keys are written to SpiderFoot through its settings API and verified by reading them back.

SpiderFoot reads option names as ``module.<mod>.<opt>`` but writes them as ``<mod>:<opt>``, and answers ``SUCCESS`` to a write
under any other name without storing anything. A key that is silently not stored is the worst failure here, so every key is
checked against the options SpiderFoot reports, written under the right name and compared after a read-back. Key values are
never logged, raised in an error, imported or printed; only module and option names are.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from spiderfoot_connector.config import ConfigError

MAX_VALUE_LENGTH = 512
_NEVER = frozenset({"invasive", "tool"})  # a key never turns an active module on


class SettingsClient(Protocol):
    def get_options(self) -> tuple[str, dict[str, Any]]: ...

    def save_options(self, options: dict[str, str], token: str) -> None: ...


@dataclass(frozen=True)
class KeyRing:
    """Option name (``sfp_x:api_key``) -> key value. Values never appear in ``repr``."""

    entries: dict[str, str] = field(default_factory=dict, repr=False)

    @property
    def modules(self) -> frozenset[str]:
        return frozenset(name.split(":", 1)[0] for name in self.entries)

    def __repr__(self) -> str:
        return f"KeyRing(options={sorted(self.entries)}, values=hidden)"

    __str__ = __repr__


@dataclass(frozen=True)
class ApplyResult:
    applied: frozenset[str]  # modules whose key is stored and verified
    failed: list[str]  # option names only


def _option_name(raw: str) -> tuple[str, str] | None:
    module, sep, option = raw.partition(":")
    if sep and not (module and option):
        return None
    return (module, option) if sep else (module, "api_key")


def load_keyring(path: str, snapshot: dict[str, dict]) -> KeyRing:
    """Read and validate the key file; every error names the entry, never a value."""
    where = "SPIDERFOOT_API_KEYS_FILE"
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"{where} cannot be read ({type(exc).__name__}: {path})") from exc
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ConfigError(f"{where} is not valid JSON") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{where} must contain a JSON object of module names and keys")

    entries: dict[str, str] = {}
    for raw_name, value in data.items():
        parsed = _option_name(str(raw_name))
        if parsed is None:
            raise ConfigError(f"{where}: invalid entry name {raw_name!r}")
        module, option = parsed
        meta = snapshot.get(module)
        if meta is None:
            raise ConfigError(f"{where}: unknown SpiderFoot module {module!r}")
        flags = set(meta["flags"])
        if "apikey" not in flags:
            raise ConfigError(f"{where}: module {module!r} does not use an API key")
        if flags & _NEVER:
            raise ConfigError(
                f"{where}: module {module!r} is an active module; a key does not enable it"
            )
        if not isinstance(value, str) or not value.strip():
            raise ConfigError(f"{where}: the key for {raw_name!r} must be a non-empty string")
        value = value.strip()
        if len(value) > MAX_VALUE_LENGTH or any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise ConfigError(
                f"{where}: the key for {raw_name!r} is too long or contains control characters"
            )
        entries[f"{module}:{option}"] = value
    return KeyRing(entries)


def apply_keys(ring: KeyRing, client: SettingsClient) -> ApplyResult:
    """Store each key in SpiderFoot and verify it; never raises, never reveals a value."""
    applied: set[str] = set()
    failed: list[str] = []
    for name, value in ring.entries.items():
        module, _, option = name.partition(":")
        read_name = f"module.{module}.{option}"
        try:
            token, options = client.get_options()
            if read_name not in options:
                failed.append(name)  # SpiderFoot would answer SUCCESS and store nothing
                continue
            if options[read_name] != value:
                client.save_options({name: value}, token)
                _, after = client.get_options()
                if after.get(read_name) != value:
                    failed.append(name)
                    continue
        except Exception:  # noqa: BLE001  the settings API must never fail an enrichment
            failed.append(name)
            continue
        applied.add(module)
    return ApplyResult(frozenset(applied), failed)
