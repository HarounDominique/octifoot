"""What changed since the previous scan of the same domain.

The state lives in OpenCTI, not in the container: every enrichment of a root target writes a Note whose abstract starts with
``octifoot snapshot for <target>:`` and whose text ends with a machine-readable snapshot line. The next enrichment reads the
newest such Note and compares. Disappearances are only reported when both scans were complete: an incomplete scan or a failing
source would otherwise make things look gone.
"""

import json
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from typing import Any

from spiderfoot_connector.dnschecks import DnsFacts, dmarc_policy

SNAPSHOT_VERSION = 1
SNAPSHOT_PREFIX = "Snapshot (machine-readable, used to detect changes at the next scan): "
MAX_LISTED = 10

_QUERY = """
query($prefix: [Any!]!) {
  notes(first: 20, orderBy: created, orderMode: desc,
        filters: {mode: and, filters: [{key: "attribute_abstract", values: $prefix, operator: starts_with}], filterGroups: []}) {
    edges { node { created attribute_abstract content } }
  }
}
"""

RunQuery = Callable[[str, dict[str, Any]], dict[str, Any]]


@dataclass
class Snapshot:
    scan: str
    at: str
    complete: bool
    hosts: list[str] = field(default_factory=list)
    ips: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    certs: list[str] = field(default_factory=list)
    asn: list[int] = field(default_factory=list)
    registrar: list[str] = field(default_factory=list)
    hosting: list[str] = field(default_factory=list)
    ns: list[str] = field(default_factory=list)
    mx: list[str] = field(default_factory=list)
    spf: str | None = None  # "none" | "present" | None when unknown / not checked
    dmarc: str | None = None  # "none" | "p=<policy>" | "present" | None


def snapshot_from(
    *,
    target: str,
    scan: str,
    at: str,
    complete: bool,
    objects: Iterable[Any],
    infra: dict[str, set[str]],
    dns: DnsFacts | None,
) -> Snapshot:
    """Snapshot of a merged enrichment result (the target itself is not a host of itself)."""
    objs = list(objects)

    def values(*types: str) -> list[str]:
        return sorted({o.value for o in objs if o.type in types and o.value != target})

    def state(value: str | None, shown: Callable[[str], str]) -> str | None:
        return None if value is None else ("none" if value == "" else shown(value))

    return Snapshot(
        scan=scan,
        at=at,
        complete=complete,
        hosts=values("domain-name"),
        ips=values("ipv4-addr", "ipv6-addr"),
        emails=values("email-addr"),
        certs=sorted({o.serial_number for o in objs if o.type == "x509-certificate"}),
        asn=sorted({o.number for o in objs if o.type == "autonomous-system"}),
        registrar=sorted(infra.get("registrar", ())),
        hosting=sorted(infra.get("hosting", ())),
        ns=sorted(infra.get("DNS", ())),
        mx=sorted(infra.get("mail", ())),
        spf=state(dns.spf if dns else None, lambda _: "present"),
        dmarc=state(
            dns.dmarc if dns else None,
            lambda v: f"p={dmarc_policy(v)}" if dmarc_policy(v) else "present",
        ),
    )


def parse_snapshot(text: str) -> Snapshot | None:
    """The snapshot line of a Note's text; None when absent, malformed or of another version."""
    for line in text.splitlines():
        if line.startswith(SNAPSHOT_PREFIX):
            try:
                data = json.loads(line[len(SNAPSHOT_PREFIX) :])
                if data.pop("v") != SNAPSHOT_VERSION:
                    return None
                return Snapshot(**data)
            except (ValueError, KeyError, TypeError):
                return None
    return None


def latest_snapshot(run_query: RunQuery, target: str) -> Snapshot | None:
    """The newest readable snapshot Note of ``target``; read-only."""
    data = run_query(_QUERY, {"prefix": [f"octifoot snapshot for {target}:"]})
    nodes = sorted(
        (e["node"] for e in data["data"]["notes"]["edges"]),
        key=lambda n: n["created"],
        reverse=True,
    )
    for node in nodes:
        snap = parse_snapshot(node["content"])
        if snap is not None:
            return snap
    return None


