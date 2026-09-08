---
name: delivery
description: "Push reviewed changes or create a review request through explicit provider adapters, including a local-only delivery path."
---

# Code delivery

Read [the runtime contract](../flow/references/runtime.md) and [adapter contract](../../references/adapters.md). Operate only the current `push` or `pr` stage.

These stages are selected by the task's PR/merged/deployed endpoint; a local endpoint excludes them automatically. Prepare the concrete destination and content before an action that still needs authorization. Reuse existing authorization; configuration alone does not authorize external mutation. If the user changes the endpoint, use `configure-flow --target ... --reason ...`; selected delivery stages cannot be silently skipped.

At `push`, enter the stage, run `gate`, and run the configured push adapter. The built-in Git adapter requires an explicit remote and never force-pushes. Report the actual remote and reviewed commit.

At `pr`, prepare a reviewer-facing title and body describing the problem, final behavior and validation. Use files for multiline content. Run the configured PR/MR adapter and require a real identifier/URL. Adapters must reconcile existing requests before retrying uncertain creation; do not create duplicate PRs after a timeout.

The report includes `adapter_run` and local delivery artifacts. Complete the current stage and return to the router. A PR endpoint finishes after PR creation plus any selected knowledge capture; it does not wait for merge or release approval. Creating a PR does not imply permission to merge it, publish comments, deploy production or send messages.
