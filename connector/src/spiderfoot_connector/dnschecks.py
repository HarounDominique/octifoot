"""The target's own mail-authentication and DNS-hardening records, queried directly.

SpiderFoot never asks for ``_dmarc``, CAA, DS or ``_mta-sts``, so its events cannot say whether they exist.
Each result is *found* (a value), *confirmed absent* (NXDOMAIN or an empty answer) or *unknown* (``None``:
timeout, SERVFAIL, resolver error). Unknown is never reported as absent.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass

import dns.exception
import dns.resolver

# lookup(name, rdtype) -> text records; [] = confirmed absent; None = could not be determined
Lookup = Callable[[str, str], list[str] | None]
RESOLVER_TIMEOUT = 5.0

_DMARC_P_RE = re.compile(r"(?:^|;)\s*p\s*=\s*([a-z]+)", re.IGNORECASE)
_SPF_ALL_RE = re.compile(r"(?:^|\s)([+\-~?]?)all(?:\s|$)", re.IGNORECASE)


@dataclass(frozen=True)
class DnsFacts:
    mx: list[str] | None
    spf: str | None  # "" = TXT answered without an SPF record
    dmarc: str | None
    caa: list[str] | None
    ds: list[str] | None
    mta_sts: str | None


def default_lookup(name: str, rdtype: str) -> list[str] | None:
    resolver = dns.resolver.Resolver()
    resolver.lifetime = RESOLVER_TIMEOUT
    try:
        answer = resolver.resolve(name, rdtype)
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return []
    except (dns.exception.DNSException, OSError):
        return None
    records = []
    for rdata in answer:
        if rdtype == "TXT":
            records.append(b"".join(rdata.strings).decode("utf-8", "replace"))
        elif rdtype == "MX":
            records.append(f"{rdata.preference} {rdata.exchange.to_text()}")
        else:
            records.append(rdata.to_text())
    return records


def _txt_record(records: list[str] | None, prefix: str) -> str | None:
    """First record starting with ``prefix`` (case-insensitive); "" if the answer had none; None if unknown."""
    if records is None:
        return None
    return next((r for r in records if r.lower().startswith(prefix)), "")


def check_domain(name: str, lookup: Lookup = default_lookup) -> DnsFacts:
    mx_raw = lookup(name, "MX")
    # A null MX ("0 .", RFC 7505) says the domain accepts no mail, so it is dropped, not listed.
    mx = (
        None
        if mx_raw is None
        else sorted(h for r in mx_raw if (h := r.split()[-1].rstrip(".").lower()))
    )
    return DnsFacts(
        mx=mx,
        spf=_txt_record(lookup(name, "TXT"), "v=spf1"),
        dmarc=_txt_record(lookup(f"_dmarc.{name}", "TXT"), "v=dmarc1"),
        caa=lookup(name, "CAA"),
        ds=lookup(name, "DS"),
        mta_sts=_txt_record(lookup(f"_mta-sts.{name}", "TXT"), "v=stsv1"),
    )


def spf_all_qualifier(spf: str) -> str | None:
    """The qualifier of the ``all`` mechanism ("+all" when none is written), or None without one."""
    m = _SPF_ALL_RE.search(spf)
    return None if m is None else f"{m.group(1) or '+'}all"


def dmarc_policy(dmarc: str) -> str | None:
    m = _DMARC_P_RE.search(dmarc)
    return m.group(1).lower() if m else None