def _listed(values: list[str]) -> str:
    shown = ", ".join(values[:MAX_LISTED])
    return shown + (f" and {len(values) - MAX_LISTED} more" if len(values) > MAX_LISTED else "")


_SET_CATEGORIES = (
    ("hostnames", "hosts"),
    ("IPs", "ips"),
    ("emails", "emails"),
    ("AS numbers", "asn"),
)
_INFRA_SETS = (("name servers", "ns"), ("mail hosts", "mx"))
_INFRA_CHANGED = (("registrar", "registrar"), ("hosting", "hosting"))


def _diff_lines(
    prev: Snapshot, cur: Snapshot, both_complete: bool, failed_sources: bool
) -> list[str]:
    lines: list[str] = []

    def added_removed(label: str, key: str, caveat: str = "") -> None:
        old, new = {str(v) for v in getattr(prev, key)}, {str(v) for v in getattr(cur, key)}
        if new - old:
            lines.append(f"{label} added: {_listed(sorted(new - old))}")
        if both_complete and old - new:
            lines.append(f"{label} not seen this time: {_listed(sorted(old - new))}{caveat}")

    caveat = " (subdomain sources reported errors: they may not be gone)" if failed_sources else ""
    for label, key in _SET_CATEGORIES:
        added_removed(label, key, caveat if key == "hosts" else "")
    new_certs = sorted(set(cur.certs) - set(prev.certs))
    if new_certs:
        lines.append(f"certificates added: {len(new_certs)} ({_listed(new_certs[:3])})")
    for label, key in _INFRA_CHANGED:
        old, new = getattr(prev, key), getattr(cur, key)
        if old != new and (both_complete or new):
            lines.append(
                f"{label} changed: {', '.join(old) or '(none)'} -> {', '.join(new) or '(none)'}"
            )
    for label, key in _INFRA_SETS:
        added_removed(label, key)
    for label, key in (("SPF", "spf"), ("DMARC", "dmarc")):
        old, new = getattr(prev, key), getattr(cur, key)
        if old is not None and new is not None and old != new:
            lines.append(f"{label}: {old} -> {new}")
    return lines


def summarize(prev: Snapshot | None, cur: Snapshot, failed_sources: bool = False) -> str:
    if prev is None:
        return "first snapshot"
    both_complete = prev.complete and cur.complete
    lines = _diff_lines(prev, cur, both_complete, failed_sources)
    if lines:
        return f"{len(lines)} change{'' if len(lines) == 1 else 's'} since {prev.at[:10]}"
    return (
        f"no changes since {prev.at[:10]}"
        if both_complete
        else f"no additions since {prev.at[:10]}"
    )


def render_changes(
    target: str,
    prev: Snapshot | None,
    cur: Snapshot,
    subdomain_sources_failed: bool = False,
    previous_unreadable: bool = False,
) -> str:
    data = {k: sorted(v) if isinstance(v, list) else v for k, v in asdict(cur).items()}
    snapshot_line = SNAPSHOT_PREFIX + json.dumps({"v": SNAPSHOT_VERSION, **data}, sort_keys=True)
    if prev is None:
        why = (
            "the previous snapshot could not be read"
            if previous_unreadable
            else "there is no previous scan"
        )
        head = f"First octifoot snapshot of {target}: {why}, nothing to compare."
        return f"{head}\n{snapshot_line}"
    both_complete = prev.complete and cur.complete
    lines = [
        f"Changes since the previous octifoot scan of {target} ({prev.at[:10]}, scan {prev.scan}):"
    ]
    if not both_complete:
        lines.append(
            "- caveat: this scan or the previous one was incomplete, so disappearances are not reported"
            + ("" if cur.complete else "; additions are reliable")
            + ("; additions may not be new" if not prev.complete else "")
        )
    diff = _diff_lines(prev, cur, both_complete, subdomain_sources_failed)
    lines += [f"- {line}" for line in diff]
    if not diff:
        when = f"({prev.at[:10]}, scan {prev.scan})"
        lines.append(
            f"- no changes since the previous scan {when}"
            if both_complete
            else f"- no additions since the previous scan {when}; disappearances are not assessed"
        )
    lines.append(snapshot_line)
    return "\n".join(lines)
