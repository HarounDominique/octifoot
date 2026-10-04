# SPEC: control-panel

Status: approved
Extends: [SPEC-spiderfoot-connector.md](SPEC-spiderfoot-connector.md) (authorization model), [SPEC-watch-automation.md](SPEC-watch-automation.md) (the watcher reads the allowlist)

## Objective

Let the operator, from a web page, (1) add and remove the domains octifoot is allowed to analyse, and (2) change the maximum time one analysis may take, instead of editing `deploy/.env` and recreating the container.
The owner asked for this on 2026-10-04 after a scan of a large site hit the fixed 15-minute limit.

octifoot has no interface of its own (analysts use OpenCTI and SpiderFoot's UI), so this is a small control panel served by the connector process.

**This page controls the authorization boundary**, the one thing that decides what may be scanned. The design therefore starts from how it could be abused and makes the safe path the default:

- reachable only from the operator's own machine (published on `127.0.0.1`), and only with a secret token; disabled entirely when no token is configured;
- adding a domain requires an explicit confirmation that the operator owns it or has written permission;
- nothing the page does can add something the connector's own rules would reject (names are validated; single labels, IPs, wildcards and URLs are refused);
- every change is recorded in an audit log; the `.env` list stays and cannot be removed from the page.

Success:
- **Authorized domains.** The effective allowlist is the `.env` list (`SPIDERFOOT_ALLOWED_DOMAINS`, read-only in the page) plus the domains added from the page, stored in a state file in a Docker volume. Both the manual enrichment and the watcher use the effective list, re-read at each use.
  A domain added from the page is analysable immediately and removable at any time; removing it does not delete anything already imported.
- **Maximum time.** A value between 60 and 7200 seconds can be set from the page; it applies to the next analysis, not to ones already running; clearing it falls back to `SPIDERFOOT_TIMEOUT_SECONDS`. The Note's "stopped after N s" uses the value actually applied.
- **Validation (also applied to `.env`).** A domain must be a valid host name with at least two labels, not an IP address, not a known multi-part public suffix (`co.uk`, `com.au`...), no scheme, path, port, wildcard or whitespace, at most 253 characters. A bad `.env` entry is a `ConfigError` (the connector refuses to start and says which).
  Entries that were valid before stay valid.
- **Access.** The page needs `OCTIFOOT_UI_TOKEN` (at least 16 characters). Login sets an `HttpOnly`, `SameSite=Strict` session cookie; every change needs a per-session CSRF token; requests whose `Host` is not `localhost`/`127.0.0.1` on the panel's port are refused (DNS rebinding); repeated failed logins are throttled; responses carry `Content-Security-Policy`, `X-Frame-Options: DENY` and `Cache-Control: no-store`; the token is never logged or echoed.
- **Audit.** Each add, remove and time change appends one line (UTC time, action, value, client address) to an audit log in the state volume; the log never contains the token.
- **Limits.** At most 100 domains can be added from the page.
- **Language.** English by default; Spanish with `OCTIFOOT_UI_LANG=es`.
- A corrupt or unreadable state file is treated as empty (the `.env` list and defaults apply) and the page says so; it never raises into an enrichment.

Out of scope: user accounts or roles (one operator, one token); HTTPS (the panel is local; put a reverse proxy with TLS in front before exposing it, which is not recommended); starting an analysis from the page (OpenCTI does that); editing any other setting; importing or exporting domain lists; the watch interval.

## Assumptions (approved by the user's standing instruction to proceed)

1. The operator is one person with access to the machine and to `deploy/.env`; the token lives there, like the OpenCTI admin credentials.
2. The panel uses only the Python standard library (`http.server`): no new dependency, so the project stays open source with nothing extra to audit.
3. A hand-kept list of common multi-part public suffixes (not the full Public Suffix List) is enough as a guard; it is a safety net, not a guarantee, and the confirmation checkbox is the real control.
4. The state file lives at `OCTIFOOT_STATE_DIR` (default `/var/lib/octifoot`, a named volume); the connector's non-root user owns it.
5. The effective allowlist is recomputed at each use, so a removal takes effect for the next analysis and the next watcher cycle; an analysis already running keeps going.

## Commands

```bash
cd connector && . .venv/bin/activate
pytest && ruff check . && ruff format --check .
```

## Test strategy

Unit: domain validation (accepted and refused forms), the state store (add, remove, duplicate, limit, persistence, corrupt file, atomic write, audit lines), effective allowlist and timeout, the connector and watcher using the runtime values, `.env` validation.
HTTP, against a real server on an ephemeral port: login required, wrong and right token, CSRF, confirmation required, validation messages, removal, time bounds, Host check, cookie flags, security headers, throttling, no token in responses or the audit log, escaping, disabled without a token, language.
Live: bring the panel up in Compose, add a domain, run an analysis on it without touching `.env`, change the time and see it in the Note, remove the domain and see the analysis refused.

## Boundaries

**Always**: require the token and the ownership confirmation; validate every name; log every change.
**Ask first**: exposing the panel beyond localhost; adding roles or remote access; any new web dependency.
**Never**: let the page authorize a name the validation rejects; accept a change without CSRF and session; log or print the token.
