"""Environment-driven settings. Fails fast so an unsafe config never starts."""

import ipaddress
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from spiderfoot_connector.allowlist import parse_allowlist, validate_domain
from spiderfoot_connector.profiles import PROFILES

PASSIVE_USECASE = "passive"
USECASES = frozenset({"all", "footprint", "investigate", PASSIVE_USECASE})
_TRUE = frozenset({"1", "true", "yes", "on"})


class ConfigError(ValueError):
    """Raised when the configuration is missing, invalid or unsafe."""


@dataclass(frozen=True)
class Settings:
    base_url: str
    allowed_domains: frozenset[str]
    usecase: str
    timeout_seconds: int
    poll_seconds: int
    score: int
    max_depth: int = 0
    max_scans: int = 5
    profile: str = "full"
    api_keys_file: str = ""  # path to the JSON file of free API keys; "" = none
    watch_interval_minutes: int = 0  # 0 = automatic re-analysis off
    watch_max_per_cycle: int = 3
    state_dir: str = (
        ""  # where the control panel keeps its settings and audit log; "" = no run-time settings
    )
    ui_url: str = (
        ""  # address of the SpiderFoot UI as the analyst's browser reaches it; "" = no links
    )
    ui_token: str = field(default="", repr=False)  # control panel secret; "" = panel off
    ui_port: int = 8099
    ui_bind: str = "127.0.0.1"
    ui_lang: str = "en"


def _int(env: Mapping[str, str], key: str, default: int, lo: int, hi: int) -> int:
    raw = env.get(key)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{key} must be an integer, got {raw!r}") from exc
    if not lo <= value <= hi:
        raise ConfigError(f"{key} must be between {lo} and {hi}, got {value}")
    return value


def load_settings(env: Mapping[str, str]) -> Settings:
    base_url = (env.get("SPIDERFOOT_URL") or "").strip().rstrip("/")
    if not base_url:
        raise ConfigError("SPIDERFOOT_URL is required")

    allowed = parse_allowlist(env.get("SPIDERFOOT_ALLOWED_DOMAINS"))
    for entry in sorted(allowed):
        try:
            validate_domain(entry)
        except ValueError as exc:
            raise ConfigError(
                f"SPIDERFOOT_ALLOWED_DOMAINS: {entry!r} is not usable: {exc}"
            ) from exc
    if not allowed:
        raise ConfigError(
            "SPIDERFOOT_ALLOWED_DOMAINS is required: list the domains you are authorized to scan"
        )

    usecase = (env.get("SPIDERFOOT_USECASE") or PASSIVE_USECASE).strip().lower()
    if usecase not in USECASES:
        raise ConfigError(f"SPIDERFOOT_USECASE must be one of {sorted(USECASES)}, got {usecase!r}")
    allow_active = (env.get("SPIDERFOOT_ALLOW_ACTIVE") or "").strip().lower() in _TRUE
    if usecase != PASSIVE_USECASE and not allow_active:
        raise ConfigError(
            f"SPIDERFOOT_USECASE={usecase} may run active modules; "
            "set SPIDERFOOT_ALLOW_ACTIVE=true to opt in explicitly"
        )

    # lean was measured faster at identical imported objects (SPEC-fast-scan-profile, Deviations);
    # it only exists for the passive use case, so any other use case keeps the full module set.
    default_profile = "lean" if usecase == PASSIVE_USECASE else "full"
    watch_raw = (env.get("SPIDERFOOT_WATCH_INTERVAL_MINUTES") or "0").strip()
    try:
        watch_interval = int(watch_raw)
    except ValueError:
        watch_interval = -1
    if watch_interval != 0 and not 5 <= watch_interval <= 10080:
        raise ConfigError(
            "SPIDERFOOT_WATCH_INTERVAL_MINUTES must be 0 (off) or between 5 and 10080 minutes, "
            f"got {watch_raw!r}"
        )
    ui_token = (env.get("OCTIFOOT_UI_TOKEN") or "").strip()
    if ui_token and len(ui_token) < 16:
        raise ConfigError("OCTIFOOT_UI_TOKEN must be at least 16 characters")
    if ui_token and not (env.get("OCTIFOOT_STATE_DIR") or "").strip():
        raise ConfigError(
            "OCTIFOOT_UI_TOKEN needs OCTIFOOT_STATE_DIR (where the panel keeps its settings)"
        )
    ui_lang = (env.get("OCTIFOOT_UI_LANG") or "en").strip().lower()
    if ui_lang not in ("en", "es"):
        raise ConfigError(f"OCTIFOOT_UI_LANG must be en or es, got {ui_lang!r}")
    ui_bind = (env.get("OCTIFOOT_UI_BIND") or "127.0.0.1").strip()
    try:
        ipaddress.ip_address(ui_bind)
    except ValueError as exc:
        raise ConfigError(f"OCTIFOOT_UI_BIND must be an IP address, got {ui_bind!r}") from exc
    ui_url = (env.get("SPIDERFOOT_UI_URL") or "").strip().rstrip("/")
    if ui_url:
        parts = urlsplit(ui_url)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            raise ConfigError(
                f"SPIDERFOOT_UI_URL must be an http(s) URL with a host, got {ui_url!r}"
            )
    profile = (env.get("SPIDERFOOT_PROFILE") or default_profile).strip().lower()
    if profile not in PROFILES:
        raise ConfigError(f"SPIDERFOOT_PROFILE must be one of {list(PROFILES)}, got {profile!r}")
    if profile == "lean" and usecase != PASSIVE_USECASE:
        raise ConfigError("SPIDERFOOT_PROFILE=lean requires SPIDERFOOT_USECASE=passive")

    return Settings(
        base_url=base_url,
        allowed_domains=allowed,
        usecase=usecase,
        timeout_seconds=_int(env, "SPIDERFOOT_TIMEOUT_SECONDS", 900, 1, 86400),
        poll_seconds=_int(env, "SPIDERFOOT_POLL_SECONDS", 10, 1, 600),
        score=_int(env, "SPIDERFOOT_SCORE", 30, 0, 100),
        max_depth=_int(env, "SPIDERFOOT_MAX_DEPTH", 0, 0, 3),
        max_scans=_int(env, "SPIDERFOOT_MAX_SCANS", 5, 1, 20),
        profile=profile,
        ui_url=ui_url,
        ui_token=ui_token,
        ui_port=_int(env, "OCTIFOOT_UI_PORT", 8099, 1, 65535),
        ui_bind=ui_bind,
        ui_lang=ui_lang,
        state_dir=(env.get("OCTIFOOT_STATE_DIR") or "").strip(),
        api_keys_file=(env.get("SPIDERFOOT_API_KEYS_FILE") or "").strip(),
        watch_interval_minutes=watch_interval,
        watch_max_per_cycle=_int(env, "SPIDERFOOT_WATCH_MAX_PER_CYCLE", 3, 1, 20),
    )
