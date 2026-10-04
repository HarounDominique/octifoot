"""Pure A/B comparison of what two SpiderFoot scans would import into OpenCTI.

Both event lists go through the real mapper; the comparison is on observable values and
relationships, never on scan ids, modules, timestamps or Note text.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from spiderfoot_connector.mapper import map_events

_SKIPPED_TYPES = {"identity", "note"}


@dataclass
class Comparison:
    only_a: list[str] = field(default_factory=list)
    only_b: list[str] = field(default_factory=list)
    flag_diffs: list[str] = field(default_factory=list)  # reported, never fail identity
    unmapped_a: dict[str, int] = field(default_factory=dict)
    unmapped_b: dict[str, int] = field(default_factory=dict)
    listed_a: int = 0  # reputation lines that only appear in the Note
    listed_b: int = 0

    @property
    def identical(self) -> bool:
        return not self.only_a and not self.only_b


def _describe(obj: Any, by_id: dict[str, Any]) -> str:
    if obj.type == "relationship":
        src, tgt = by_id[obj.source_ref], by_id[obj.target_ref]
        return (
            f"relationship:{obj.relationship_type}:{_describe(src, by_id)}>{_describe(tgt, by_id)}"
        )
    if obj.type == "autonomous-system":
        return f"autonomous-system:{obj.number}"
    return f"{obj.type}:{obj.value}"


def _view(result) -> tuple[dict[str, Any], dict[str, list[str]]]:
    by_id = {o.id: o for o in result.objects}
    described: dict[str, Any] = {}
    labels: dict[str, list[str]] = {}
    for obj in result.objects:
        if obj.type in _SKIPPED_TYPES:
            continue
        key = _describe(obj, by_id)
        described[key] = obj
        if obj.type != "relationship":
            labels[key] = sorted(getattr(obj, "x_opencti_labels", []))
    return described, labels


def compare_events(
    events_a: list[dict],
    events_b: list[dict],
    *,
    target: str,
    scan_a: str,
    scan_b: str,
    score: int,
    now: datetime,
) -> Comparison:
    res_a = map_events(events_a, target=target, scan_id=scan_a, score=score, now=now)
    res_b = map_events(events_b, target=target, scan_id=scan_b, score=score, now=now)
    objs_a, labels_a = _view(res_a)
    objs_b, labels_b = _view(res_b)
    diffs = [
        f"{key}: A has labels {labels_a[key]}, B has {labels_b[key]}"
        for key in sorted(objs_a.keys() & objs_b.keys())
        if key in labels_a and labels_a[key] != labels_b[key]
    ]
    return Comparison(
        only_a=sorted(objs_a.keys() - objs_b.keys()),
        only_b=sorted(objs_b.keys() - objs_a.keys()),
        flag_diffs=diffs,
        unmapped_a=dict(res_a.unmapped),
        unmapped_b=dict(res_b.unmapped),
        listed_a=len(res_a.listed),
        listed_b=len(res_b.listed),
    )


def invalid_reasons(label: str, outcome) -> list[str]:
    """Why a run cannot be used as evidence: it was cut off by the timeout or SpiderFoot aborted it."""
    reasons = []
    if outcome.timed_out:
        reasons.append(f"{label} run {outcome.scan_id} timed out before SpiderFoot finished it")
    if outcome.status != "FINISHED" and not (outcome.timed_out and outcome.status == "RUNNING"):
        reasons.append(f"{label} run {outcome.scan_id} ended {outcome.status}, not FINISHED")
    return reasons


def speedup(seconds_a: float, seconds_b: float) -> float:
    """Fraction of time saved by B relative to A (0.6 = 60% faster); negative if B is slower."""
    if seconds_a <= 0:
        return 0.0
    return round((seconds_a - seconds_b) / seconds_a, 4)
