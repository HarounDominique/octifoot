"""Event catalogue: what octifoot does with every SpiderFoot v4.0 event type, and why.

The catalogue is data derived from three inputs (SpiderFoot's own event-type table, its module
metadata, and counts of what real passive scans produced) plus the decisions below. It is
committed as ``data/event_catalogue.json`` and rendered to ``docs/event-catalogue.md``; tests
fail if either drifts from this module or from the mapper, so a decision cannot be forgotten.
"""

import json
import re
from collections import defaultdict
from importlib import resources
from typing import Any

ALLOWED_STATUSES = frozenset({"imported", "planned", "declined", "blocked", "no-data"})
_EXCLUDED_FLAGS = frozenset({"apikey", "invasive", "tool"})

# status "imported": how the mapper uses the type today -> (action, OpenCTI/STIX target, rationale)
IMPORTED = {
    "INTERNET_NAME": (
        "object",
        "domain-name",
        "The target's own hostnames; `related-to` the scanned domain.",
    ),
    "IP_ADDRESS": (
        "object",
        "ipv4-addr",
        "Resolved from a hostname that is the target's; `resolves-to`.",
    ),
    "IPV6_ADDRESS": ("object", "ipv6-addr", "Same as IPv4."),
    "EMAILADDR": (
        "object",
        "email-addr",
        "Addresses found for the target itself; `related-to` the domain.",
    ),
    "NETBLOCK_MEMBER": (
        "object",
        "autonomous-system",
        "Used to link each imported IP to its AS; the netblock itself is not an object.",
    ),
    "NETBLOCKV6_MEMBER": ("object", "autonomous-system", "Same as IPv4 netblocks."),
    "BGP_AS_MEMBER": (
        "object",
        "autonomous-system",
        "AS number only; `belongs-to` from each imported IP.",
    ),
    "MALICIOUS_IPADDR": (
        "label",
        "ipv4-addr / ipv6-addr",
        "Label `spiderfoot:malicious` plus one reference per feed, only on imported IPs.",
    ),
    "MALICIOUS_INTERNET_NAME": (
        "label",
        "domain-name",
        "Same label on imported hostnames and on the target itself.",
    ),
    "MALICIOUS_SUBNET": (
        "note",
        "note",
        "Shared infrastructure: listed in the scan Note, never an object.",
    ),
    "MALICIOUS_COHOST": (
        "note",
        "note",
        "Shared infrastructure: listed in the scan Note, never an object.",
    ),
    "DOMAIN_REGISTRAR": ("note", "note", "`Infrastructure` line of the Note."),
    "PROVIDER_HOSTING": ("note", "note", "`Infrastructure` line of the Note."),
    "PROVIDER_DNS": ("note", "note", "`Infrastructure` line of the Note."),
    "PROVIDER_MAIL": ("note", "note", "`Infrastructure` line of the Note."),
}

# Decisions backed by what real passive scans of three domains showed (see the task notes).
DECISIONS = {
    "DOMAIN_WHOIS": (
        "planned",
        "note",
        "whois-dns-notes",
        "Registration facts of the target (creation, expiry, update, status) are CTI context (domain age) with no STIX field: one Note line.",
    ),
    "DNS_TEXT": (
        "planned",
        "note",
        "whois-dns-notes",
        "TXT records of the target (SPF, DMARC, verification tokens) say who may send mail for it: one Note line.",
    ),
    "WEB_ANALYTICS_ID": (
        "planned",
        "note",
        "whois-dns-notes",
        "Observed values were domain-verification tokens from the target's own TXT records; a pivot, summarised in the same Note line.",
    ),
    "SSL_CERTIFICATE_RAW": (
        "planned",
        "x509-certificate",
        "x509-certificates",
        "Certificates issued for the target's names (from crt.sh) are standard STIX x509-certificate objects with the SANs as context.",
    ),
    "COMPANY_NAME": (
        "declined",
        "",
        "",
        "Real values were the registry, the registrar and a privacy proxy named in the WHOIS text, not the target's owner: importing them would misattribute.",
    ),
    "PHYSICAL_ADDRESS": (
        "declined",
        "",
        "",
        "Real values were the head-office addresses of the registry operator (via GLEIF), not the target's.",
    ),
    "LEI": (
        "declined",
        "",
        "",
        "Real values were the registry operator's legal entity identifier, not the target's.",
    ),
    "PHONE_NUMBER": (
        "declined",
        "",
        "",
        "Real values were the registrar's contact number from WHOIS; personal data that is not the target's.",
    ),
    "DOMAIN_NAME": (
        "declined",
        "",
        "",
        "Observed values were the target itself or its parent: no new information.",
    ),
    "DOMAIN_NAME_PARENT": (
        "declined",
        "",
        "",
        "Observed value was the parent domain of a third party's hostname (a provider), not of the target.",
    ),
    "COUNTRY_NAME": (
        "declined",
        "",
        "",
        "Derived from the TLD or prefix of co-hosted sites and phone numbers: describes third parties.",
    ),
    "RAW_DNS_RECORDS": (
        "declined",
        "",
        "",
        "Raw zone text; the NS and MX hosts are already in the Infrastructure line and the TXT records are covered by `DNS_TEXT`.",
    ),
    "RAW_RIR_DATA": (
        "declined",
        "",
        "",
        "Raw registry text; the useful part (AS and netblock) already arrives as structured events.",
    ),
    "SEARCH_ENGINE_WEB_CONTENT": (
        "declined",
        "",
        "",
        "Raw search-engine snippets: unstructured and about third parties.",
    ),
    "PUBLIC_CODE_REPO": (
        "declined",
        "",
        "",
        "Matches repositories by name (unrelated people's projects named like the domain); would credit their work to the target.",
    ),
}

