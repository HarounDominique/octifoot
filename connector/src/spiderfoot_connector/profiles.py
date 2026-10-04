"""Scan profiles: which SpiderFoot modules to run.

``full`` runs SpiderFoot's whole "Passive" group. ``lean`` runs an explicit module list
derived from SpiderFoot's own module metadata: passive, keyless, non-invasive modules reachable
from the target, minus a small deny-list of modules that only feed data we discard.
"""

import json
from functools import lru_cache
from importlib import resources

PROFILES = ("full", "lean")
# Evidence-based. robtex finds co-hosted sites and countryname processes them, feeding a chain
# (dnsresolve -> whois -> email) whose output is discarded (SPEC-fast-scan-profile). The four
# cloud-storage modules guess thousands of bucket names against third-party storage hosts and
# their events are not imported; in scan E664397D sfp_s3bucket was the only module still running
# 164 s after all others had finished (SPEC-ab-validity-and-cloud-bucket-deny).
DENY = frozenset(
    {
        "sfp_robtex",
        "sfp_countryname",
        "sfp_s3bucket",
        "sfp_azureblobstorage",
        "sfp_digitaloceanspace",
        "sfp_googleobjectstorage",
    }
)
# Lean-profile modules that really enumerate subdomains (others, like sfp_flickr or sfp_apple_itunes,
# only emit hostnames as a by-product). Used to say when subdomain discovery may be incomplete.
SUBDOMAIN_SOURCES = frozenset(
    {
        "sfp_crt",
        "sfp_crobat_api",
        "sfp_dnsdumpster",
        "sfp_dnsgrep",
        "sfp_mnemonic",
        "sfp_open_passive_dns_database",
        "sfp_sublist3r",
        "sfp_threatminer",
        "sfp_urlscan",
    }
)
_SEED_EVENTS = frozenset({"ROOT", "DOMAIN_NAME", "INTERNET_NAME"})
_EXCLUDED_FLAGS = frozenset({"apikey", "invasive", "tool"})


def derive_lean(meta: dict[str, dict], deny: frozenset[str]) -> list[str]:
    """Passive, keyless, non-invasive modules reachable from the target, minus deny."""
    eligible = {
        name
        for name, m in meta.items()
        if "Passive" in m["useCases"] and not _EXCLUDED_FLAGS & set(m["flags"]) and name not in deny
    }
    seen = set(_SEED_EVENTS)
    chosen: set[str] = set()
    changed = True
    while changed:
        changed = False
        for name in sorted(eligible - chosen):
            watched = set(meta[name]["watched"])
            if "*" in watched or watched & seen:
                chosen.add(name)
                seen |= set(meta[name]["produced"])
                changed = True
    return sorted(chosen)


def _read(name: str) -> object:
    return json.loads(resources.files("spiderfoot_connector.data").joinpath(name).read_text())


@lru_cache(maxsize=1)
def load_snapshot() -> dict[str, dict]:
    """SpiderFoot v4.0 module metadata (useCases, flags, watched/produced event types)."""
    return _read("sf_modules_v4.0.json")  # type: ignore[return-value]


@lru_cache(maxsize=1)
def lean_modules() -> list[str]:
    """The committed lean module list (regenerate when the SpiderFoot pin changes)."""
    return _read("lean_modules.json")  # type: ignore[return-value]
