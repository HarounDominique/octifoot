"""Environment-driven settings. Fails fast so an unsafe config never starts."""

from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit

from spiderfoot_connector.allowlist import parse_allowlist
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
    ui_url: str = (
        ""  # address of the SpiderFoot UI as the analyst's browser reaches it; "" = no links
    )


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
        api_keys_file=(env.get("SPIDERFOOT_API_KEYS_FILE") or "").strip(),
        watch_interval_minutes=watch_interval,
        watch_max_per_cycle=_int(env, "SPIDERFOOT_WATCH_MAX_PER_CYCLE", 3, 1, 20),
    )
