---
topic: code-editing
priority: low
---

### patch-with-exact-edits-and-verify
_derived_from: reflection/risk-signal-mapping.md, reflection/asn-enrichment.md, reflection/fast-scan-profile.md, reflection/source-health-note.md, reflection/scan-changes.md · evidence_count: 5 · last_validated: 2026-10-04_

Modify source with exact-match edit tools, or assert a scripted replacement actually changed the file; formatters rewrite lines and make blind string replaces miss silently.

### macos-sed-and-chains-skip-silently
_derived_from: reflection/fast-scan-profile.md · evidence_count: 1 · last_validated: 2026-10-04_

On macOS use `sed -i ''` (or an edit tool) and never chain a multi-file edit script after it with `&&`; after any scripted multi-file edit, check `git status`/`git diff` before reporting it done.

### patch-from-the-current-text-never-from-memory
_derived_from: reflection/scan-changes.md, reflection/spiderfoot-ui-link.md, reflection/api-keys.md · evidence_count: 3 · last_validated: 2026-10-04_

Run the formatter before writing a scripted patch and build its search strings from the file as it is now; a patch whose pattern stopped matching after a reformat leaves the code half-edited, so apply scripted edits one by one and check each reports success.

### read-a-status-flag-after-refreshing-what-it-describes
_derived_from: reflection/control-panel.md · evidence_count: 1 · last_validated: 2026-10-04_

When an object keeps a status flag set by its last read (such as a `problem` message), refresh the data before reading the flag; reading it first reports the previous read's state.

### inject-the-clock-for-deadlines
_derived_from: reflection/total-deadline.md · evidence_count: 1 · last_validated: 2026-10-04_

Take the clock as a constructor argument (default `time.monotonic`) for any time budget, and let the fake scan advance it; deadline logic is then tested without waiting.

### when-a-new-test-and-the-spec-disagree-check-the-spec-first
_derived_from: reflection/total-deadline.md · evidence_count: 1 · last_validated: 2026-10-04_

A test written before the code can encode a miscount; re-read the spec sentence it claims to check before changing the code to satisfy it, and run the linter on new tests (it caught `or True`).
