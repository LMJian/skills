# Recon Output

The output should support the next decision. Scale its form to the scope and audience; do not produce a fixed audit package for every edit.

## Default: one short baseline

Before implementation, write a compact `report.md` containing:

- Task boundary, target design/source version, deployment/compatibility requirements and pre-change commit or workspace state.
- Phase-specific readiness and a short reason.
- A change table with concrete evidence and validation behavior.
- Only the gaps that remain relevant, stating whether they block this phase or belong to later verification.

| Current behavior and evidence | Required target | Retain / replace / remove | Affected files | Validation scenario |
| --- | --- | --- | --- | --- |

Use concise prose when a table would add no clarity. Avoid empty sections, duplicate system descriptions and a separate question file when no questions exist. A collector-generated `baseline-evidence.json` is useful when discovery is broad; it is not mandatory for a few known files.

A scenario should describe observable behavior, such as “an old load finishing after removal cannot reintroduce the route,” rather than merely naming a unit test to write. A capacity assumption must be identified as an assumption.

## Expand only for a concrete need

For a formal audit, complex migration, cross-repository contract change or explicit handoff, add the sections and files needed by the reviewer:

- `report.md`: relevant flow, historical rationale, migration constraints and decisions; no fixed ten-section requirement.
- `contract-matrix.md`: useful when producer/consumer versions, owners or wire fields require separate tracking.
- `open-questions.md`: useful when unresolved decisions involve multiple owners or milestones.
- `baseline-evidence.json`: reproducible inventory if the collector was used.

A contract matrix can use:

| Contract | Inspected producer/consumer versions | Semantics and failure behavior | Evidence | Verification status | Impact on next step |
| --- | --- | --- | --- | --- | --- |

Use `verified_local_only` or `unverified_external` where appropriate; add an owner only when known. Do not invent ownership. For each important claim, cite the actual `commit:path:line` or captured working-tree evidence. A file list alone is not proof of a contract.

## Readiness and remaining questions

Name the evaluated phase: design, implementation, integration or release. Apply `READY`, `READY_WITH_GAPS` or `BLOCKED` to that phase only. List later phases as pending when they were not evaluated.

For each gap, explain the missing fact, the action it affects, why existing evidence cannot settle it, and when an answer is needed. Only call it blocking when the next action depends on the answer. Distinguish a potentially breaking unknown contract from a known contract whose live environment has not been tested.

## Keep the evidence timeline intact

Separate three kinds of statements: pre-change facts, accepted target decisions and implementation/validation results. Preserve the original baseline. Append dated discoveries or store follow-up evidence under a new filename; do not overwrite it with final-state descriptions.

After implementation, record verification in a separate section or file, including what actually ran, its result and material limits. Reading a test, passing a mock-based test and validating a production integration are different claims. Do not add passed-test labels retroactively to pre-change evidence.
