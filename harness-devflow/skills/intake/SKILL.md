---
name: intake
description: "Align a software requirement with an existing repository and produce module boundaries, acceptance criteria and a dependency graph."
---

# Requirement intake

Read [the runtime contract](../flow/references/runtime.md). Enter `intake`.

For an unclear existing behavior/contract, or an explicit recon binding, follow the [capability handoff](../../references/capabilities.md): `prepare-capability recon --reason ...`. Auto selects the bundled [brownfield-recon](../brownfield-recon/SKILL.md). Read the returned request and pinned skill, investigate, then submit `complete-capability recon --report ...`. A small known scope can reuse an existing baseline without a new investigation. An explicitly configured provider must run; do not silently use builtin instead.

Use recon findings or focused direct reads to map the change to existing components. Preserve the pre-change baseline and retain/replace/remove decisions; do not rewrite them as the completed implementation. Recon readiness must name design or implementation as appropriate. Later integration/release gaps do not automatically block local work. Clarify only material ambiguity; retain accepted constraints and authorization. Prefer one module until a useful split is justified.

Write requirements Markdown: observable behavior, scope, stable acceptance IDs, module boundaries and open decisions. Link the recon baseline instead of repeating its traces; reference its validation scenarios when defining acceptance. Supply `details.acceptance` and `details.modules`. Every criterion must be owned; unknown, duplicate and cyclic dependencies are rejected. Recon results supplement this report and never replace its acceptance/module contract.

When design is not selected, include a concrete short `details.approach`. When test design is not selected, include `details.verification` explaining how observable acceptance will be checked. The light profile carries these decisions here, without separate design documents. `checkout` isolation supports one module; multiple modules use auto/worktree isolation.

Validate the split against real contracts and implementation boundaries. Complete `intake` and follow the next selected stage from status.
