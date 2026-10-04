---
topic: code-editing
priority: low
---

### patch-with-exact-edits-and-verify
_derived_from: reflection/risk-signal-mapping.md, reflection/asn-enrichment.md, reflection/fast-scan-profile.md, reflection/source-health-note.md · evidence_count: 4 · last_validated: 2026-10-04_

Modify source with exact-match edit tools, or assert a scripted replacement actually changed the file; formatters rewrite lines and make blind string replaces miss silently.

### macos-sed-and-chains-skip-silently
_derived_from: reflection/fast-scan-profile.md · evidence_count: 1 · last_validated: 2026-10-04_

On macOS use `sed -i ''` (or an edit tool) and never chain a multi-file edit script after it with `&&`; after any scripted multi-file edit, check `git status`/`git diff` before reporting it done.
