# SPEC: api-keys

Status: approved
Extends: [SPEC-fast-scan-profile.md](SPEC-fast-scan-profile.md) (the lean module list excludes keyed modules), [SPEC-event-catalogue.md](SPEC-event-catalogue.md) (28 event types blocked on API keys)

## Objective

Let the owner give octifoot free API keys for the SpiderFoot modules that use them, so those modules run and feed OpenCTI (more reputation flags, more subdomains, more passive DNS) through the mappings that already exist.
The owner approved this on 2026-10-04 on two conditions: keys must be free ones, and the tool must stay open source in its entirety.

Open-source position: octifoot's code and every dependency it adds stay under open-source licences (no proprietary SDK, client library or bundled service is added). A key is only a credential the owner obtains from a third-party service
and hands to the open-source SpiderFoot module that already talks to it; those services are outside the project and some are proprietary SaaS. The feature is optional and off unless a key file is provided.

Evidence (probed on the running SpiderFoot v4.0):
- 83 modules carry the `apikey` flag; 94 key options exist (`module.<mod>.api_key`, plus a few such as `ipgeolocation_api_key`).
- `GET /optsraw` returns `[SUCCESS, {token, data}]` with options named `module.<mod>.<opt>` and a fresh CSRF token per call; `POST /savesettingsraw` takes `allopts` (JSON) and `token` and **reads names as `<mod>:<opt>`**.
- Writing with the *read* name (`module.<mod>.<opt>`), or with a name that does not exist, returns `SUCCESS` and changes nothing. Only the `<mod>:<opt>` form stores the value (confirmed by reading it back, then reverting it).
  A key that is silently not stored is the worst failure mode here, so the connector must verify what it writes.

Success:
- New optional setting `SPIDERFOOT_API_KEYS_FILE`: path to a JSON object such as `{"sfp_virustotal": "KEY", "sfp_abstractapi:ipgeolocation_api_key": "KEY"}`; a bare module name means `<module>:api_key`, a `module:option` name is used as written. Unset or empty means the feature is off.
- Fail fast at start (a `ConfigError` that never contains a key value) for: unreadable file, invalid JSON, not an object, a blank or over-long value, a control character in a value, an unknown module, a module without the `apikey` flag, or a module flagged `invasive` or `tool` (a key never turns an active module on).
- Before each enrichment the connector applies the keys through SpiderFoot's settings API: it checks the option exists in `optsraw`, writes with the `<mod>:<opt>` name using a fresh token, reads it back and compares. A key that fails any step is dropped for this run and reported by module name only; the others still apply.
- The `lean` module list gains exactly the keyed modules whose key was applied (never an `invasive` or `tool` one); without keys the list is unchanged. The `full` profile needs nothing extra.
- Key values never appear in logs, exceptions, Notes, the work message or any imported object; only module names do. `Settings` and the key holder hide values in `repr`.
- Compose mounts `deploy/secrets/` read-only inside the container; the real key file and anything else in that directory is git-ignored (only a README and an example with placeholders are tracked).
- A failure of the settings API never fails the enrichment: the scan runs without the keys that could not be applied, and the Note's source-health line shows any module whose key the provider rejects.

Out of scope: obtaining or registering keys (that needs the owner's identity and acceptance of each provider's terms); verifying that a key is valid with the provider before scanning (SpiderFoot reports a rejected key as a module error, which the source-health line shows);
mapping new event types that keyed modules emit (they appear in the link to the full SpiderFoot scan and in the "unmapped" counts; mapping needs real data); encrypting the key file or SpiderFoot's own database, where it stores keys in clear.

## Assumptions (approved by the user's standing instruction to proceed)

1. Keys are read from a file, not from environment variables, because environment variables are visible in `docker inspect`; the file is mounted read-only.
2. SpiderFoot keeps the keys in its own settings database inside its volume, in clear text; protecting that volume is the owner's responsibility and is documented.
3. Re-applying keys before every enrichment is cheap (two requests) and heals a SpiderFoot that was reset or redeployed.
4. Which keyed services have a free tier, and on what terms, changes; the documentation names modules and what they add, and tells the owner to read each provider's current terms.

## Commands

```bash
cd connector && . .venv/bin/activate
pytest && ruff check . && ruff format --check .
```

## Test strategy

Unit: key-file parsing and every validation failure (with a sentinel value proving it never leaks); settings client against a mocked SpiderFoot (token, names, read-back, silent no-op detection); the lean list with keyed modules (invasive/tool never; unchanged without keys); connector behaviour (keys applied before scans, dropped on failure, never in output).
Live: the real SpiderFoot round trip with a dummy value on one module (apply, read back, then revert), the connector start-up with a key file, and the module list actually sent for a scan, with no real key and no scan against a third party using a fake credential.

## Boundaries

**Always**: verify what is written by reading it back; log module names, never values; keep the feature off unless configured.
**Ask first**: registering for a service, or sending a credential to a third party for testing.
**Never**: add a proprietary dependency; enable an `invasive` or `tool` module because a key exists; commit a key.
