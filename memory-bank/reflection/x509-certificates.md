# Reflection: x509-certificates

Date: 2026-10-04 · Spec: SPEC-x509-certificates.md (approved) · Plan: 2 phases DONE · Live check: recorded real scan replayed through the connector path, read back from OpenCTI

## Implementation vs spec

| Spec requirement | Result |
|---|---|
| Certificate with CN = target / wildcard / under it / parent becomes `x509-certificate` with fields and `related-to` | Met; real certificate round-tripped through OpenCTI |
| Other CNs not imported and counted as "not the target's" | Met (unit tests); not seen live |
| Names inside certificates never become domains | Met (test) |
| At most 10, most recent first, rest counted, Note line | Met (unit tests); the cap was never exercised on real data |
| Invalid / duplicate serial handling; ids of other objects unchanged | Met |

Deviations: live check was a replay (crt.sh still down); a parser bug and an import error fixed during the build.

## What the data allowed and did not

- Exactly one real certificate exists across 21 scans, and SpiderFoot truncated its text at 1024 characters before the SAN list. The slice is therefore built for what one real
  sample and the spec's rules can support: attribution by subject CN, no names from inside certificates, a cap, and a Note that states what was left out.
- This is the weakest-evidenced slice so far: the code path for several certificates, the cap and foreign certificates is proven only on synthetic input shaped like the real one.
  Its value depends on crt.sh answering, which it has not for hours.

## Workflow evaluation

- Copying the real text shape into the test fixture (including `Not After :`) is what exposed the parser bug immediately; a hand-made, tidier fixture would have passed and shipped a
  parser that drops the expiry date on real certificates.
- Replaying recorded real events through the production path again gave a real round trip when a fresh scan was impossible, with the limitation written down.
- A diagnostic print lost its output because of `os._exit` on a piped stdout; verifying the result from the target system rather than from the script's own output avoided a false conclusion.

## Rules extracted

- Reinforced: `mapper-fixtures-from-real-payloads` (evidence 2) and `replay-recorded-events-when-upstream-is-nondeterministic` (evidence 3).

## Follow-ups (not blocking)

- A fresh scan with crt.sh working, to see several certificates and the cap on real data.
- SANs would be available only if the 1024-character truncation could be avoided; that is SpiderFoot's export, not ours.
