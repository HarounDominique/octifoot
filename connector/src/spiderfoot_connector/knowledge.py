"""What OpenCTI already knows about the observables a scan just found.

The connector used to only send data. Here it reads the platform (one batched, read-only GraphQL query)
and reports what *other sources* attached to the same observables: indicators, reports, labels and
creators. Objects octifoot itself created never count, so a previous import is not "knowledge".
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

BATCH = 50
MAX_LINES = 20
MAX_REPORT_NAMES = 5
OWN_CREATOR = "SpiderFoot"
OWN_LABEL_PREFIX = "spiderfoot:"

_QUERY = """
query($values: [Any!]!) {
  stixCyberObservables(first: 100, filters: {mode: and, filters: [{key: "value", values: $values}], filterGroups: []}) {
    edges { node {
      entity_type observable_value createdBy { name } objectLabel { value }
      indicators { edges { node { name x_opencti_score revoked } } }
      reports { edges { node { name } } }
    } }
  }
}
"""

RunQuery = Callable[[str, dict[str, Any]], dict[str, Any]]


@dataclass
class Known:
    value: str
    entity_type: str
    indicators: list[tuple[str, int | None]] = field(default_factory=list)
    reports: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    creators: list[str] = field(default_factory=list)


def _known_from(node: dict[str, Any]) -> Known | None:
    creator = (node.get("createdBy") or {}).get("name")
    known = Known(
        value=node["observable_value"],
        entity_type=node["entity_type"],
        indicators=[
            (e["node"]["name"], e["node"].get("x_opencti_score"))
            for e in node["indicators"]["edges"]
            if not e["node"].get("revoked")
        ],
        reports=[e["node"]["name"] for e in node["reports"]["edges"]],
        labels=[
            label["value"]
            for label in node["objectLabel"]
            if not label["value"].startswith(OWN_LABEL_PREFIX)
        ],
        creators=[creator] if creator and creator != OWN_CREATOR else [],
    )
    return known if (known.indicators or known.reports or known.labels or known.creators) else None


def query_known(run_query: RunQuery, values: Iterable[str]) -> list[Known]:
    unique = list(dict.fromkeys(values))
    found: dict[str, Known] = {}
    for start in range(0, len(unique), BATCH):
        batch = unique[start : start + BATCH]
        data = run_query(_QUERY, {"values": batch})
        for edge in data["data"]["stixCyberObservables"]["edges"]:
            known = _known_from(edge["node"])
            if known:
                found[known.value] = known
    return [found[v] for v in sorted(found)]


def _plural(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def _line(k: Known) -> str:
    parts = []
    if k.indicators:
        scores = [s for _, s in k.indicators if s is not None]
        high = f" (highest score {max(scores)})" if scores else ""
        parts.append(_plural(len(k.indicators), "indicator") + high)
    if k.reports:
        names = "; ".join(k.reports[:MAX_REPORT_NAMES])
        parts.append(f"{_plural(len(k.reports), 'report')} ({names})")
    if k.labels:
        parts.append("labels: " + ", ".join(sorted(k.labels)))
    if k.creators:
        parts.append("also from " + ", ".join(sorted(k.creators)))
    return f"- {k.value} ({k.entity_type}): " + "; ".join(parts)


def render_knowledge(known: list[Known], total: int) -> tuple[str, str]:
    """(abstract, content) of the knowledge Note."""
    abstract = (
        f"OpenCTI knowledge before this import: {len(known)} of {total} observables already known"
    )
    header = (
        "OpenCTI knowledge (queried by octifoot before this import; "
        "excludes SpiderFoot's own objects):"
    )
    if not known:
        none = (
            f"none of the {total} imported observables has indicators, reports or labels "
            "from other sources in OpenCTI"
        )
        return abstract, f"{header}\n{none}"
    ordered = sorted(known, key=lambda k: k.value)
    lines = [_line(k) for k in ordered[:MAX_LINES]]
    if len(ordered) > MAX_LINES:
        lines.append(f"- and {len(ordered) - MAX_LINES} more")
    return abstract, "\n".join([header, *lines])
