---
name: plan
description: "Create concrete implementation tasks, map them to acceptance and verification, and order modules by dependencies."
---

# Implementation planning

Read [the runtime contract](../flow/references/runtime.md). Run `next` for the selected `plan` stage after the selected upstream stages. Read intake and any selected design/test/interface artifacts.

Write a JSON mapping of each module ID to tasks with `id`, `summary`, `acceptance` and `verification`. Make tasks actionable and proportionate: a small fix can have one task; a large module needs enough decomposition to track behavior, compatibility and testing. Every module acceptance criterion must be covered. Use actual test commands or observable checks in verification, not generic completion claims.

Run `plan --tasks <file>`. The runtime validates task coverage, generates a durable plan artifact and computes dependency waves. Auto isolation chooses the owning checkout for one module and worktrees for multiple modules; explicit worktree isolation remains available. Inspect the returned plan and explain meaningful ordering.

This stage creates no worktrees. Do not flatten dependencies to increase parallelism. Semantic module changes reopen intake; task changes reopen plan. Only selected approval gates need decisions.

The `plan` command submits its generated result; continue with `next`. In guided mode, each task should have a small observable outcome and an executable check, since implementation records an ordered checkpoint for every task.
