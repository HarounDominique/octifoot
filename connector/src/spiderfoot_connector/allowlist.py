"""Authorization allowlist: the connector only scans domains the operator listed."""


def _norm(domain: str) -> str:
    return domain.strip().lower().rstrip(".")


def parse_allowlist(raw: str | None) -> frozenset[str]:
    """Parse a comma-separated domain list; blanks dropped, names lowercased."""
    if not raw:
        return frozenset()
    return frozenset(d for d in (_norm(p) for p in raw.split(",")) if d)


def is_allowed(target: str, allowlist: frozenset[str]) -> bool:
    """True if target equals an allowlisted domain or is a subdomain of one."""
    t = _norm(target)
    if not t:
        return False
    return any(t == d or t.endswith("." + d) for d in allowlist)
