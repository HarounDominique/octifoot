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
_DOMAIN_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9_]([a-z0-9_-]{0,61}[a-z0-9_])?\.)+[a-z]{2,63}$")

DOMAIN_EVENTS = {"INTERNET_NAME", "AFFILIATE_INTERNET_NAME"}
IP_EVENTS = {"IP_ADDRESS"}
EMAIL_EVENTS = {"EMAILADDR"}
MAPPED_EVENTS = DOMAIN_EVENTS | IP_EVENTS | EMAIL_EVENTS


@dataclass
class MapResult:
    objects: list[Any] = field(default_factory=list)
    unmapped: Counter = field(default_factory=Counter)
    false_positives: int = 0
    invalid: int = 0


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
    target_obj = stix2.DomainName(value=target)
    objects: dict[str, Any] = {identity.id: identity, target_obj.id: target_obj}
    domains: dict[str, Any] = {target: target_obj}
    emitted: set[tuple[str, str]] = set()

    def observable(factory, value: str, module: str, obs_score: int):
        obj = factory(
            value=value,
            allow_custom=True,
            x_opencti_score=obs_score,
            x_opencti_created_by_ref=identity.id,
            x_opencti_external_references=_ref(scan_id, module),
        )
        objects.setdefault(obj.id, obj)
        return objects[obj.id]

    def relate(kind: str, source: Any, tgt: Any, module: str) -> None:
        rel = _relationship(kind, source, tgt, identity.id, _ref(scan_id, module))
        objects.setdefault(rel.id, rel)

    pending_ips: list[tuple[str, str, str]] = []

    for ev in events:
        etype = ev.get("event_type", "")
        if ev.get("false_positive"):
            result.false_positives += 1
            continue
        if etype not in MAPPED_EVENTS:
            result.unmapped[etype] += 1
            continue

        data = str(ev.get("data", "")).strip()
        module = str(ev.get("module", "unknown"))

        if etype in DOMAIN_EVENTS:
            name = _norm_domain(data)
            if not _is_domain(name):
                result.invalid += 1
                continue
            if name == target or (etype, name) in emitted:
                continue
            emitted.add((etype, name))
            obs_score = score // AFFILIATE_SCORE_DIVISOR if etype.startswith("AFFILIATE") else score
            domains[name] = observable(stix2.DomainName, name, module, obs_score)
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

        else:  # IP_ADDRESS — resolved after all domains are known
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
        ip_obj = observable(factory, str(ip), module, score)
        relate("resolves-to", domains.get(source_host, target_obj), ip_obj, module)

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


def _summary(result: MapResult, objects: dict[str, Any], scan_id: str, target: str) -> str:
    kinds = Counter(o.type for o in objects.values() if o.type.endswith(("-name", "-addr")))
    lines = [
        f"SpiderFoot scan {scan_id} for {target}.",
        "Mapped: " + (", ".join(f"{k}={v}" for k, v in sorted(kinds.items())) or "nothing"),
    ]
    if result.unmapped:
        lines.append(
            "Unmapped event types (not imported): "
            + ", ".join(f"{k}={v}" for k, v in sorted(result.unmapped.items()))
        )
    lines.append(
        f"False positives skipped: {result.false_positives}; invalid values: {result.invalid}"
    )
    return "\n".join(lines)
