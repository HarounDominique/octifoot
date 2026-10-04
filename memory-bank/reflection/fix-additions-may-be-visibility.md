# Reflection: fix-additions-may-be-visibility

Date: 2026-10-04 · Spec: SPEC-scan-changes.md (amended) · Plan: 2 phases DONE · Live check: replay of two recorded scans; the defect itself was found with two real consecutive scans

## What the real scans showed

Two consecutive enrichments of bugoverflow.com differed in 33 objects, and the changes Note reported them as new. Nothing had changed on the domain: crt.sh answered one time and not the other. This is the product's own central limit (a pipeline of
flaky third-party sources) showing up in the feature built to describe change.

## Implementation vs spec

| Requirement | Result |
|---|---|
| Additions after a scan whose subdomain sources failed are marked as possibly newly visible | Met (tests; live replay) |
| Certificates appearing where there were none are marked as possibly crt.sh answering | Met |
| Older snapshots stay readable | Met (field defaults to false; tested) |

Deviations: the spec was amended after the fact (a visible note in the spec).

## Workflow evaluation

- This was found by running the system twice for real, not by any test: unit tests of the diff logic were all correct for the cases I had imagined. The case I had not imagined was a "complete" scan that is silently missing a source.
- Honest limit that remains: crt.sh cannot report outages, so a caveat is only attached when the previous scan recorded source errors (always true today because Sublist3r and Crobat fail) or had no certificates. A first scan with a silent crt.sh outage and a second with a different silent gap would still be reported without a caveat.
- Ground truth was available only indirectly (the domain really did not change within minutes), which is itself the evidence.

## Rules extracted

- New `a-diff-of-runs-of-an-unreliable-pipeline-reports-its-flakiness-as-change` (external-integrations).
- Reinforced: `validate-absence-claims-against-ground-truth` (evidence 2): the same inference error in the other direction (presence).

## Follow-ups (not blocking)

- A direct probe of crt.sh (an outbound request, "ask first") would turn the heuristic caveat into a fact.