_POLICY = (
    (
        "AFFILIATE_",
        "A third party's data (mail providers, partners, co-hosts); never attributed to the target.",
    ),
    ("MALICIOUS_AFFILIATE_", "A flag on a third party's host; never attributed to the target."),
    (
        "CO_HOSTED_",
        "Co-hosted sites share infrastructure with the target; they are not the target's.",
    ),
    (
        "BLACKLISTED_",
        "Not equivalent to `MALICIOUS_*`: some modules emit it for content filters (SpiderFoot's Cloudflare Family module), which would mislabel benign hosts.",
    ),
)

# Suggested OpenCTI/STIX shape for families nothing in our scans has produced yet.
_TARGETS = (
    (r"^(TCP|UDP)_PORT_OPEN", "Note line (no port entity in OpenCTI) or network-traffic"),
    (
        r"^(WEBSERVER_|SOFTWARE_USED|OPERATING_SYSTEM|DEVICE_TYPE)",
        "software observable or Note line",
    ),
    (r"^VULNERABILITY_", "vulnerability (CVE) related to the IP, with the feed as reference"),
    (r"^SSL_CERTIFICATE_", "x509-certificate"),
    (r"^(ACCOUNT_EXTERNAL|SOCIAL_MEDIA)", "user-account (privacy review first)"),
    (r"^(BITCOIN|ETHEREUM)_", "cryptocurrency-wallet"),
    (r"^(GEOINFO|PHYSICAL_COORDINATES)", "location, only for the target's own IPs"),
    (
        r"^(HUMAN_NAME|USERNAME|EMAILADDR_)",
        "individual / email-addr (privacy and attribution review first)",
    ),
    (r"^(LEAKSITE|DARKNET|HACKED|BREACH)", "Note line plus label (privacy review first)"),
    (r"^(URL_|LINKED_URL)", "url observable"),
    (r"^(HASH|RAW_FILE|JUNK_FILE|PGP_KEY|INTERESTING_FILE)", "file observable or Note line"),
    (
        r"^(CLOUD_STORAGE_BUCKET)",
        "Note line; `_OPEN` is a real finding (see ab-validity-and-cloud-bucket-deny)",
    ),
)


def classify_needs(event_type: str, meta: dict[str, dict], lean: set[str]) -> str:
    """What it takes to get SpiderFoot to emit ``event_type`` with this connector's configuration."""
    producers = {n: m for n, m in meta.items() if event_type in m["produced"]}
    if not producers:
        return "none"
    if any(n in lean for n in producers):
        return "passive"
    keyless_passive = [
        m
        for m in producers.values()
        if "Passive" in m["useCases"] and not _EXCLUDED_FLAGS & set(m["flags"])
    ]
    if keyless_passive:
        return "denied-module"
    if any(
        "Passive" in m["useCases"]
        and "apikey" in m["flags"]
        and not {"invasive", "tool"} & set(m["flags"])
        for m in producers.values()
    ):
        return "api-key"
    return "active"


def _target_for(event_type: str) -> str:
    return next((t for pattern, t in _TARGETS if re.match(pattern, event_type)), "")


