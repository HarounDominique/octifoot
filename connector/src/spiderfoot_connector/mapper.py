"""Map SpiderFoot scan events to STIX 2.1 objects for OpenCTI.

Pure functions, no I/O. Only a small, clean subset of event types is mapped; everything
else is counted in ``MapResult.unmapped`` so nothing is dropped silently.
"""

import ipaddress
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import stix2
from pycti import Identity, Note, StixCoreRelationship

SOURCE_NAME = "SpiderFoot"
AFFILIATE_SCORE_DIVISOR = 2
_FEED_RE = re.compile(r"^(?P<feed>[^\[\n]+?)\s*\[(?P<value>[^\]\n]+)\]")
_DOMAIN_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9_]([a-z0-9_-]{0,61}[a-z0-9_])?\.)+[a-z]{2,63}$")

DOMAIN_EVENTS = {"INTERNET_NAME", "AFFILIATE_INTERNET_NAME"}
IP_EVENTS = {"IP_ADDRESS", "IPV6_ADDRESS"}
EMAIL_EVENTS = {"EMAILADDR"}
MAPPED_EVENTS = DOMAIN_EVENTS | IP_EVENTS | EMAIL_EVENTS

# Reputation signals. A flagged IP that is part of the output is labelled; subnet and
# co-host hits describe shared infrastructure, so they are only listed in the Note.
FLAG_IP_EVENT = "MALICIOUS_IPADDR"
FLAG_NAME_EVENT = "MALICIOUS_INTERNET_NAME"
LISTED_EVENTS = {"MALICIOUS_SUBNET", "MALICIOUS_COHOST"}
MALICIOUS_LABEL = "spiderfoot:malicious"
MAX_NOTE_LINES = 20

# Network ownership of imported IPs: IP -> netblock (NETBLOCK_*) -> AS (BGP_AS_MEMBER).
NETBLOCK_EVENTS = {"NETBLOCK_MEMBER", "NETBLOCKV6_MEMBER"}
AS_EVENT = "BGP_AS_MEMBER"
MAX_ASN = 4_294_967_295

# Who runs the target's registration, hosting, name servers and mail: text in the Note only.
INFRA_EVENTS = {
    "DOMAIN_REGISTRAR": "registrar",
    "PROVIDER_HOSTING": "hosting",
    "PROVIDER_DNS": "DNS",
    "PROVIDER_MAIL": "mail",
}
MAX_INFRA_VALUES = 5

# Every event type that ends up as an object, a label or a Note line. A scan profile must keep
# producing all of these (checked against SpiderFoot's module metadata in the profile tests).
IMPORTED_EVENTS = (
    MAPPED_EVENTS
    | {FLAG_IP_EVENT, FLAG_NAME_EVENT}
    | LISTED_EVENTS
    | NETBLOCK_EVENTS
    | {AS_EVENT}
    | set(INFRA_EVENTS)
)


@dataclass
class MapResult:
    objects: list[Any] = field(default_factory=list)
    unmapped: Counter = field(default_factory=Counter)
    false_positives: int = 0
    invalid: int = 0
    flags_skipped: int = 0
    name_flags_skipped: int = 0
    infra: dict[str, set[str]] = field(default_factory=dict)  # kind -> provider values
    discovered_domains: list[str] = field(default_factory=list)  # INTERNET_NAME, in order
    as_ips: dict[int, set[str]] = field(default_factory=dict)  # ASN -> imported IPs in it
    listed: list[tuple[str, str, str]] = field(default_factory=list)  # (event, feed, value)


def parse_feed_event(data: str) -> tuple[str, str] | None:
    """'Maltiverse [1.2.3.4]\\n...' -> ('Maltiverse', '1.2.3.4'); None if unparsable."""
    m = _FEED_RE.match(data.strip())
    return (m["feed"].strip(), m["value"].strip()) if m else None


