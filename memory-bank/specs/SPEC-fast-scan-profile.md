# SPEC: fast-scan-profile

Status: approved
Extends: [SPEC-spiderfoot-connector.md](SPEC-spiderfoot-connector.md) (client, config, connector wiring)

## Objective

Make scans noticeably faster while importing (practically) the same objects, by running
SpiderFoot with an explicit module list instead of the whole "Passive" group, and **prove it
with an A/B comparison** before making it the default.

Evidence (recorded scan `DF50665A`, registrolineas.com, 375 s, 447 events): only 38 events
(8.5%) were imported. The tail of the scan is a chain that works on third parties we discard:
`sfp_robtex` (145 co-hosted sites) → `sfp_dnsresolve` (107) → `sfp_whois` (49) → `sfp_email` (57)
→ `sfp_countryname` (38). Module metadata read from SpiderFoot v4.0: 236 modules, 201 Passive;
`robtex` watches `IP_ADDRESS` and produces `CO_HOSTED_SITE`, consumed by those four modules.
`sfp_crt` (our subdomain source) also produces `CO_HOSTED_SITE`, so excluding by event type is wrong.

Success:
- `SPIDERFOOT_PROFILE=full` behaves exactly as the pre-profile connector (default only when the use case is not `passive`).
- `SPIDERFOOT_PROFILE=lean` starts scans with an explicit `modulelist`: SpiderFoot's passive
  modules without API key, `invasive` or `tool` flags, minus a deny-list of modules that only
  feed discarded data (`sfp_robtex`, `sfp_countryname`).
- A/B on the same domains: the set of imported STIX ids is identical, except documented losses,
  and lean takes at least 30% less time. Only then does `lean` become the default.
  *(Amended: the user made `lean` the default on 2026-10-04 although the rule was met on one
  domain only; see the task file, Deviations. A later A/B with validated runs, SPEC-ab-validity-and-cloud-bucket-deny, met the
  rule on both domains: 64.8 % and 87.2 %.)*
- The lean list can never contain an active module (enforced by a test against SpiderFoot's own metadata).

Out of scope: changing SpiderFoot module options globally, parallel scans, caching of recent
scans, module selection per event type.

## Assumptions (approved by the user's standing instruction to proceed)

1. `startscan` accepts `modulelist` (verified in SpiderFoot source); when given, `usecase` is ignored,
   and `sfp__stor_db` is added by SpiderFoot itself.
2. The lean list is derived from SpiderFoot v4.0 module metadata (`useCases`, `flags`, `watched`,
   `produced`) by a pure function and committed as data together with the metadata snapshot it
   came from, so it is reproducible and testable without Docker.
3. Deny-list is small and evidence-based: `sfp_robtex`, `sfp_countryname`. Anything more needs A/B evidence.
4. Known, accepted loss: `MALICIOUS_COHOST` lines in the scan Note (they come from `comodo`/`opendns`
   checking co-hosted sites). Imported objects must not change.
5. `lean` requires `SPIDERFOOT_USECASE=passive`; any other combination is a `ConfigError`.
6. Lean list is tied to the pinned SpiderFoot (`v4.0`); changing the pin requires regenerating it.
7. Maltiverse is non-deterministic, so the A/B compares object ids and reports label/reference
   differences separately instead of failing on them.
8. Acceptance thresholds: identical imported ids (excluding Note), ≥ 30% faster on at least two domains.

## Commands

```bash
cd connector && . .venv/bin/activate
pytest tests/unit -q
pytest && ruff check . && ruff format --check .
python tools/ab_scan.py --help        # A/B harness (talks to a running SpiderFoot)
```

## Structure

```
connector/src/spiderfoot_connector/profiles.py        # pure: derive lean list from metadata
connector/src/spiderfoot_connector/data/sf_modules_v4.0.json   # metadata snapshot
connector/src/spiderfoot_connector/data/lean_modules.json      # generated list
connector/src/spiderfoot_connector/{config,client,connector}.py # profile plumbing
connector/tools/ab_scan.py                            # harness (pure compare + CLI)
connector/tests/unit/test_profiles.py, test_ab_compare.py, test_client_*.py, test_config.py
docs/README.md, deploy/docker-compose.yml, deploy/.env.example
```

## Style

```python
def derive_lean(meta: dict[str, dict], deny: frozenset[str]) -> list[str]:
    """Passive, keyless, non-invasive modules reachable from the target, minus deny."""
```

## Test strategy

- Unit, TDD, no network: `derive_lean` on a small synthetic metadata set (passive/active,
  apikey, invasive, unreachable, deny) and on the real snapshot (must exclude deny-list, must
  include `sfp_crt`, `sfp_dnsraw`, `sfp_dnsresolve`, `sfp_maltiverse`, `sfp_ripe`, `sfp_voipbl`,
  must be a subset of Passive, no `invasive`/`tool`/`apikey`); config (profile values, lean needs
  passive); client sends `modulelist` and no `usecase` for lean, unchanged for full; connector passes the profile.
- A/B compare is a pure function, unit-tested (identical, extra, missing, label-only differences).
- Live: run the harness against the real SpiderFoot on two domains (one behind a CDN, one with
  subdomains), record times and diffs in the task file, then apply the acceptance rule.

## Boundaries

**Always**
- Keep `full` available and identical to current behaviour.
- Derive and test the lean list from SpiderFoot's metadata; keep it passive-only.
- Decide the default from measured A/B results and record them.

**Ask first**
- Adding modules to the deny-list without A/B evidence; changing SpiderFoot's global settings.
- Enabling parallel scans.

**Never**
- Put an `invasive`, `tool` or non-Passive module in the lean list.
- Switch the default to lean without the A/B passing the acceptance rule.
- Commit API keys or real third-party data into the snapshot or fixtures.
