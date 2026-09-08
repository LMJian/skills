---
name: review
description: "Review and verify committed changes against acceptance and selected design artifacts, with bounded fixes and durable evidence."
---

# Code review and verification

Read [the runtime contract](../flow/references/runtime.md) and [review criteria](../../references/review-criteria.md). Enter `review` on the owning branch containing all module merges.

Use [capability handoff](../../references/capabilities.md): `prepare-capability review --reason ...`. Auto uses the builtin review below; an explicit project provider supplies domain findings via `complete-capability review --report ...`. This does not replace the real check commands or the final Harness findings report. Finalize professional review only after code fixes and final checks; further code changes require reopening review and refreshing its evidence.

Read intake acceptance, planned verification and any selected design/scenario artifacts; review the diff from the recorded base SHA to HEAD. Light tasks use their compact approach and verification, without requiring missing design documents. Assess changed behavior and its necessary context; avoid unrelated historical cleanup. Cover correctness, security, concurrency, compatibility and operational risks as applicable. Record material coverage gaps honestly.

Run each configured review check using `run-check <name>`. Inspect failed logs. Make bounded fixes within the user's scope, commit, rerun checks, and reassess affected findings. Any new commit invalidates previous receipts. Do not fabricate an empty findings array when review was not performed.

Write the report with an explicit findings array, code/evidence anchors and all required check receipt IDs. Complete `review` only with no unresolved blockers and fresh successful checks. A check's exit code establishes command success; assess whether its assertions actually cover the intended behavior.

If verification cannot converge within the retry budget, fail the stage with the observed cause and required decision. Do not increase limits or replace tests with no-ops to pass the gate.
