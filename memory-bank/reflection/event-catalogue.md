# Reflection: event-catalogue

Date: 2026-10-04 · Spec: SPEC-event-catalogue.md (approved) · Plan: 2 phases DONE · Live check: data derived from the running SpiderFoot (event types, 21 stored scans)

## Implementation vs spec

| Spec requirement | Result |
|---|---|
| One entry per SpiderFoot event type with needs, producers, observed counts, decision and rationale | Met: 172 entries |
| Tests fail on missing entries, undecided observed types, imported ≠ mapper, non-declined third-party families, doc/JSON drift | Met (13 catalogue tests) |
| Decisions on observed types rest on real values | Met: the values were read for every candidate before deciding |

Deviations: tests were written before the spec file; one test assumption was wrong (see below). Both accepted.

## What the catalogue showed

- The headline "15 of 172 imported (9 %)" is misleading. Passive keyless scans emitted only 46 distinct types in 21 scans; octifoot imports 15 of those 46 and
  declines most of the rest on purpose. The remaining 126 types are not a mapping backlog: 61 are producible but never seen, 17 come only from deny-listed modules,
  28 need an API key and 6 need active modules. Closing the gap with SpiderFoot standalone is mostly about what runs (keys, active modules), not about the mapper.
- Reading the real values corrected a plan: company names, addresses, LEIs and phone numbers were the registry, the registrar and a privacy proxy, not the target.
- `EMAILADDR` is imported but never appeared in any real scan: that mapper has only been proven on fixtures. The catalogue now makes that visible.
- Evidence for source choices appeared as a by-product: AS names are missing because `api.bgpview.io` fails on every request; `sfp_certspotter` (keyed) is a
  certificate-transparency alternative to crt.sh.

## Workflow evaluation

- Deriving everything from SpiderFoot's own tables and the running instance, and making the page a generated artefact with a drift test, means the
  catalogue cannot silently go stale when the mapper changes.
- I wrote a test that encoded an assumption (every unobserved type is blocked or no-data); the failing run found `EMAILADDR` and turned a hidden gap into a stated fact.
- Counting what real runs produce changed the question from "how do we map 97 more types" to "which of the 31 observed-but-unimported are worth it", which is a much smaller and better-founded backlog.

## Rules extracted

- New `measure-coverage-against-observed-output` (external-integrations).
- Reinforced: `inspect-real-output-before-specifying-a-mapping` (evidence 5).

## Follow-ups (not blocking)

- Slices already named in the catalogue: `whois-dns-notes`, `x509-certificates`.
- Owner decisions the catalogue exposes: which API keys to obtain, and whether any active module may ever run against an authorised target.
