"""A/B harness: run the same target with the `full` and `lean` profiles, compare what each
would import and how long each took. Talks to a running SpiderFoot; never touches OpenCTI.

    SPIDERFOOT_ALLOWED_DOMAINS=example.com python tools/ab_scan.py \
        --sf-url http://localhost:5001 --target example.com

Acceptance rule (SPEC-fast-scan-profile): identical imported objects and >= 30% faster.
"""

import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from datetime import UTC, datetime

from spiderfoot_connector.abcompare import compare_events, speedup
from spiderfoot_connector.allowlist import is_allowed, parse_allowlist
from spiderfoot_connector.client import SpiderFootClient
from spiderfoot_connector.profiles import lean_modules

MIN_SPEEDUP = 0.30


def _timed(client: SpiderFootClient, target: str, modules, timeout: int):
    start = time.monotonic()
    outcome = client.run_scan(
        target, "passive", timeout_seconds=timeout, poll_seconds=5, modules=modules
    )
    return outcome, round(time.monotonic() - start, 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sf-url", default="http://localhost:5001")
    parser.add_argument("--target", required=True)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--order", choices=["ab", "ba"], default="ab")
    args = parser.parse_args()

    allowlist = parse_allowlist(os.environ.get("SPIDERFOOT_ALLOWED_DOMAINS"))
    if not is_allowed(args.target, allowlist):
        print(f"refusing: {args.target} is not in SPIDERFOOT_ALLOWED_DOMAINS", file=sys.stderr)
        return 2

    client = SpiderFootClient(args.sf_url)
    runs = {}
    for label in args.order:
        modules = None if label == "a" else lean_modules()
        runs[label] = _timed(client, args.target, modules, args.timeout)
    (out_a, secs_a), (out_b, secs_b) = runs["a"], runs["b"]

    comparison = compare_events(
        out_a.events,
        out_b.events,
        target=args.target,
        scan_a=out_a.scan_id,
        scan_b=out_b.scan_id,
        score=30,
        now=datetime.now(UTC),
    )
    saved = speedup(secs_a, secs_b)
    report = {
        "target": args.target,
        "order": args.order,
        "full": {"scan": out_a.scan_id, "seconds": secs_a, "events": len(out_a.events)},
        "lean": {"scan": out_b.scan_id, "seconds": secs_b, "events": len(out_b.events)},
        "speedup": saved,
        "identical_objects": comparison.identical,
        "comparison": asdict(comparison),
        "accepted": comparison.identical and saved >= MIN_SPEEDUP,
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
