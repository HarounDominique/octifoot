---
slug: reputation-and-infra-notes
spec: SPEC-reputation-and-infra-notes.md
status: approved
---

## Implementation Roadmap

Routing: standard (one mapper extension, no new object types).

- [x] Phase 1 — Mapper: flagged hostnames labelled, infrastructure Note line, `IMPORTED_EVENTS` extended, tests (satisfies: SPEC-reputation-and-infra-notes.md#objective, SPEC-reputation-and-infra-notes.md#boundaries)
- [x] Phase 2 — Docs + live check: README table, rebuild connector, enrich a real domain, read Note and labels back (satisfies: SPEC-reputation-and-infra-notes.md#test-strategy)

## Execution State

**Build Status**: COMPLETE
**Current Phase**: —
**Current Step**: —
**Step Attempts**: {1: 1, 2: 1}
**Last Block Rule**: none
**Can Resume**: NO

## Deviations

**Live check (2026-10-04, OpenCTI 7.261002.0, connector rebuilt from this branch)**

- Fresh enrichment of bugoverflow.com: work complete, 20/20, no errors, 2 min 23 s (scan AD468000). The Note in OpenCTI carries the
  line `Infrastructure (as reported by SpiderFoot): registrar: Dinahosting s.l.; hosting: dinahosting; DNS: ns.dinahosting.com, ns2..., ns3..., ns4...; mail: mail.dinaserver.com`,
  and the four infrastructure types no longer appear under "Unmapped".
- That scan did not contain a `MALICIOUS_INTERNET_NAME` event (Comodo flagged `redirecciones.dinaserver.com` in 1 of 5 scans of this domain: it is
  non-deterministic), so the label could not appear. It was verified by replaying the recorded real events of scan `635DE72C` through the real
  connector path (`process_message` with the real helper, queue and worker): work complete 20/20, no errors; the observable
  `redirecciones.dinaserver.com` has label `spiderfoot:malicious` and the reference "Comodo Secure DNS 635DE72C - Flagged malicious by Comodo Secure DNS (SpiderFoot module sfp_comodo)";
  the Note has the Infrastructure line and `BLACKLISTED_INTERNET_NAME` stays unmapped.
- A first replay through a direct API import (`import_bundle_from_json`) showed neither the label nor the reference; the connector path showed both.
  Cause of the difference not investigated.
- Old vs new mapper on the real events of two scans: identical object ids (19 and 18), only the Note and the one label differ.
- Scope reduced against the original idea of "ports, banners, technologies, indicators, AS names, non-CTI, bidirectional loop": evidence found no passive events for
  ports/banners/technologies, `BLACKLISTED_*` is not a duplicate of `MALICIOUS_*`, and the rest need their own specs (see the spec's Out of scope).
