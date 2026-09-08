---
name: interfaces
description: "Apply approved public schema, API or generated-client changes through project-selected tools before implementation planning."
---

# Interface updates

Read [the runtime contract](../flow/references/runtime.md) and [the adapter contract](../../references/adapters.md). Enter `interfaces` only when selected and prior selected stages are complete. A design approval gate applies only when selected.

Read the change inventory from design or intake. With no separate contract/generation work, record a specific skip reason; ordinary API implementation can remain in implement. For required separate changes, choose the project's existing generator/toolchain: OpenAPI, Protobuf, GraphQL, SQL migrations or another actual format. Configure an `interfaces` adapter that executes the update and reports evidence. No specific language or upstream repository is assumed.

Prepare the concrete schema changes and run `run-adapter interfaces`; supply existing authorization when the adapter performs external mutations. Verify generated outputs, compatibility and downstream dependency updates. Generators may change code; commit the intended results before proceeding. Confirm upstream jobs actually succeeded when the adapter delegates asynchronous work. Record the adapter receipt and schema/dependency artifacts in the stage report.

Do not treat a missing tool, failed job or uncertain remote outcome as 'no changes'. Stop with the specific missing decision or failed evidence. Complete `interfaces` only with the validated result.
