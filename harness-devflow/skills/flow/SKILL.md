---
name: flow
description: "Choose and run a task-sized development workflow with configurable delivery endpoints, durable evidence and optional design approval."
---

# Harness development workflow

Use this workflow when the user asks to orchestrate a feature through design, implementation, verification and delivery. A standalone explanation or an ordinary small edit does not by itself start a workflow.

Read [the runtime contract](references/runtime.md) before operating state. The plugin root is two directories above this skill's directory; resolve its absolute path from the skill location. The consumer repository is the user's target checkout, never the installed plugin directory.

## Entry and configuration

1. Read the consumer's applicable AGENTS.md and project instructions. Determine the actual host and available tools; keep the current model and permissions.
2. Identify the goal, target repository and stable task ID. Local text or Markdown is sufficient. Determine the relevant domain (`backend`, `frontend`, `mixed`, or `generic`) from the task and code; state the choice with the profile. Do not require a tracker, documentation/testing platform or a personal skill installation.
3. Select scope from the actual request. Use `light` for a focused fix or small reversible change, `standard` for a feature needing design and scenario review, and `release` for a change needing formal design review and deployment. State your choice briefly; do not ask the user to choose routine configuration. Preserve explicit project/user requirements. See [profiles and endpoints](references/profiles.md).
4. Select the delivery endpoint independently: `local`, `pr`, `merged`, or `deployed`. Default to local unless the task calls for a remote deliverable. A request to implement does not imply creating a PR or deploying. Enable interfaces, additional testing or knowledge only when applicable. Use `--enable design_approval` when a concrete unresolved architecture/risk decision or explicit project policy warrants it; routine designs do not need an extra approval step.
5. The plugin bundles `brownfield-recon` and `server-tech-design`. Read [capability handoff](../../references/capabilities.md) when selecting a method. Auto uses recon only when needed and server design/review for backend tasks. `--capability SLOT=PROVIDER` selects a required method; `builtin` selects the generic fallback. Do not load another same-named skill from a personal directory. Custom methods belong in the consumer's `.harness/skills/<name>/`.
6. Run `doctor` with the same profile, endpoint, domain and overrides intended for start. If configuration is absent, `init --base <verified-base-ref>` creates `.harness/project.json`. Set real checks and selected adapters; inspect existing scripts rather than inventing a passing command. Commit configuration as part of authorized setup. A Git repository, initial commit and clean named branch are required.
7. Use a dedicated local feature branch unless the user explicitly requests the base branch. Run `start --goal <goal> --profile <profile> --target <endpoint> --domain <domain>` with applicable overrides. Read `active_stages`; only those stages run. `start` and `resume` return state; the agent performs the work.

## Routing

Read only the skill for the current stage, plus its linked contract. Invoke names as `harness-devflow:<skill>` when the host supports plugin skill discovery; otherwise read the same SKILL.md and execute inline.

| State stage | Skill |
| --- | --- |
| intake | intake |
| design | design |
| design_audit | design-audit |
| test_design | test-design |
| design_approval | flow (approval procedure below) |
| interfaces | interfaces |
| plan | plan |
| implement | implement |
| review | review |
| push, pr | delivery |
| integration | integration-test |
| monitor | monitor |
| release, deploy | release |
| knowledge | knowledge |

After each skill, reread `status` and continue while the current action is authorized and unblocked. Do not report an internal routing message as a completed user task. At a human gate, show the concrete artifacts and request the needed decision, respecting prior session authorization. At a failed command, diagnose the actual logs before retrying. Never edit stage statuses or synthesize receipts.

## Selected design approval

Only when `design_approval` is selected, enter it and assemble a local packet linking requirements, designs and any selected audit/scenario artifacts. Show material decisions, interface changes and remaining risks. Run `request-approval design_approval --report ...` for this concrete packet. Record an actual applicable user decision with `approve design_approval --actor ... --note ...`; generic permission to implement is not approval of an unseen design. Revisions reopen the earliest affected stage. Local Markdown is sufficient; publishing elsewhere requires the user's authorization for that destination.

## Recovery and control

- `status`: show stage, missing evidence, pending decisions and module progress.
- `resume`: inspect state and continue its current skill. A `waiting_human` state needs the user's decision; elapsed time is not approval.
- `reopen <stage> --reason ...`: preserve history and invalidate that stage and everything downstream. Changed design goes back to design; code repairs after review go back to review.
- `configure-flow ... --reason ...`: change the task's profile, endpoint, isolation or selected stages; inspect the resulting route and affected evidence. Extend a completed local task to PR/merged/deployed only when the user requests that next deliverable. Do not change scope merely to evade a failed check.
- `sync-config --reason ...`: accept an intentional project configuration change. Command/policy changes invalidate affected work; operational limits alone do not reopen design approval. A new code/config commit still requires fresh code verification.
- `abort --reason ...`: stop this run. Explicitly cancel any real scheduler whose handle was recorded. Preserve branches, worktrees, drafts and logs.
- `export --output <new-path>`: write a portable Markdown progress/evidence report.

Unselected stages are automatically excluded with a recorded policy reason. Selected interfaces, integration and knowledge can be skipped with a specific applicability reason. Missing credentials or failed checks are not proof of inapplicability. Delivery stages required by the chosen endpoint cannot be skipped. Finish when that endpoint and any selected knowledge capture are complete: a PR endpoint does not wait for merge, and local/PR/merged endpoints do not request release approval.
