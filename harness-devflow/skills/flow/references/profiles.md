# Profiles and delivery endpoints

Profiles select development depth. Endpoints select the requested deliverable. They are
independent; neither grants permission to push, create a PR, merge, schedule or deploy.

| Profile | Development stages | Default endpoint |
| --- | --- | --- |
| light | intake → plan → implement → review | local |
| standard | intake → design → design_audit → test_design → plan → implement → review | local |
| release | standard stages plus design_approval before interfaces/plan | deployed |

Use light for focused fixes or small reversible changes. Intake still records an approach
and verification method, and plan maps concrete tasks to acceptance. Standard suits features
with meaningful contracts or cross-module behavior. Release supplies formal design approval;
project/user requirements can select it on other profiles too. Do not make every change a
release workflow merely because it edits server code.

| Endpoint | Additional stages | Completion |
| --- | --- | --- |
| local | none | Verified local implementation |
| pr | push → pr | Actual PR/MR created; no merge wait |
| merged | push → pr → monitor | Observed merged PR/MR |
| deployed | push → pr → monitor → release → deploy | Release approved and deployment verified |

The deployed route currently uses the PR/merge path. Direct deployment without a PR is not
a separate built-in endpoint. Explicitly extending a completed task with `configure-flow
--target ... --reason ...` preserves earlier valid evidence and opens the additional work.
Changing scope does not undo remote effects or cancel an external scheduler.

## Configuration

The project-level `workflow` object and per-task CLI flags use the same options:

```json
{
  "profile": "standard",
  "target": "local",
  "domain": "backend",
  "capabilities": {"recon": "auto", "design": "auto", "design_audit": "auto", "review": "builtin"},
  "isolation": "auto",
  "integration_position": "before_push",
  "knowledge_approval": false,
  "stages": {"interfaces": false, "knowledge": false}
}
```

| Option | Values and behavior |
| --- | --- |
| profile | `light`, `standard`, `release`; default standard |
| target | `local`, `pr`, `merged`, `deployed`; omitted/null uses the profile default |
| domain | `generic` (default), `backend`, `frontend`, `mixed`; backend selects bundled server design/audit methods |
| capabilities | Logical providers for `recon`, `design`, `design_audit`, `review`: `auto`, `builtin`, a bundled name or a project skill name; never an absolute path |
| isolation | `auto`: checkout for one module, worktrees for multiple; `checkout`: one module only; `worktree`: always isolated |
| integration_position | `before_push` by default; `after_push` for a pushed preview/environment, requiring a remote endpoint when integration is selected |
| knowledge_approval | false by default; true requires approval of notes, never of a `no_changes` outcome |
| stages | Boolean overrides for `design`, `design_audit`, `test_design`, `design_approval`, `interfaces`, `integration`, `knowledge` |

Interfaces and knowledge default off. Integration defaults on when the project assigns
nonempty `stage_checks.integration`. Design audit/approval require design. The four core
stages and the endpoint's delivery stages cannot be disabled. A configured adapter alone
does not select an external stage. There is no arbitrary stage reordering; integration's
two supported positions retain the verified-code dependencies.

Example command suffixes (global `--repo` and `--task` precede them):

```text
start --goal 'Fix the parser boundary condition' --profile light --target local
start --goal 'Implement export' --profile standard --target pr --enable interfaces
start --goal 'Release export' --profile release --target deployed --enable knowledge
configure-flow --enable design --enable design_audit --enable design_approval --reason 'The change now includes a migration requiring review'
configure-flow --target pr --reason 'User requested a PR for the completed local change'
```

Task flags override project defaults; explicit stage overrides remain in force when changing
profile, so enable/disable them deliberately. `configure-flow` records the rationale and
invalidates the affected suffix. Use it for actual scope changes, not to hide failing checks.
Excluded stages remain excluded on reopen. If separate design/test design is removed after
intake, intake reopens to supply the required compact approach/verification.

Capability flags use `--capability SLOT=PROVIDER`; each supplied slot overrides only that slot.
`--domain backend` selects a design method without changing the profile or endpoint. Changing
a provider, or a domain affecting design/audit, invalidates that stage and its downstream work.
No capability enables a disabled stage. See the [handoff contract](../../../references/capabilities.md)
for bundle-relative resolution, preparation and result requirements.

## v0.2 compatibility

v0.3 adds domain and capability defaults to schema-2 tasks in memory. Read-only status leaves
the file untouched; a normal mutation persists the defaults. Existing evidence and approvals
remain valid unless a relevant policy, code or artifact actually changes.

## v0.1 compatibility

Project configuration remains schema 1; older configs receive the new defaults for new tasks.
Task state is schema 2 because ordering, gates and module plans changed. v0.2 rejects v0.1
task state before writing it. Finish/export an active old task with the retained v0.1
distribution, then start a new task ID. Do not hand-convert state or fabricate task maps.
`design-approval` is no longer a separate Skill; `flow` handles that selected stage.
The plan command now requires `--tasks`; completion reports use planned task IDs. The `stages`
command returns a capability catalog, while task `status` supplies its actual selected route.
