# Runtime contract

Resolve `<plugin-root>` from the loaded skill directory, not a shell startup file.
All commands below are suffixes of:

```bash
python3 "<plugin-root>/scripts/harness.py" --repo "<owning-repository>" --task "<task-id>" COMMAND
```

`--repo` and `--task` are global flags and precede the command. Use absolute paths when
issuing real calls. The CLI is orchestration infrastructure; it does not invoke a model.
An agent reads the current skill, performs the work and submits its evidence.

## State and paths

```text
consumer/
  .harness/
    project.json                 # Version-controlled project policy and commands
    .gitignore                   # Ignores local runtime data below
    skills/<name>/               # Optional project-owned professional providers
    runs/<task>/
      state.json                 # Single authoritative state, receipts and event history
      artifacts/                 # Human-readable documents and JSON stage reports
      capabilities/<id>/         # Request and pinned professional skill/resources
      commands/<run-id>/          # Actual request, stdout and stderr
    worktrees/<task>/<epoch>/<module>/
    knowledge/<task>/<snapshot>/  # Local snapshots with approval provenance
```

Never edit stage statuses, approval data or command receipts directly. State writes use
an OS lock and atomic replacement. A task belongs to its named branch and owning checkout.
Worktree workers always use that owning checkout for workflow commands; `run-check --module`
selects their working directory. The runtime never switches the user's primary branch.

Completion states are `done` or `skipped` (applicability or task-policy exclusion). Other states are
`pending`, `running`, `waiting_human`, `failed`; a run can also be aborted. `status` reports
stale evidence separately. Every report/artifact path must stay inside the consumer repository,
including after symlink resolution. Use a new report file for each attempt; do not overwrite
evidence consumed by completed stages.

## Selected stages

```text
intake -> design -> design_audit -> test_design -> design_approval
       -> interfaces -> plan -> implement -> review -> integration -> push
       -> pr -> monitor -> release -> deploy -> knowledge
```

This is the catalog order, not a mandatory route. Read [profiles and endpoints](profiles.md)
and the task's `active_stages`/`workflow` in status. Integration can instead follow push.

- Core stages: intake, plan, implement, review. Profile-selected design stages and optional
  interfaces/integration precede delivery. Knowledge is optional after the endpoint.
- Design approval is a gate only when selected. Release runs only for a deployed endpoint.
  Knowledge defaults to automatic local archival; explicit approval applies only to notes,
  never to `no_changes`.
- Selected interfaces, integration and knowledge may be skipped for a concrete applicability
  reason. Other selection uses `configure-flow`; the endpoint's required delivery stages
  cannot be skipped. Missing required infrastructure is not an applicability reason.
- Default max attempts: 3; parallel module commands: 4; command timeout: 300 seconds.
- A committed, clean checkout is required for review/delivery/verification evidence.
- Review/push/integration/PR/monitor/release/deploy/knowledge evidence binds to the actual
  code fingerprint. Changing HEAD or working bytes invalidates it. Review's default two-hour
  age limit applies at push; an unchanged PR can wait for human review longer than two hours.

## Stage commands

```text
enter STAGE
complete STAGE --report <file>
request-approval GATE --report <file>
approve GATE --actor <actual-user> --note <actual-decision>
skip STAGE --reason <specific-applicability-decision>
fail STAGE --reason <observed-failure>
reopen STAGE --reason <why-the-existing-evidence-is-invalid>
```

First enter a stage, do the work, then submit a report. `plan --tasks <file>` enters/completes
planning using a concrete module-to-tasks JSON map and the intake graph. It creates no worktrees.
Human approval is recorded only after a concrete packet exists and the user has accepted it.
An `actor`/`authorization` string is an audit annotation, not a cryptographic identity or an
authorization service. Host/user permissions remain authoritative. These local files and
hooks protect against workflow mistakes; they are not a tamper-proof CI security boundary.

Reopening archives previous state and resets all downstream stages. It does not revert
code, remote actions, branches or worktrees. Reconcile those effects before retrying. A
configuration change requires `sync-config --reason ...`. Changed commands and selected stages
invalidate affected work. Operational limits do not force design reapproval; any new code/config
commit still invalidates code verification. Per-task profile/endpoint changes use
`configure-flow ... --reason ...`, preserving history and resetting the affected suffix.
An aborted task stays aborted; a new task ID starts new work.

## Common report shape

Write real findings and artifacts first; examples describe schemas, not evidence to reuse.

```json
{
  "schema_version": 1,
  "stage": "design_audit",
  "status": "pass",
  "summary": "Describe what was actually reviewed or verified",
  "artifacts": [".harness/runs/example/artifacts/design-audit.md"],
  "findings": [],
  "details": {}
}
```

Artifacts must be nonempty files; the report and every artifact are content-hashed.
Findings use `severity: blocker | warning | suggestion` and a nonempty `message`.
Include evidence anchors and corrections in findings/documents. Only a truly resolved blocker
may have `resolved: true`. Design-audit and review reports require an explicit findings array.

Stage-specific additions:

