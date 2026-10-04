"""Map SpiderFoot scan events to STIX 2.1 objects for OpenCTI.

Pure functions, no I/O. Only a small, clean subset of event types is mapped; everything
else is counted in ``MapResult.unmapped`` so nothing is dropped silently.
"""

import ipaddress
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import stix2
from pycti import Identity, Note, StixCoreRelationship

from spiderfoot_connector.dnschecks import DnsFacts, dmarc_policy, spf_all_qualifier

SOURCE_NAME = "SpiderFoot"
_FEED_RE = re.compile(r"^(?P<feed>[^\[\n]+?)\s*\[(?P<value>[^\]\n]+)\]")
_DOMAIN_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9_]([a-z0-9_-]{0,61}[a-z0-9_])?\.)+[a-z]{2,63}$")

# AFFILIATE_INTERNET_NAME is deliberately absent: those hostnames belong to other parties (mail
# providers, reverse DNS of someone else's IPs, name servers), not to the target.
DOMAIN_EVENTS = {"INTERNET_NAME"}
AFFILIATE_NAME_EVENT = "AFFILIATE_INTERNET_NAME"
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

# TLS certificates (SpiderFoot's text is cut at 1024 characters, so serial/issuer/validity/subject only).
CERT_EVENT = "SSL_CERTIFICATE_RAW"
MAX_CERTS = 10
_CN_RE = re.compile(r"CN\s*=\s*([^,]+)")

# Registration facts and TXT records of the target, as Note lines (no objects).
WHOIS_EVENT = "DOMAIN_WHOIS"
TXT_EVENT = "DNS_TEXT"
MAX_SPF_CHARS = 160
NEW_DOMAIN_DAYS = 30
REGISTRATION_EXPIRY_DAYS = 30
CERT_EXPIRY_DAYS = 14
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_WHOIS_DATE_KEYS = {
    "creation date": "created",
    "created": "created",
    "registered on": "created",
    "registration time": "created",
    "updated date": "updated",
    "last updated": "updated",
    "last modified": "updated",
    "registry expiry date": "expires",
    "registrar registration expiration date": "expires",
    "expiry date": "expires",
    "expiration date": "expires",
    "paid-till": "expires",
}
_VERIFICATION_RE = re.compile(r"^([a-z0-9._-]+)-verification=")
_DMARC_POLICY_RE = re.compile(r"(?:^|;)\s*p=([a-z]+)")

# Source health: modules that logged ERROR rows during the scan (diagnostic text only).
MAX_HEALTH_MODULES = 8
MAX_HEALTH_MESSAGE = 80