def parse_asn(raw: str) -> int | None:
    """'13335' -> 13335; None unless an integer in 1..4294967295."""
    value = raw.strip()
    if not value.isdigit():
        return None
    number = int(value)
    return number if 1 <= number <= MAX_ASN else None


def _norm_domain(value: str) -> str:
    return value.strip().lower().rstrip(".")


def _is_domain(value: str) -> bool:
    return bool(_DOMAIN_RE.match(value))


def _ref(scan_id: str, module: str) -> list[dict[str, str]]:
    return [
        {
            "source_name": SOURCE_NAME,
            "external_id": scan_id,
            "description": f"SpiderFoot scan {scan_id}, module {module}",
        }
    ]


def _flag_ref(scan_id: str, feed: str, flag_module: str) -> dict[str, str]:
    return {
        "source_name": feed,
        "external_id": scan_id,
        "description": f"Flagged malicious by {feed} (SpiderFoot module {flag_module})",
    }


def _relationship(kind: str, source: Any, target: Any, identity_id: str, refs: list[dict]):
    return stix2.Relationship(
        id=StixCoreRelationship.generate_id(kind, source.id, target.id),
        relationship_type=kind,
        source_ref=source.id,
        target_ref=target.id,
        created_by_ref=identity_id,
        external_references=refs,
        allow_custom=True,
    )


