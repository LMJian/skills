---
name: implement
description: "Execute planned tasks in the owning checkout or isolated worktrees, verify module behavior and integrate dependency waves."
---

# Module implementation

Read [the runtime contract](../flow/references/runtime.md). Enter `implement`. Read intake, concrete planned tasks and any selected designs/scenarios. Use `execution_mode` from state; a separate worktree is not required for a single module in auto/checkout mode.

For language/framework details, use a relevant project-provided Skill when available. Resolve its location from project instructions relative to the repository (for example `.harness/skills/<name>/SKILL.md`), and cite the method in the module artifact; do not require a personal installation. This is implementation guidance, not another capability slot or stage. Harness still owns task IDs, command receipts, module completion and merging.

For each module in the current wave:

1. Run `prepare-module <id>` from the owning checkout. Use the returned `worktree` path for code edits: in checkout mode this is the owning repository itself. Keep workflow calls pointed at that repository and task ID.
2. Follow the task IDs and verification plan already recorded in `plan`. Resolve setup through the project's environment. If the task plan materially changes, reopen plan rather than claiming unplanned work completed the original tasks.
3. Implement and test the behavior. Use focused tests and the language's established workflow; run failing tests first when demonstrating a bug or meaningful new behavior. Preserve unrelated changes. Commit the module changes before final verification.
4. For each required review check, run `run-check <name> --module <id>`. Commands run in the prepared checkout/worktree and record actual results. A failed or stale receipt cannot verify the module.
5. Produce a module completion report with `module`, `status`, `summary`, `completed_tasks` (all planned task IDs), `acceptance`, `artifacts` and `checks`; run `complete-module <id> --report ...`.

In checkout mode, completing the module records it as integrated; do not run `merge-wave`. In worktree mode, run `merge-wave` after every module in the wave verifies. Resolve actual merge conflicts using both intended behaviors, commit the resolved merge, and retry. Never use blanket ours/theirs resolution. The next wave branches from the updated owning branch.

Default to sequential execution. If the user or applicable instructions authorize parallel agents and the host supports them, dispatch independent modules up to configured `parallel_max`. Give each worker the plugin path, owning repository, task ID, module ID, worktree path and relevant artifacts. Wait only on successfully created workers. Worker failure does not count as completion.

Once every wave is merged, write the overall implementation report and complete `implement`. Keep worktrees for inspection; cleanup is separate and never deletes unmerged work by default.
