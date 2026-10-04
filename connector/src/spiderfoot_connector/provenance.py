"""Reproducibility and coverage lines for a scan's Note.

The digest proves that an import matches what SpiderFoot returned (identity of content);
it does not prove the authenticity of the sources behind it.
"""

import hashlib
import json
from collections.abc import Sequence

DIGEST_SHOWN = 16  # hex characters shown in the Note; the full SHA-256 is 64


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def events_digest(events: Sequence[dict]) -> str:
    """SHA-256 of the canonical JSON of the events (sorted keys, sorted events)."""
    rows = sorted(json.dumps(e, sort_keys=True, default=str, ensure_ascii=False) for e in events)
    return _sha256("\n".join(rows))


def provenance_line(
    *,
    octifoot_version: str,
    spiderfoot_version: str,
    profile: str,
    usecase: str,
    modules: Sequence[str] | None,
    seconds: int,
    events: Sequence[dict],
) -> str:
    """Which tools and settings produced this scan, and a digest of what came back."""
    if modules is None:
        requested = "modules: SpiderFoot's passive group"
    else:
        listing = _sha256("\n".join(sorted(modules)))[:DIGEST_SHOWN]
        requested = f"modules requested: {len(modules)} (list sha256 {listing})"
    return (
        f"Provenance: octifoot {octifoot_version}; SpiderFoot {spiderfoot_version or 'unknown'}; "
        f"profile {profile}, use case {usecase}; {requested}; time applied {seconds} s; "
        f"events: {len(events)} (sha256 {events_digest(events)[:DIGEST_SHOWN]})"
    )


def coverage_line(
    events: Sequence[dict], source_errors: Sequence[tuple[str, str]], keyed: frozenset[str]
) -> str:
    """How much of the source space answered; silence from a source is not evidence of absence."""
    producing = {
        str(e.get("module", "")) for e in events if str(e.get("module", "")).startswith("sfp_")
    }
    erroring = {module for module, _ in source_errors}
    text = (
        f"Coverage: {len(producing)} {'module' if len(producing) == 1 else 'modules'} produced data; "
        f"{len(erroring)} {'module' if len(erroring) == 1 else 'modules'} reported errors"
    )
    if keyed:
        text += f"; API-keyed modules active: {', '.join(sorted(keyed))}"
    return text + ". A source that answers 'no information' cannot be told from silence."
