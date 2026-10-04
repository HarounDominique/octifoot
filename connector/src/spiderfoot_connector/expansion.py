"""Pure planner for the iterative scan loop.

Expansion never widens the authorized scope: a discovered domain is only ever a scan
target if it passes the same allowlist check as the original target.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field

from spiderfoot_connector.allowlist import is_allowed


@dataclass
class Plan:
    targets: list[str] = field(default_factory=list)
    out_of_scope: list[str] = field(default_factory=list)
    budget_skipped: list[str] = field(default_factory=list)


def plan_next(
    discovered: Iterable[str],
    *,
    scanned: set[str],
    allowlist: frozenset[str],
    remaining_budget: int,
) -> Plan:
    """Split discoveries into targets to scan, out-of-scope and budget-skipped (order kept)."""
    plan = Plan()
    seen: set[str] = set()
    for raw in discovered:
        name = raw.strip().lower().rstrip(".")
        if not name or name in scanned or name in seen:
            continue
        seen.add(name)
        if not is_allowed(name, allowlist):
            plan.out_of_scope.append(name)
        elif len(plan.targets) < remaining_budget:
            plan.targets.append(name)
        else:
            plan.budget_skipped.append(name)
    return plan