| Stage | Required fields beyond common shape |
| --- | --- |
| intake | `details.acceptance`: criterion IDs; `details.modules`: `{id, depends_on, acceptance}` covering all criteria; `details.approach` when design is off and `details.verification` when test design is off |
| design | `details.designs`: map every module ID to a path also listed in `artifacts` |
| test_design | `details.scenarios`: `{id, acceptance}` objects covering all intake criteria; expected behavior belongs in the artifact |
| plan | `details.waves` and `details.tasks`: validated task/acceptance map, generated by `plan --tasks <file>` |
| implement | All runtime module records must already be verified and merged |
| review, integration | `checks`: successful IDs returned by this stage's `run-check` calls, covering configured checks |
| interfaces, push, pr, monitor, deploy | `adapter_run`: successful ID returned by the matching adapter; monitor also requires observed state `merged` |
| release | `details.checklist` with `verification`, `rollback`, `observability`, `risks`; each has `status: pass | not_applicable` and a nonempty `evidence` explanation |
| knowledge | `details.outcome: draft | no_changes`; actual notes/rationale are included as artifacts |

Intake example:

```json
{
  "acceptance": ["AC-1", "AC-2"],
  "modules": [
    {"id": "storage", "depends_on": [], "acceptance": ["AC-1"]},
    {"id": "api", "depends_on": ["storage"], "acceptance": ["AC-2"]}
  ]
}
```

Unknown dependencies, self-dependencies, duplicate IDs and cycles are errors, never silently removed.

## Command receipts

```text
run-check unit
run-check unit --module storage
run-adapter push --authorization <existing-user-authorization>
```

Checks execute actual configured argument vectors without a shell; the agent cannot provide an
exit code. Receipts bind task, stage epoch, command-configuration hash, code fingerprint, command, logs and
exit status. Checks that modify tested bytes fail freshness verification. Commands can use
`{plugin_root}`, `{repo}`, `{artifact_dir}` and `{task}` placeholders in individual arguments;
substitution creates arguments, never shell code. Adapter details: [adapter contract](../../../references/adapters.md).

Failed commands return CLI code 1; invalid state/contracts return 2; successful operations
return 0. Adapter observations may be `pending` with CLI code 0 and still cannot complete a
stage. A missing executable or malformed response is a failure. Per-command retries are
bounded; pending monitor observations do not consume a failure retry budget.

After interruption, inspect the saved logs, process IDs and real external state. If both owner
and child processes have exited, `abandon-run <id> --reason ...` releases the interrupted receipt.
Do not repeat an uncertain external mutation before the adapter has reconciled it. Adapter
requests carry a stable idempotency key for the same task/stage epoch/config/code input.

## Professional capabilities

After entering the matching stage, prepare a method and read its returned request and pinned
Skill. The agent performs the investigation/design/review, then submits a result envelope:

```text
prepare-capability recon --reason 'Establish the existing contract'
collect-recon --scope src --keyword compatibility
complete-capability recon --report <capability-result.json>
```

Slots are `recon`, `design`, `design_audit` and `review`. `collect-recon` is optional and uses
the actual bundled collector through the command runner; its receipt has kind `capability`
and binds the invocation and source digest. Preparation and collection alone never advance a
stage. Professional results must complete before the parent stage can pass; builtin choices
use the ordinary stage report without an extra result envelope. Selected source snapshots,
requests, results and artifacts join the stage evidence. Provider changes/reopens retain the
old invocation history. `status`, `doctor` and `export` expose selections/provenance.

See the [full handoff contract](../../../references/capabilities.md) for result schemas,
readiness, findings propagation, source resolution and recovery.

## Module execution

Before implementation, create the plan's task input (one entry for every module):

```json
{
  "storage": [
    {"id": "persist", "summary": "Persist accepted records atomically", "acceptance": ["AC-1"],
     "verification": "Run persistence tests, including interrupted writes"}
  ]
}
```

`plan --tasks <file>` validates unique task IDs and exact module acceptance coverage. Summaries
and verification methods are required. The durable plan contains tasks and dependency waves.
Runtime `execution_mode` resolves auto to checkout for one module and worktree for multiple.

```text
prepare-module storage
run-check unit --module storage
complete-module storage --report <module-completion-file>
merge-wave
```

`prepare-module` returns `worktree`, `branch` and `base`. In checkout mode `worktree` is the
owning repository and module completion integrates it without a merge command. The report is distinct from
a stage report:

```json
{
  "schema_version": 1,
  "module": "storage",
  "status": "pass",
  "summary": "Describe the implemented behavior and verification",
  "completed_tasks": ["persist"],
  "acceptance": ["AC-1"],
  "artifacts": [".harness/runs/example/artifacts/storage-plan-and-results.md"],
  "checks": ["an-actual-returned-receipt-id"]
}
```

Each module needs an implementation commit, a clean checkout/worktree and successful configured
review checks. Completed task IDs must match its plan. In worktree mode, merge only after all
wave members verify. An interrupted/conflicting merge preserves progress;
resolve and commit in the owning branch, then rerun `merge-wave`. The next wave contains the
previous wave's code. Parallel execution is optional and subject to actual host capability and
authorization; sequential operation supports the whole workflow.

## Push gate and host behavior

`gate` verifies current reviewed code before a push. `install-git-hook` explicitly installs
a repository-local pre-push hook; it refuses existing hooks and `core.hooksPath` configurations.
Compose `check-push` into an existing hook manager manually when needed. The hook supports
current-branch pushes; tags need a separate release policy. Deleting a ref adds no new code.
Hooks are optional defense in depth: no global hooks/settings are modified, and CI/branch
protection must independently enforce organizational policy.

Codex uses `$harness-devflow:flow`; Claude Code uses `/harness-devflow:flow`. Hosts without
skill loading can read the Markdown directly and invoke the same CLI. Scheduler/subagent APIs
are discovered at runtime; the plugin does not invent handles, create a background process
without authorization, change models or require disabled sandboxing.
