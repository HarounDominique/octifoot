# Reflection: reputation-and-infra-notes

Date: 2026-10-04 · Spec: SPEC-reputation-and-infra-notes.md (approved) · Plan: 2 phases DONE · Live check: fresh scan plus replay through the real connector path

## Implementation vs spec

| Spec requirement | Result |
|---|---|
| Imported flagged hostname, or the target, gets the label and one reference per feed | Met; unit-tested, and live via replay of real events |
| Flagged hostname not imported is counted, never imported | Met (unit-tested); not seen live |
| Note has one `Infrastructure` line, sorted, de-duplicated, capped; those types leave "Unmapped" | Met; live on a fresh scan and on the replay |
| `BLACKLISTED_*`, `PUBLIC_CODE_REPO`, affiliates stay unmapped and counted | Met |
| Existing object ids unchanged | Met: identical id sets on real events of two scans |
| Live: label and Note read back from OpenCTI | Met for both, but the label only through the replay: the fresh scan had no flag event |

Deviations: none from the spec. The spec itself already narrowed the original idea, see below.

## Scope decision, from evidence

The list of "possible next steps" in the archives (ports/banners/technologies, `Indicator` objects with CDN filtering, AS names,
non-CTI entities, a bidirectional loop) was checked against what real passive scans contain before writing the spec:
- Ports/banners/technologies: zero such events in any recorded passive scan; nothing to map.
- `BLACKLISTED_*`: I first assumed it duplicates `MALICIOUS_*`. Comparing the two sets per module showed `sfp_cloudflaredns` emits
  `BLACKLISTED_COHOST` alone (its "Family" content filter). Mapping it as malicious would have labelled benign hosts. It stays unmapped.
- The data did show two unmapped, useful signals (`MALICIOUS_INTERNET_NAME`, providers), which became this task.
- Left out with reasons recorded in the spec: AS names (not in events), `Indicator`/CDN policy, `PUBLIC_CODE_REPO` (name matches by unrelated people),
  non-CTI entities and an OpenCTI-triggered loop (own specs; the loop also needs the multi-scan expansion verified live first).

## Workflow evaluation

- The hostname flag is non-deterministic: Comodo flagged it in 1 of 5 scans of the same domain, and in none of the three lean scans. A live test
  that depends on it needs a recorded event to replay; the fresh-scan check alone would have passed without exercising the feature.
- A direct API import of the bundle showed no label and no reference, while the same events through the connector helper and worker showed both.
  I did not find out why; the practical consequence is not to conclude from the shortcut.
- Pre-computing the old-vs-new mapper diff on real events before touching OpenCTI caught nothing wrong but gave a cheap regression proof (same ids).

## Rules extracted

- New `confirm-through-the-production-path-before-concluding` (external-integrations).
- Reinforced: `inspect-real-output-before-specifying-a-mapping` (evidence 3), `replay-recorded-events-when-upstream-is-nondeterministic` (evidence 2).

## Follow-ups (not blocking)

- If `CLOUD_STORAGE_BUCKET_OPEN` or code-leak findings are ever wanted, they need their own spec (false-positive policy first).
- Verify the "flagged hostname not imported" Note line live when a scan produces that case.
