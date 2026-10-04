"""Environment-driven settings. Fails fast so an unsafe config never starts."""

from collections.abc import Mapping
from dataclasses import dataclass

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
    )
