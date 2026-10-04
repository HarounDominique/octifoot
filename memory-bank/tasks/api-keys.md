---
slug: api-keys
spec: SPEC-api-keys.md
status: approved
---

## Implementation Roadmap

Routing: standard.

- [x] Phase 1 — Key file parsing and validation, settings client, apply-and-verify, lean list with keyed modules, connector wiring, tests (satisfies: SPEC-api-keys.md#objective, SPEC-api-keys.md#boundaries)
- [x] Phase 2 — Compose mount, secrets directory and ignore rules, documentation of keyed modules, live check without a real key (satisfies: SPEC-api-keys.md#test-strategy)

## Execution State

**Build Status**: COMPLETE
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {1: 1, 2: 1}
**Last Block Rule**: none
**Can Resume**: NO

## Deviations

- My first assumption about the settings API was wrong twice: I guessed the write names (`<mod>:<opt>`) correctly from memory but the *read* names turned out to be `module.<mod>.<opt>`, and my first round trip used the read name, which SpiderFoot accepted with `SUCCESS` while storing nothing.
  The design (check the option exists, write under the colon name, read back, compare) comes from that finding. A shell command also failed to parse (an unclosed quote in a commit message) and nothing was created; the files were then written with the file tools.
- Found while verifying: a configuration error made the connector restart in a loop with **no message** in `docker compose logs` (the traceback never appeared). `main()` now validates every setting before registering and exits with code 2 and `octifoot: configuration error: <reason>` on stderr; the same applies to a missing allowlist. Two tests.
- In SpiderFoot v4.0 no module is both keyed and active, so the "a key never enables an active module" guard is defensive; its test tolerates that.
- Free-tier facts in the documentation were checked with web searches on 2026-10-04 (secondary pages): VirusTotal public API 500/day and 4/min, non-commercial; AbuseIPDB 1,000 checks/day; GreyNoise community about 50 searches/week; AlienVault OTX free key with no published limit; SecurityTrails quota not confirmed and therefore not stated.

**Live check (2026-10-04, connector rebuilt from this branch; no real provider key exists, and no credential was sent to any third party):**
- real SpiderFoot settings API through the real connector path with a dummy value (`DUMMY-LIVE-CHECK-KEY-000`) and a simulated scan: the key was stored and verified (`stored in SpiderFoot while the scan ran: the dummy value`), the module list sent was 105 modules, i.e. the 104 lean modules plus exactly `sfp_abuseipdb`, the value was not in the work message, and it was reverted (`stored now: ''`);
- the dummy value appeared in no connector log, no SpiderFoot log, no OpenCTI Note and no external reference (0 matches in each);
- start-up with a valid key file logged `API keys loaded` with module names only; with an invalid file the connector exited with code 2 and the readable message above;
- restored: test file removed, connector recreated without the setting (empty variable, no keys-loaded line), the replay's snapshot Note deleted.
Not seen live: a real provider key working end to end, a provider rejecting a key (the source-health line would name the module), SpiderFoot restarting and losing the keys (the per-enrichment re-apply is unit-tested).
