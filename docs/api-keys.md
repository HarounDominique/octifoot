# Free API keys (optional)

octifoot works without any key. Some SpiderFoot modules query services that ask for a free API key; without one they simply do not run. If you obtain such keys you can hand them to octifoot, and those modules join the scan and feed the same OpenCTI
objects as before (more reputation flags on IPs and hostnames, more subdomains, more passive DNS). Nothing new is mapped: see "What it adds" below.

**Open source.** octifoot's code and everything it depends on stay open source; this feature adds no dependency. A key is only a credential that you obtain from a third-party service and give to the open-source SpiderFoot module that already talks to it.
Those services are hosted by their vendors and are outside this project; read each one's current terms before using it. The feature is off unless you provide a key file.

## How to use it

1. Register for the service yourself (this needs your identity and your acceptance of its terms; octifoot never does that for you) and copy your key.
2. Create `deploy/secrets/api-keys.json` (it is git-ignored; copy `api-keys.example.json`):

   ```json
   {
     "sfp_abuseipdb": "your key",
     "sfp_virustotal": "your key",
     "sfp_alienvault": "your key"
   }
   ```

   A bare module name means that module's `api_key` option. Modules with more than one key use `module:option` (for example `"sfp_abstractapi:ipgeolocation_api_key"`).
3. In `deploy/.env` set `SPIDERFOOT_API_KEYS_FILE=/run/octifoot-secrets/api-keys.json` (the `deploy/secrets/` directory is mounted read-only at `/run/octifoot-secrets`) and recreate the connector:
   `docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d connector-spiderfoot`.

At start the connector refuses a bad file and says which entry is wrong (never the value): unreadable or invalid JSON, a blank or over-long key, an unknown module, a module that does not use a key, or an active (`invasive`/`tool`) module: a key never switches an active module on.

## What happens at each enrichment

Before the scan the connector writes each key into SpiderFoot's settings and **verifies it by reading it back**. This matters: SpiderFoot answers `SUCCESS` to a settings write under a wrong or non-existent option name and stores nothing, so a key can
look accepted and be silently ignored. A key that cannot be verified is dropped for that run and its option name (not its value) is logged; the others still apply. The `lean` module list then gains exactly the modules whose key was verified.
If SpiderFoot's settings API is unreachable the scan runs without keys. Key values never appear in logs, Notes, imported objects or error messages.

If a provider rejects a key, SpiderFoot reports an error for that module and the **source-health line** of the Note names the module (for example `sfp_abuseipdb: ... 401`). That line is how you find out that a key is wrong or exhausted.

## What it adds

Keyed modules that produce event types octifoot already imports (from SpiderFoot's own module metadata): 52 of them. By what they add:

| Adds to OpenCTI | Modules (without the `sfp_` prefix) |
|---|---|
| Malicious flag on IPs (`MALICIOUS_IPADDR`) | abuseipdb, abusix, alienvault, badpackets, binaryedge, botscout, focsec, fraudguard, googlesafebrowsing, greynoise, honeypot, iknowwhatyoudownload, ipqualityscore, and others |
| Subdomains (`INTERNET_NAME`) | alienvault, binaryedge, builtwith, c99, certspotter, dnsdb, fsecure_riddler, fullhunt, hybrid_analysis, intelx, leakix, networksdb, onyphe, projectdiscovery, and others |
| More IPs and IPv6 | alienvault, dnsdb, networksdb, spyse, hostio, riskiq, c99, and others |
| Emails of the target | builtwith, clearbit, dehashed, emailcrawlr, fullcontact, hostio, hunter, intelx, snov, spyse, and others |
| Malicious flag on hostnames / listings on subnets and co-hosts | virustotal, abusix, googlesafebrowsing, ipqualityscore, malwarepatrol, metadefender, pulsedive, xforce, greynoise, honeypot |
| Certificates | certspotter (an alternative source to crt.sh, which is frequently down) |

Everything else those modules emit (open ports, vulnerabilities, banners...) is not mapped (octifoot has never seen real data for those types, see `docs/event-catalogue.md`), but it is kept in SpiderFoot and reachable through the link at the top of each scan Note.
The lines for flagged IPs and hostnames use the same label and the same shared-infrastructure rule as before, so more feeds mean more reputation evidence, not new kinds of object.

## Free tiers (checked on 2026-10-04 from public pages; they change, read the provider's own terms)

| Service (module) | Free access, as found |
|---|---|
| VirusTotal (`sfp_virustotal`) | public API key: 500 requests/day and 4 per minute; non-commercial use only |
| AbuseIPDB (`sfp_abuseipdb`) | free account: 1,000 checks per day |
| AlienVault OTX (`sfp_alienvault`) | free key with a free account; no published rate limit for indicator lookups |
| GreyNoise (`sfp_greynoise`) | community access: about 50 searches per week, shared with its web visualiser |
| SecurityTrails (`sfp_securitytrails`) | a limited free plan exists; the quota was not confirmed, check their pricing page |

A scan of one domain makes many requests (one per host and IP in some modules), so a small free quota can run out within a few scans; the source-health line will show the module failing when it does.

## Where the keys are stored

In `deploy/secrets/api-keys.json` (git-ignored, mounted read-only), and, once applied, inside SpiderFoot's own settings database in its Docker volume **in clear text**: that is how SpiderFoot stores them. Treat that volume and the file as secrets;
do not publish backups of either, and never commit the file (the directory's `.gitignore` allows only its README and the example). Revoke a key at the provider if either leaks.
