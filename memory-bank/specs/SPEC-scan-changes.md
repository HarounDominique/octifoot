# SPEC: scan-changes

Status: approved
Extends: [SPEC-opencti-knowledge.md](SPEC-opencti-knowledge.md) (reads the platform), [SPEC-partial-scan-visibility.md](SPEC-partial-scan-visibility.md) (completeness)

## Objective

Report what changed since the previous scan of the same domain. OpenCTI stores the graph but does not say what is new; SpiderFoot scans are independent snapshots with no memory. Attack-surface work is mostly about change
(a new host, a new IP, a changed mail setup), so the connector remembers the last result and diffs against it.

State lives in OpenCTI, not in the container: each enrichment of a root target writes one Note whose abstract is `octifoot snapshot for <target>: <summary>`, whose text lists the changes in plain language and ends with a
machine-readable snapshot line; the next run reads the newest such Note (`attribute_abstract` starts with `octifoot snapshot for <target>:`) and compares.

Success:
- The snapshot holds, for the merged result of the enrichment: hostnames (without the target), IPs, emails, certificate serials, AS numbers, registrar, hosting, name servers, mail hosts, SPF and DMARC state (only when the direct DNS check ran), scan id, time and whether the scan was complete.
- With a previous snapshot, the Note lists per category what is **added** and what is **not seen this time**; with no change it says so; with no previous snapshot it says it is the first and that nothing can be compared.
- Disappearances are reported only when **both** scans were complete; otherwise the Note says disappearances are not reported and why. When subdomain sources reported errors in this scan, the not-seen hostnames carry the caveat that they may not be gone.
- Additions against an incomplete previous scan carry the caveat that they may not be new.
- Certificates: only additions (the import is capped at the 10 newest, so removals would be artefacts). SPF/DMARC: reported as a change of state (none / present / policy) when both snapshots hold a known state.
- A failing read of the previous snapshot still writes the new snapshot and says the previous one could not be read; a failing write path never fails the enrichment.
- Expansion sub-scans do not get their own snapshot; the root's snapshot covers the merged set.

Out of scope: WHOIS date changes (kept in Note text, not snapshotted), scheduling re-scans (OpenCTI enriches on demand or on entity events), alerting, history beyond the previous snapshot.

## Assumptions (approved by the user's standing instruction to proceed)

1. Notes are immutable history: a new Note per enrichment; the newest by creation time is "previous". Deleting Notes resets the baseline.
2. The snapshot line is JSON with a version field (`v: 1`); an unreadable or unknown-version snapshot is treated as "previous could not be read".
3. At most 10 values per category are listed, then "and N more".
4. A scan is complete when it was not stopped by the timeout and ended FINISHED.

## Commands

```bash
cd connector && . .venv/bin/activate
pytest && ruff check . && ruff format --check .
```

## Test strategy

Unit, pure: snapshot building, JSON round trip, diff for every category, removal suppression rules, caveats, first snapshot, no change, deterministic text, retrieval with a fake query (newest wins, unreadable ignored).
Connector: Note written with and without a previous snapshot, failure isolation, root only.
Live: replay two recorded real scans of zonetransfer.me in sequence and read the second Note back.

## Boundaries

**Always**: say when a comparison is unreliable (incomplete scans, failing sources).
**Ask first**: scheduling or alerting from changes.
**Never**: report a disappearance as fact when either scan was incomplete.
