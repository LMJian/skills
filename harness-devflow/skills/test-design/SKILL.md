---
name: test-design
description: "Turn requirements and module designs into provider-neutral test scenarios before implementation and automation."
---

# Test scenario design

Read [the runtime contract](../flow/references/runtime.md). Enter `test_design` when selected; read requirements and any selected design/audit artifacts. A missing unselected design stage is not a blocker.

Start from recon validation scenarios and the design's verification section. Reuse or reference those scenarios, assign stable IDs, and add only missing boundaries, errors and regressions. Each scenario needs preconditions, action, expected outcome and acceptance IDs. Choose unit, contract, integration or end-to-end checks according to the project, without requiring a runner/platform or recreating the same scenarios in several documents.

The report's `details.scenarios` contains unique `id` values and nonempty `acceptance` arrays. Together these must cover every acceptance criterion. The detailed scenario artifact also records data/environment needs and expected verification commands where known. Ensure planned checks assert behavior instead of mirroring implementation structure.

Complete `test_design`, then follow the next selected stage in status. Executable tests are implemented with the code and exercised during verification; this stage does not submit cases to an external service.