# Every event type that ends up as an object, a label or a Note line. A scan profile must keep
# producing all of these (checked against SpiderFoot's module metadata in the profile tests).
IMPORTED_EVENTS = (
    MAPPED_EVENTS
    | {FLAG_IP_EVENT, FLAG_NAME_EVENT}
    | LISTED_EVENTS
    | NETBLOCK_EVENTS
    | {AS_EVENT}
    | set(INFRA_EVENTS)
    | {WHOIS_EVENT, TXT_EVENT, CERT_EVENT}
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
    whois: dict[str, Any] = field(default_factory=dict)  # created/updated/expires/status/dnssec
    txt_spf: str = ""
    txt_dmarc: str = ""
    txt_verification: dict[str, set[str]] = field(
        default_factory=dict
    )  # service -> distinct tokens
    txt_other: set[str] = field(default_factory=set)
    certs_imported: int = 0
    certs_over_cap: int = 0
    certs_foreign: int = 0
    dns_raw_seen: bool = False  # SpiderFoot got DNS answers for exactly the scanned name
    flagged: list[tuple[str, list[str]]] = field(default_factory=list)  # (host or IP, feeds)
    # (CN, not_before, not_after) of the imported certificates
    cert_info: list[tuple[str, datetime | None, datetime | None]] = field(default_factory=list)
    mail_exact: set[str] = field(
        default_factory=set
    )  # mail hosts from records of the scanned name itself
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


def _ref(scan_id: str, module: str, scan_url: str = "") -> list[dict[str, str]]:
    ref = {
        "source_name": SOURCE_NAME,
        "external_id": scan_id,
        "description": f"SpiderFoot scan {scan_id}, module {module}",
    }
    if scan_url:  # one click from OpenCTI to the complete scan in SpiderFoot
        ref["url"] = scan_url
    return [ref]


def _flag_ref(scan_id: str, feed: str, flag_module: str, scan_url: str = "") -> dict[str, str]:
    ref = {
        "source_name": feed,
        "external_id": scan_id,
        "description": f"Flagged malicious by {feed} (SpiderFoot module {flag_module})",
    }
    if scan_url:
        ref["url"] = scan_url
    return ref


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
    source_errors: Sequence[tuple[str, str]] = (),
    subdomain_sources: frozenset[str] = frozenset(),
    dns_facts: DnsFacts | None = None,
    scan_status: str = "FINISHED",
    timeout_seconds: int = 0,
    timed_out: bool = False,
    ui_url: str = "",
    extra_lines: Sequence[str] = (),
) -> MapResult:
    """Convert SpiderFoot ``scanexportjsonmulti`` rows into STIX objects."""
    result = MapResult()
    scan_url = f"{ui_url}/scaninfo?id={scan_id}" if ui_url else ""
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
            refs += _ref(scan_id, flag_module, scan_url) + [
                _flag_ref(scan_id, feed, flag_module, scan_url)
            ]
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
        refs = _ref(scan_id, module, scan_url)
        extra = {}
        if flags:
            refs += [_flag_ref(scan_id, feed, flag_module, scan_url) for feed, flag_module in flags]
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
        rel = _relationship(kind, source, tgt, identity.id, _ref(scan_id, module, scan_url))
        objects.setdefault(rel.id, rel)

    def autonomous_system(number: int, module: str):
        obj = stix2.AutonomousSystem(
            number=number,
            allow_custom=True,
            x_opencti_created_by_ref=identity.id,
            x_opencti_external_references=_ref(scan_id, module, scan_url),
        )
        objects.setdefault(obj.id, obj)
        return objects[obj.id]

    certs: dict[str, tuple[dict[str, Any], str]] = {}  # serial -> (parsed, module), first wins
    pending_ips: list[tuple[str, str, str]] = []
    pending_hosting: list[tuple[str, str]] = []  # (source IP or host, "name: url")
    affiliate_hosts: set[str] = set()  # hostnames of other parties, never imported
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
        if etype in (WHOIS_EVENT, TXT_EVENT):
            if not _is_target_or_parent(str(ev.get("source_data", "")), target):
                result.unmapped[f"{etype} (not the target's)"] += 1
            elif etype == WHOIS_EVENT:
                if not _merge_whois(result.whois, data):
                    result.invalid += 1
            else:
                _add_txt(result, data)
            continue
        if etype == CERT_EVENT:
            cert = _parse_cert(data)
            if cert is None:
                result.invalid += 1
            elif not (
                _norm_domain(str(ev.get("source_data", ""))) == target
                or _cert_covers(cert["cn"], target)
            ):
                result.certs_foreign += 1
                result.unmapped[f"{etype} (not the target's)"] += 1
            else:
                certs.setdefault(cert["serial"], (cert, module))
            continue
        if etype in INFRA_EVENTS:
            source = str(ev.get("source_data", ""))
            if etype == "PROVIDER_HOSTING":
                pending_hosting.append((source, data))  # source is an IP: judged once IPs are known
            elif not _is_target_or_parent(source, target):
                # e.g. the MX of a provider's domain seen while resolving a CNAME target
                result.unmapped[f"{etype} (not the target's)"] += 1
            else:
                _add_infra(result, etype, data)
                if etype == "PROVIDER_MAIL" and _norm_domain(source) == target:
                    result.mail_exact.add(_infra_value(etype, data))
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
        if etype == "RAW_DNS_RECORDS" and _norm_domain(str(ev.get("source_data", ""))) == target:
            result.dns_raw_seen = True
        if etype not in MAPPED_EVENTS:
            if etype == AFFILIATE_NAME_EVENT:
                affiliate_hosts.add(_norm_domain(data))
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
            result.discovered_domains.append(name)
            domains[name] = observable(
                stix2.DomainName, name, module, score, flagged_names.get(name, [])
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
        if source_host in affiliate_hosts and source_host not in domains:
            # Falling back to the target would present another party's IP as the target's.
            result.unmapped["IP_ADDRESS (affiliate host)"] += 1
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

    newest_first = sorted(
        certs.values(),
        key=lambda item: item[0].get("not_before") or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )
    result.certs_over_cap = max(0, len(newest_first) - MAX_CERTS)
    for parsed, cert_module in newest_first[:MAX_CERTS]:
        extra = {k: parsed[k] for k in ("not_before", "not_after") if k in parsed}
        certificate = stix2.X509Certificate(
            serial_number=parsed["serial"],
            issuer=parsed.get("issuer"),
            subject=parsed["subject"],
            signature_algorithm=parsed.get("algorithm"),
            validity_not_before=extra.get("not_before"),
            validity_not_after=extra.get("not_after"),
            allow_custom=True,
            x_opencti_created_by_ref=identity.id,
            x_opencti_external_references=_ref(scan_id, cert_module, scan_url),
        )
        objects.setdefault(certificate.id, certificate)
        relate("related-to", certificate, target_obj, cert_module)
        result.certs_imported += 1
        result.cert_info.append((parsed["cn"], parsed.get("not_before"), parsed.get("not_after")))

    emitted_ips = {o.value for o in objects.values() if o.type in ("ipv4-addr", "ipv6-addr")}
    for source, data in pending_hosting:
        if _is_target_or_parent(source, target) or _norm_ip(source) in emitted_ips:
            _add_infra(result, "PROVIDER_HOSTING", data)
        else:
            result.unmapped["PROVIDER_HOSTING (not the target's)"] += 1
    result.flagged = sorted(
        [
            (n, sorted({f for f, _ in fs}))
            for n, fs in flagged_names.items()
            if n == target or n in domains
        ]
        + [(ip, sorted({f for f, _ in fs})) for ip, fs in flagged.items() if ip in emitted_ips]
    )
    result.flags_skipped = sum(1 for ip in flagged if ip not in emitted_ips)
    result.name_flags_skipped = sum(
        1 for name in flagged_names if name != target and name not in domains
    )

    summary = _summary(
        result,
        objects,
        scan_id,
        target,
        now,
        source_errors,
        subdomain_sources,
        dns_facts,
        _completeness(scan_status, timeout_seconds, timed_out),
        scan_url,
        extra_lines,
    )
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


def _is_target_or_parent(source: str, target: str) -> bool:
    """True when ``source`` is the target itself or a parent domain of it (never a sibling)."""
    name = _norm_domain(source)
    return bool(name) and (name == target or target.endswith("." + name))


def _merge_whois(whois: dict[str, Any], text: str) -> bool:
    """Take dates, EPP status and DNSSEC from WHOIS text, first value wins; False if nothing parsed.

    Registrant and contact lines are never read. SpiderFoot truncates the text, so partial is normal.
    """
    found: dict[str, Any] = {}
    status: list[str] = []
    for raw in text.replace("\r", "").split("\n"):
        key, _, value = raw.partition(":")
        key, value = key.strip().lower(), value.strip()
        if key in _WHOIS_DATE_KEYS and (m := _DATE_RE.search(value)):
            found.setdefault(_WHOIS_DATE_KEYS[key], m.group(0))
        elif key == "domain status" and value:
            token = value.split()[0]
            if token not in status:
                status.append(token)
        elif key == "dnssec" and value:
            found.setdefault("dnssec", value.split()[0].lower())
    if status:
        found["status"] = status
    for name, value in found.items():
        whois.setdefault(name, value)
    return bool(found)


def _parse_cert(text: str) -> dict[str, Any] | None:
    """Serial, issuer, validity, subject and algorithm from ``openssl x509 -text``; None if no serial or subject."""
    lines = [ln.strip() for ln in text.replace("\r", "").split("\n")]
    out: dict[str, Any] = {}
    for i, ln in enumerate(lines):
        key, _, value = ln.partition(":")
        key, value = key.strip(), value.strip()  # openssl prints "Not After : ..."
        if key == "Serial Number":
            out.setdefault("serial", value or (lines[i + 1] if i + 1 < len(lines) else ""))
        elif key == "Signature Algorithm" and value:
            out.setdefault("algorithm", value)
        elif key == "Issuer" and value:
            out.setdefault("issuer", value)
        elif key == "Subject" and value:
            out.setdefault("subject", value)
        elif key in ("Not Before", "Not After"):
            try:
                when = datetime.strptime(value.replace("GMT", "+0000"), "%b %d %H:%M:%S %Y %z")
            except ValueError:
                continue
            out.setdefault("not_before" if key == "Not Before" else "not_after", when)
    cn = _CN_RE.search(out.get("subject", ""))
    if not out.get("serial") or not cn:
        return None
    out["cn"] = cn.group(1).strip()
    return out


def _cert_covers(cn: str, target: str) -> bool:
    """A certificate is the target's when its CN is the target, a wildcard of it, a name under it, or its parent."""
    name = cn.lower().strip().rstrip(".").removeprefix("*.")
    return bool(name) and (
        name == target or name.endswith("." + target) or target.endswith("." + name)
    )


def _tls_line(result: MapResult) -> str:
    if not (result.certs_imported or result.certs_over_cap or result.certs_foreign):
        return ""
    return (
        f"TLS certificates: {result.certs_imported} imported, {result.certs_over_cap} over the cap of "
        f"{MAX_CERTS}, {result.certs_foreign} not issued for the target"
    )


def _add_txt(result: MapResult, value: str) -> None:
    text = value.strip()
    lower = text.lower()
    if lower.startswith("v=spf1"):
        result.txt_spf = result.txt_spf or text[:MAX_SPF_CHARS]
    elif lower.startswith("v=dmarc1"):
        m = _DMARC_POLICY_RE.search(lower)
        result.txt_dmarc = result.txt_dmarc or (m.group(1) if m else "")
    elif m := _VERIFICATION_RE.match(lower):
        service = m.group(1).removesuffix("-site")
        result.txt_verification.setdefault(service, set()).add(lower)
    elif text:
        result.txt_other.add(text)


def _whois_line(whois: dict[str, Any], now: datetime) -> str:
    if not whois:
        return ""
    parts = []
    if "created" in whois:
        created = whois["created"]
        days = (now.date() - datetime.fromisoformat(created).date()).days
        parts.append(
            f"created {created}" + (f" ({days} days before this scan)" if days >= 0 else "")
        )
    for name in ("updated", "expires"):
        if name in whois:
            parts.append(f"{name} {whois[name]}")
    if whois.get("status"):
        parts.append("status: " + ", ".join(whois["status"]))
    if "dnssec" in whois:
        parts.append(f"DNSSEC: {whois['dnssec']}")
    return "WHOIS (as reported by SpiderFoot): " + "; ".join(parts) if parts else ""


def _txt_line(result: MapResult) -> str:
    parts = []
    if result.txt_spf:
        parts.append(f"SPF: {result.txt_spf}")
    if result.txt_dmarc:
        parts.append(f"DMARC: p={result.txt_dmarc}")
    if result.txt_verification:
        services = ", ".join(
            f"{s} ({len(tokens)})" for s, tokens in sorted(result.txt_verification.items())
        )
        parts.append(f"verification tokens: {services}")
    if result.txt_other:
        parts.append(f"other records: {len(result.txt_other)}")
    return "DNS TXT (as reported by SpiderFoot): " + "; ".join(parts) if parts else ""


def _norm_ip(value: str) -> str:
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return ""


def _add_infra(result: MapResult, etype: str, data: str) -> None:
    value = _infra_value(etype, data)
    if value:
        result.infra.setdefault(INFRA_EVENTS[etype], set()).add(value)
    else:
        result.invalid += 1


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


def _plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def _completeness(status: str, timeout_seconds: int, timed_out: bool) -> str:
    """A scan that did not run to the end must say so; the Note is what analysts read."""
    if timed_out:
        return (
            f"scan incomplete: stopped after {timeout_seconds} s, results are partial "
            "(SPIDERFOOT_TIMEOUT_SECONDS)"
        )
    if status != "FINISHED":
        return f"scan ended {status}, not FINISHED: results may be partial"
    return ""


def _mail_findings(result: MapResult, target: str, dns: DnsFacts | None) -> list[str]:
    """Mail-authentication findings. Direct DNS answers win; without them, fall back to scan events."""
    if dns is not None and dns.mx is not None:
        if not dns.mx:
            return []  # confirmed: this name receives no mail
        out = []
        if dns.spf == "":
            out.append(f"receives mail (MX: {', '.join(dns.mx[:2])}) but publishes no SPF record")
        elif dns.spf and (q := spf_all_qualifier(dns.spf)) in ("+all", "?all"):
            out.append(f"SPF ends in {q}: it does not restrict senders")
        if dns.dmarc == "":
            out.append(f"receives mail but publishes no DMARC record at _dmarc.{target}")
        elif dns.dmarc and dmarc_policy(dns.dmarc) == "none":
            out.append("DMARC policy is p=none (spoofed mail is only monitored, not rejected)")
        return out
    # Fallback: only records of the scanned name itself; a parent zone's mail is not this name's.
    mail = sorted(result.mail_exact)
    if mail and result.dns_raw_seen and not result.txt_spf:
        gap = "publishes no SPF record (DNS answered; DMARC is not checked by SpiderFoot)"
        return [f"receives mail (MX: {', '.join(mail[:2])}) but {gap}"]
    return []


def _findings(
    result: MapResult,
    now: datetime,
    source_errors: Sequence[tuple[str, str]],
    subdomain_sources: frozenset[str],
    target: str = "",
    dns_facts: DnsFacts | None = None,
) -> list[str]:
    """What is notable in the data, by fixed rules; every item is tied to observed evidence."""
    today = now.date()
    out: list[str] = []
    if result.flagged:
        feeds = sorted({f for _, fs in result.flagged for f in fs})
        values = ", ".join(v for v, _ in result.flagged[:MAX_INFRA_VALUES])
        extra = len(result.flagged) - MAX_INFRA_VALUES
        what = _plural(len(result.flagged), "hostname/IP", "hostnames/IPs")
        out.append(
            f"{what} flagged malicious ({', '.join(feeds)}): {values}"
            + (f" and {extra} more" if extra > 0 else "")
        )
    out.extend(_mail_findings(result, target, dns_facts))
    newest: dict[str, tuple[datetime | None, datetime | None]] = {}
    floor = datetime.min.replace(tzinfo=UTC)
    for cn, not_before, not_after in result.cert_info:
        if cn not in newest or (not_before or floor) > (newest[cn][0] or floor):
            newest[cn] = (not_before, not_after)
    for cn, (_, not_after) in sorted(newest.items()):  # older certificates are rotation history
        if not_after is None:
            continue
        days = (not_after.date() - today).days
        if not_after < now:
            out.append(f"certificate for {cn} expired on {not_after.date()}")
        elif days <= CERT_EXPIRY_DAYS:
            out.append(f"certificate for {cn} expires in {days} days ({not_after.date()})")
    created, expires = result.whois.get("created"), result.whois.get("expires")
    if created:
        age = (today - datetime.fromisoformat(created).date()).days
        if 0 <= age < NEW_DOMAIN_DAYS:
            out.append(f"registered {age} days ago ({created})")
    if expires:
        left = (datetime.fromisoformat(expires).date() - today).days
        if left < 0:
            out.append(f"registration expired on {expires}")
        elif left <= REGISTRATION_EXPIRY_DAYS:
            out.append(f"registration expires in {left} days ({expires})")
    if result.listed:
        listings = _plural(len(result.listed), "reputation listing", "reputation listings")
        out.append(f"{listings} on shared infrastructure (not the target's own)")
    failing = sorted({m for m, _ in source_errors} & subdomain_sources)
    if failing:
        out.append(
            f"subdomain discovery may be incomplete: {', '.join(failing)} reported errors "
            "(sfp_crt does not report outages)"
        )
    return out


def _findings_block(
    result: MapResult,
    now: datetime,
    source_errors: Sequence[tuple[str, str]],
    subdomain_sources: frozenset[str],
    target: str = "",
    dns_facts: DnsFacts | None = None,
    incomplete: str = "",
) -> list[str]:
    items = _findings(result, now, source_errors, subdomain_sources, target, dns_facts)
    if incomplete:
        items.insert(0, incomplete)  # it conditions every other finding, so it comes first
    if not items:
        return ["Key findings: nothing notable in the data the answering sources returned."]
    return ["Key findings (as of this scan):", *[f"- {item}" for item in items]]


def _dns_line(f: DnsFacts | None) -> str:
    if f is None:
        return ""

    def txt(value: str | None, shown) -> str:
        return "unknown" if value is None else ("none" if value == "" else shown(value))

    def count(items: list[str] | None, noun: str) -> str:
        return (
            "unknown"
            if items is None
            else ("none" if not items else _plural(len(items), noun, noun + "s"))
        )

    mx = (
        "unknown"
        if f.mx is None
        else (
            "none"
            if not f.mx
            else ", ".join(f.mx[:3]) + (f" and {len(f.mx) - 3} more" if len(f.mx) > 3 else "")
        )
    )
    dnssec = "unknown" if f.ds is None else ("DS record present" if f.ds else "no DS record")
    return (
        "DNS checks (queried by octifoot, not by SpiderFoot): "
        f"MX: {mx}; "
        f"SPF: {txt(f.spf, lambda v: v[:MAX_SPF_CHARS])}; "
        f"DMARC: {txt(f.dmarc, lambda v: f'p={dmarc_policy(v)}' if dmarc_policy(v) else 'present (no p= policy)')}; "
        f"CAA: {count(f.caa, 'record')}; "
        f"DNSSEC: {dnssec}; "
        f"MTA-STS: {txt(f.mta_sts, lambda v: 'present')}"
    )


def _health_line(errors: Sequence[tuple[str, str]]) -> str:
    by_module: dict[str, list[str]] = {}
    for module, message in errors:
        by_module.setdefault(module, []).append(message)
    if not by_module:
        return ""
    # Most errors first, then by name, so the line does not depend on log order.
    ordered = sorted(by_module.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    shown = [f"{m}: {min(msgs)[:MAX_HEALTH_MESSAGE]} ({len(msgs)})" for m, msgs in ordered]
    extra = len(shown) - MAX_HEALTH_MODULES
    text = "; ".join(shown[:MAX_HEALTH_MODULES]) + (f" and {extra} more" if extra > 0 else "")
    return (
        f"Sources that reported errors ({len(by_module)} modules; an outage that a module reports "
        f"as 'no information' is not detectable here): {text}"
    )


def _summary(
    result: MapResult,
    objects: dict[str, Any],
    scan_id: str,
    target: str,
    now: datetime,
    source_errors: Sequence[tuple[str, str]] = (),
    subdomain_sources: frozenset[str] = frozenset(),
    dns_facts: DnsFacts | None = None,
    incomplete: str = "",
    scan_url: str = "",
    extra_lines: Sequence[str] = (),
) -> str:
    kinds = Counter(o.type for o in objects.values() if o.type.endswith(("-name", "-addr")))
    lines = [
        f"SpiderFoot scan {scan_id} for {target}."
        + (f" Full results in SpiderFoot: {scan_url}" if scan_url else ""),
        *_findings_block(
            result, now, source_errors, subdomain_sources, target, dns_facts, incomplete
        ),
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
    for extra in (
        _whois_line(result.whois, now),
        _txt_line(result),
        _tls_line(result),
        _dns_line(dns_facts),
    ):
        if extra:
            lines.append(extra)
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
    health = _health_line(source_errors)
    if health:
        lines.append(health)
    lines.extend(extra_lines)
    lines.append(
        f"False positives skipped: {result.false_positives}; invalid values: {result.invalid}"
    )
    return "\n".join(lines)
