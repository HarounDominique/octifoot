# SPEC: value-assessment

Status: approved
Extends: [SPEC-event-catalogue.md](SPEC-event-catalogue.md)

## Objective

State, with evidence, whether octifoot is at least as valuable as SpiderFoot and OpenCTI used separately, and where it is not. The owner's goal was parity; the document must say whether it holds, for which scope, and how each claim was verified.

Success:
- A side-by-side table for the questions an analyst asks, with an explicit "No" where octifoot is weaker (API keys, active modules, scheduling).
- Measured figures only, computed from the repository (catalogue counts, lean list size, test count, A/B speed-ups).
- A section on weaknesses citing the real defects found and the failure modes seen, and the split between live-verified and unit-tested-only behaviour.
- A plain verdict that does not claim parity outside the scope where it holds.

Out of scope: marketing language; estimates of value on data the platform does not hold.

## Boundaries

**Always**: cite what was measured; separate live from synthetic evidence.
**Never**: claim parity for keyed sources, active modules or monitoring that does not exist.
