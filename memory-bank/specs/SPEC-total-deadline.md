# SPEC: total-deadline

Status: approved
Extends: [SPEC-iterative-scan-loop.md](SPEC-iterative-scan-loop.md) (expansion), [SPEC-partial-scan-visibility.md](SPEC-partial-scan-visibility.md), [SPEC-control-panel.md](SPEC-control-panel.md) (the panel edits the time settings)

## Objective

One enrichment must be bounded as a whole and must not hold its results hostage until its last step. Today the limit is per scan, and an expansion multiplies it: with `SPIDERFOOT_MAX_SCANS=5` and a 900 s limit one enrichment can run 75 minutes, and everything is sent to OpenCTI only when the last
scan ends. Seen live on 2026-10-04 (forocoches.com): after about 40 minutes the operator stopped it and the four finished scans were lost from OpenCTI (the data stayed in SpiderFoot, and the root scan had to be re-imported by hand).

Success:
- **Total deadline.** `SPIDERFOOT_MAX_TOTAL_SECONDS` (60 to 86400, default 3600) bounds one whole enrichment (all its scans). Each scan gets `min(per-scan limit, time left)`; a scan is not started when less than 60 s is left; targets skipped for that reason are named in the expansion Note
  (`Skipped, total time limit reached (N s): ...`) and in the work message, and the snapshot is marked incomplete.
- **Results as they finish.** When an expansion is enabled and more scans are queued, the objects and Note of the scan that just finished are sent to OpenCTI immediately (only objects not yet sent). The final bundle still carries everything (the authoritative version; identifiers are deterministic, so repeating an object is idempotent).
  A run stopped, killed or failing after some scans therefore keeps what was already sent. A run with a single scan sends exactly one bundle, as before.
- **Applied time is reported.** A scan cut by the limit says `stopped after N s` with the time that was actually applied to it (which may be less than the per-scan limit when the total is nearly spent).
- **Control panel.** The maximum total time can be changed there too (60 to 14400 s, empty = default), applying to the next analysis, audited like the other changes.
- Root scan failures still fail the work (nothing partial is hidden); sub-scan failures still do not lose what was collected.

Out of scope: cancelling a running analysis (a separate control); splitting one scan's time between modules; importing partial results *inside* one scan.

## Assumptions (approved by the user's standing instruction to proceed)

1. 60 s is the smallest useful scan budget (the same minimum as the per-scan time in the panel).
2. Sending an object twice (early bundle and final bundle) costs a little extra work in OpenCTI and nothing else, because ids are deterministic; the benefit is a self-contained early bundle without reordering the existing final-bundle logic.
3. The default of 3600 s is one hour: shorter than the 75-minute worst case seen, long enough for the usual five-scan expansion of a normal domain.
4. The deadline uses a monotonic clock injected into the enrichment, so it is testable without waiting.

## Commands

```bash
cd connector && . .venv/bin/activate
pytest && ruff check . && ruff format --check .
```

## Test strategy

Unit with a fake clock: the order of scans and sends, what each early bundle holds, single-scan runs, a failure after the first scan, the per-scan time under a total, the skip below 60 s and its reporting, the incomplete snapshot, configuration bounds, the panel and store for the new setting.
Live: lower the total in the panel, analyse a domain that expands, and see the early bundle arrive before the end, the skipped targets named and the work finish within the limit.

## Boundaries

**Always**: bound the whole enrichment; report what was skipped and why; keep the final bundle complete.
**Ask first**: cancelling analyses, or changing the default total.
**Never**: hold finished scans' results until the last scan ends when more scans are queued; exceed the total deadline by starting a scan with too little time left.