def map_events(
    events: list[dict],
    *,
    target: str,
    scan_id: str,
    score: int,
    now: datetime,
) -> MapResult:
    """Convert SpiderFoot ``scanexportjsonmulti`` rows into STIX objects."""
    result = MapResult()
    target = _norm_domain(target)

    identity = stix2.Identity(
        id=Identity.generate_id(SOURCE_NAME, "system"),
        name=SOURCE_NAME,
        identity_class="system",
        description="SpiderFoot OSINT automation (passive enrichment)",
    )
    # Flagged hostnames are collected first so the label does not depend on event order.
    flagged_names: dict[str, list[tuple[str, str]]] = {}  # hostname -> [(feed, module)]
    for ev in events:
        if ev.get("event_type") != FLAG_NAME_EVENT or ev.get("false_positive"):
            continue
        parsed = parse_feed_event(str(ev.get("data", "")).strip())
        host = _norm_domain(parsed[1]) if parsed else ""
        if not _is_domain(host):
            result.invalid += 1
            continue
        flagged_names.setdefault(host, []).append((parsed[0], str(ev.get("module", "unknown"))))

    if target in flagged_names:
        # Same STIX id as the bare observable, so OpenCTI merges the label onto the analyst's object.
        refs = []
        for feed, flag_module in flagged_names[target]:
            refs += _ref(scan_id, flag_module) + [_flag_ref(scan_id, feed, flag_module)]
        target_obj = stix2.DomainName(
            value=target,
            allow_custom=True,
            x_opencti_labels=[MALICIOUS_LABEL],
            x_opencti_external_references=refs,
        )
    else:
        target_obj = stix2.DomainName(value=target)
    objects: dict[str, Any] = {identity.id: identity, target_obj.id: target_obj}
    domains: dict[str, Any] = {target: target_obj}
    emitted: set[tuple[str, str]] = set()

    def observable(
        factory, value: str, module: str, obs_score: int, flags: list[tuple[str, str]] = ()
    ):
        refs = _ref(scan_id, module)
        extra = {}
        if flags:
            refs += [_flag_ref(scan_id, feed, flag_module) for feed, flag_module in flags]
            extra["x_opencti_labels"] = [MALICIOUS_LABEL]
        obj = factory(
            value=value,
            allow_custom=True,
            x_opencti_score=obs_score,
            x_opencti_created_by_ref=identity.id,
            x_opencti_external_references=refs,
            **extra,
        )
        objects.setdefault(obj.id, obj)
        return objects[obj.id]

    def relate(kind: str, source: Any, tgt: Any, module: str) -> None:
        rel = _relationship(kind, source, tgt, identity.id, _ref(scan_id, module))
        objects.setdefault(rel.id, rel)

    def autonomous_system(number: int, module: str):
        obj = stix2.AutonomousSystem(
            number=number,
            allow_custom=True,
            x_opencti_created_by_ref=identity.id,
            x_opencti_external_references=_ref(scan_id, module),
        )
        objects.setdefault(obj.id, obj)
        return objects[obj.id]

    pending_ips: list[tuple[str, str, str]] = []
    flagged: dict[str, list[tuple[str, str]]] = {}  # ip -> [(feed, module)]
    block_of_ip: dict[str, str] = {}  # ip -> netblock CIDR
    as_of_block: dict[str, tuple[int, str]] = {}  # netblock CIDR -> (ASN, module)

    for ev in events:
        etype = ev.get("event_type", "")
        if ev.get("false_positive"):
            result.false_positives += 1
            continue
        data = str(ev.get("data", "")).strip()
        module = str(ev.get("module", "unknown"))

        if etype == FLAG_NAME_EVENT:
            continue  # collected before the loop
        if etype in INFRA_EVENTS:
            value = _infra_value(etype, data)
            if value:
                result.infra.setdefault(INFRA_EVENTS[etype], set()).add(value)
            else:
                result.invalid += 1
            continue
        if etype == FLAG_IP_EVENT or etype in LISTED_EVENTS:
            parsed = parse_feed_event(data)
            if parsed is None:
                result.invalid += 1
            elif etype in LISTED_EVENTS:
                result.listed.append((etype, *parsed))
            else:
                try:
                    flagged.setdefault(str(ipaddress.ip_address(parsed[1])), []).append(
                        (parsed[0], module)
                    )
                except ValueError:
                    result.invalid += 1
            continue
        if etype in NETBLOCK_EVENTS:
            try:
                block_of_ip[str(ipaddress.ip_address(str(ev.get("source_data", "")).strip()))] = (
                    data
                )
            except ValueError:
                result.invalid += 1
            continue
        if etype == AS_EVENT:
            number = parse_asn(data)
            if number is None:
                result.invalid += 1
            else:
                as_of_block[str(ev.get("source_data", "")).strip()] = (number, module)
            continue
        if etype not in MAPPED_EVENTS:
            result.unmapped[etype] += 1
            continue

        if etype in DOMAIN_EVENTS:
            name = _norm_domain(data)
            if not _is_domain(name):
                result.invalid += 1
                continue
            if name == target or (etype, name) in emitted:
                continue
            emitted.add((etype, name))
            if etype == "INTERNET_NAME":
                result.discovered_domains.append(name)
            obs_score = score // AFFILIATE_SCORE_DIVISOR if etype.startswith("AFFILIATE") else score
            domains[name] = observable(
                stix2.DomainName, name, module, obs_score, flagged_names.get(name, [])
            )
            relate("related-to", domains[name], target_obj, module)

        elif etype in EMAIL_EVENTS:
            addr = data.lower()
            if "@" not in addr:
                result.invalid += 1
                continue
            if (etype, addr) in emitted:
                continue
            emitted.add((etype, addr))
            email = observable(stix2.EmailAddress, addr, module, score)
            relate("related-to", email, target_obj, module)

        else:  # IP_ADDRESS / IPV6_ADDRESS — resolved after all domains are known
            pending_ips.append((data, _norm_domain(str(ev.get("source_data", ""))), module))

    for data, source_host, module in pending_ips:
        try:
            ip = ipaddress.ip_address(data)
        except ValueError:
            result.invalid += 1
            continue
        key = ("IP_ADDRESS", f"{source_host}>{ip}")
        if key in emitted:
            continue
        emitted.add(key)
        factory = stix2.IPv4Address if ip.version == 4 else stix2.IPv6Address
        ip_obj = observable(factory, str(ip), module, score, flagged.get(str(ip), []))
        relate("resolves-to", domains.get(source_host, target_obj), ip_obj, module)

        # A fact about the IP's network, never an ownership claim about the target.
        found = as_of_block.get(block_of_ip.get(str(ip), ""))
        if found:
            number, as_module = found
            relate("belongs-to", ip_obj, autonomous_system(number, as_module), as_module)
            result.as_ips.setdefault(number, set()).add(str(ip))

    emitted_ips = {o.value for o in objects.values() if o.type in ("ipv4-addr", "ipv6-addr")}
    result.flags_skipped = sum(1 for ip in flagged if ip not in emitted_ips)
    result.name_flags_skipped = sum(
        1 for name in flagged_names if name != target and name not in domains
    )

    summary = _summary(result, objects, scan_id, target)
    note = stix2.Note(
        id=Note.generate_id(now.isoformat(), summary),
        created=now,
        modified=now,
        content=summary,
        abstract=f"SpiderFoot scan {scan_id} summary",
        object_refs=[target_obj.id],
        created_by_ref=identity.id,
        allow_custom=True,
    )
    objects[note.id] = note
    result.objects = list(objects.values())
    return result


