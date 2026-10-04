"""Authorization allowlist: the connector only scans domains the operator listed."""

import ipaddress
import re


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


_LABEL = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")
_TLD = re.compile(r"^([a-z]{2,63}|xn--[a-z0-9-]{1,59})$")
# Names under which a whole population of unrelated sites live. Authorising one would authorise strangers' sites.
# A hand-kept list of common ones, a safety net and not a guarantee (the Public Suffix List is not bundled).
_PUBLIC_SUFFIXES = frozenset(
    {
        "co.uk",
        "org.uk",
        "me.uk",
        "ac.uk",
        "gov.uk",
        "ltd.uk",
        "plc.uk",
        "com.au",
        "net.au",
        "org.au",
        "edu.au",
        "gov.au",
        "co.jp",
        "ne.jp",
        "or.jp",
        "ac.jp",
        "go.jp",
        "com.br",
        "net.br",
        "org.br",
        "gov.br",
        "com.mx",
        "org.mx",
        "com.ar",
        "com.co",
        "com.pe",
        "com.ve",
        "com.uy",
        "com.ec",
        "co.nz",
        "org.nz",
        "net.nz",
        "co.za",
        "org.za",
        "co.in",
        "net.in",
        "org.in",
        "co.kr",
        "or.kr",
        "co.th",
        "co.il",
        "co.id",
        "com.cn",
        "net.cn",
        "org.cn",
        "com.hk",
        "com.tw",
        "com.sg",
        "com.my",
        "com.ph",
        "com.vn",
        "com.pk",
        "com.tr",
        "com.ua",
        "com.eg",
        "com.sa",
        "com.ng",
        "com.es",
        "nom.es",
        "org.es",
        "gob.es",
        "edu.es",
        "com.pt",
        "com.pl",
        "com.ru",
        "github.io",
        "gitlab.io",
        "herokuapp.com",
        "blogspot.com",
        "appspot.com",
        "azurewebsites.net",
        "cloudfront.net",
        "amazonaws.com",
        "web.app",
        "firebaseapp.com",
        "netlify.app",
        "vercel.app",
        "pages.dev",
        "workers.dev",
        "wordpress.com",
    }
)


def validate_domain(value: str) -> str:
    """Normalise a domain and refuse anything that is not one registrable host name.

    The allowlist decides what may be scanned, so a name that would authorise strangers (a bare TLD, a public suffix, an IP
    range-like or wildcard entry) is refused rather than trusted.
    """
    raw = value.strip()
    if not raw:
        raise ValueError("the domain is empty")
    if re.search(r"\s", raw):
        raise ValueError("a domain cannot contain whitespace")
    if "://" in raw:
        raise ValueError("write the domain only, without a scheme such as http://")
    if "*" in raw:
        raise ValueError(
            "wildcards are not allowed: list the domain and its subdomains are included"
        )
    if "/" in raw:
        raise ValueError("write the domain only, without a path")
    try:
        ipaddress.ip_address(raw.strip("[]").rstrip("."))
    except ValueError:
        pass
    else:
        raise ValueError("an IP address is not a domain")
    if re.search(r":\d+$", raw):
        raise ValueError("write the domain only, without a port")
    domain = _norm(raw)
    if len(domain) > 253:
        raise ValueError("the domain is too long")
    labels = domain.split(".")
    if len(labels) < 2:
        raise ValueError("a domain needs at least two labels (for example example.com)")
    if not all(_LABEL.match(label) for label in labels) or not _TLD.match(labels[-1]):
        raise ValueError(f"{domain!r} is not a valid host name")
    if domain in _PUBLIC_SUFFIXES:
        raise ValueError(
            f"{domain} is a public suffix shared by unrelated sites, not a domain you own"
        )
    return domain