def build_catalogue(
    types: dict[str, dict],
    meta: dict[str, dict],
    lean: set[str],
    observed: dict[str, dict],
    imported: set[str] | frozenset[str],
) -> list[dict[str, Any]]:
    entries = []
    for tid in sorted(types):
        info = types[tid]
        needs = classify_needs(tid, meta, lean)
        modules = sorted(n for n, m in meta.items() if tid in m["produced"])
        seen = observed.get(tid, {"events": 0, "targets": 0})
        entry = {
            "id": tid,
            "description": info["description"],
            "category": info["category"],
            "needs": needs,
            "modules": modules,
            "observed_events": seen["events"],
            "observed_targets": seen["targets"],
            "status": "",
            "action": "",
            "target": "",
            "slice": "",
            "rationale": "",
        }
        policy = next((why for prefix, why in _POLICY if tid.startswith(prefix)), None)
        if tid in imported:
            action, target, why = IMPORTED[tid]
            entry.update(status="imported", action=action, target=target, rationale=why)
        elif tid in DECISIONS:
            status, target, slice_, why = DECISIONS[tid]
            entry.update(
                status=status,
                action="decline"
                if status == "declined"
                else ("object" if target.startswith("x509") else "note"),
                target=target,
                slice=slice_,
                rationale=why,
            )
        elif policy:
            entry.update(status="declined", action="decline", rationale=policy)
        elif tid == "ROOT" or info["category"] == "INTERNAL":
            entry.update(
                status="declined", action="decline", rationale="SpiderFoot-internal event."
            )
        elif needs == "none":
            entry.update(
                status="declined",
                action="decline",
                rationale="No SpiderFoot v4.0 module produces it.",
            )
        elif needs in {"api-key", "active"}:
            hint = (
                "an API key for one of the producing modules"
                if needs == "api-key"
                else "a non-passive module (needs the owner's explicit permission and SPIDERFOOT_ALLOW_ACTIVE)"
            )
            entry.update(
                status="blocked",
                action="map-later",
                target=_target_for(tid),
                rationale=f"Not produced by this configuration: needs {hint}. Map it when it can be produced and verified.",
            )
        else:  # passive, or produced only by a deny-listed keyless module
            reason = (
                "deny-listed module"
                if needs == "denied-module"
                else "no event of this type in any recorded scan"
            )
            entry.update(
                status="no-data",
                action="map-later",
                target=_target_for(tid),
                rationale=f"Producible with the current profile but never seen ({reason}); decide when real data exists.",
            )
        entries.append(entry)
    return entries


def load_catalogue() -> list[dict[str, Any]]:
    return json.loads(
        resources.files("spiderfoot_connector.data").joinpath("event_catalogue.json").read_text()
    )


def render_markdown(entries: list[dict[str, Any]], observed_meta: dict[str, Any]) -> str:
    by_status: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        by_status[e["status"]].append(e)
    scans, targets = observed_meta["scans"], observed_meta["targets"]
    seen = sum(1 for e in entries if e["observed_events"])
    lines = [
        "# Event catalogue",
        "",
        "What octifoot does with each of the 172 event types SpiderFoot v4.0 can emit, and why. Generated by",
        "`connector/tools/build_catalogue.py` from SpiderFoot's event-type table, its module metadata, counts of what",
        f"{scans} real passive scans of {targets} domains produced, and the decisions in `catalogue.py`; tests fail if this",
        "page drifts from the mapper. Do not edit it by hand.",
        "",
        f"Only **{seen}** of the 172 types appeared in those scans: the passive, keyless configuration produces a small",
        "part of what SpiderFoot can find. Most of the rest needs an API key or an active module.",
        "",
        "| Status | Types | Meaning |",
        "|---|---|---|",
    ]
    meaning = {
        "imported": "the mapper turns it into an object, label or Note line today",
        "planned": "seen in real scans and worth importing; a named slice will do it",
        "declined": "decided against, with the reason (mostly: it describes a third party or is raw text)",
        "blocked": "not produced by this configuration: needs an API key or an active module",
        "no-data": "producible with the current profile but never seen; decide when real data exists",
    }
    for status in ("imported", "planned", "declined", "blocked", "no-data"):
        lines.append(f"| {status} | {len(by_status[status])} | {meaning[status]} |")

    def table(title: str, status: str, cols: list[str]) -> None:
        rows = by_status[status]
        if not rows:
            return
        lines.extend(
            [
                "",
                f"## {title}",
                "",
                "| Event type | " + " | ".join(cols) + " |",
                "|---|" + "---|" * len(cols),
            ]
        )
        for e in rows:
            cells = {
                "Becomes": f"{e['action']}: {e['target']}" if e["target"] else e["action"],
                "Slice": e["slice"],
                "Seen": f"{e['observed_events']} events" if e["observed_events"] else "no",
                "Why": e["rationale"],
                "Needs": e["needs"],
                "Suggested shape": e["target"] or "-",
                "Example modules": ", ".join(e["modules"][:3]) or "-",
            }
            lines.append(
                f"| `{e['id']}` | " + " | ".join(cells[c].replace("|", "/") for c in cols) + " |"
            )

    table("Imported", "imported", ["Becomes", "Seen", "Why"])
    table("Planned", "planned", ["Becomes", "Slice", "Seen", "Why"])
    table("Declined", "declined", ["Seen", "Why"])
    table(
        "Blocked: needs an API key or an active module",
        "blocked",
        ["Needs", "Suggested shape", "Example modules"],
    )
    table("No data yet", "no-data", ["Needs", "Suggested shape", "Example modules"])

    unlock: dict[str, set[str]] = defaultdict(set)
    for e in by_status["blocked"]:
        if e["needs"] == "api-key":
            for m in e["modules"]:
                unlock[m].add(e["id"])
    if unlock:
        lines.extend(
            [
                "",
                "## What an API key would unlock",
                "",
                "Blocked event types per keyed module (most first). Which keys are worth getting is the owner's decision.",
                "",
                "| Module | Blocked types it could produce |",
                "|---|---|",
            ]
        )
        for m, ids in sorted(unlock.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:12]:
            lines.append(f"| `{m}` | {len(ids)} |")
    return "\n".join(lines) + "\n"