def _infra_value(etype: str, data: str) -> str:
    value = data.strip()
    if etype == "PROVIDER_HOSTING":
        value = value.split(": ", 1)[0].strip()  # "name: https://url" -> "name"
    elif etype in ("PROVIDER_DNS", "PROVIDER_MAIL"):
        value = value.lower().rstrip(".")
    return value


def _infra_line(infra: dict[str, set[str]]) -> str:
    parts = []
    for kind in INFRA_EVENTS.values():
        values = sorted(infra.get(kind, ()))
        if not values:
            continue
        shown = ", ".join(values[:MAX_INFRA_VALUES])
        if len(values) > MAX_INFRA_VALUES:
            shown += f" and {len(values) - MAX_INFRA_VALUES} more"
        parts.append(f"{kind}: {shown}")
    return "Infrastructure (as reported by SpiderFoot): " + "; ".join(parts) if parts else ""


def _summary(result: MapResult, objects: dict[str, Any], scan_id: str, target: str) -> str:
    kinds = Counter(o.type for o in objects.values() if o.type.endswith(("-name", "-addr")))
    lines = [
        f"SpiderFoot scan {scan_id} for {target}.",
        "Mapped: " + (", ".join(f"{k}={v}" for k, v in sorted(kinds.items())) or "nothing"),
    ]
    if result.as_ips:
        systems = ", ".join(
            f"AS{number} ({len(ips)} {'IP' if len(ips) == 1 else 'IPs'})"
            for number, ips in sorted(result.as_ips.items())
        )
        lines.append(f"Autonomous systems: {systems}")
    infra = _infra_line(result.infra)
    if infra:
        lines.append(infra)
    if result.unmapped:
        lines.append(
            "Unmapped event types (not imported): "
            + ", ".join(f"{k}={v}" for k, v in sorted(result.unmapped.items()))
        )
    if result.listed:
        lines.append("Reputation hits on shared infrastructure (not imported as objects):")
        hits = sorted(f"{feed}: {value} ({etype})" for etype, feed, value in result.listed)
        lines += [f"- {h}" for h in hits[:MAX_NOTE_LINES]]
        if len(hits) > MAX_NOTE_LINES:
            lines.append(f"- and {len(hits) - MAX_NOTE_LINES} more")
    if result.flags_skipped:
        lines.append(f"Malicious flags on IPs not in this import: {result.flags_skipped}")
    if result.name_flags_skipped:
        lines.append(
            f"Malicious flags on hostnames not in this import: {result.name_flags_skipped}"
        )
    lines.append(
        f"False positives skipped: {result.false_positives}; invalid values: {result.invalid}"
    )
    return "\n".join(lines)
