---
name: brownfield-recon
description: Evidence-backed investigation of existing repository behavior, historical decisions, compatibility constraints, and cross-module or cross-repository contracts before design or implementation. Use when users ask for “存量逻辑调研”, “历史逻辑扫描”, “梳理旧逻辑”, “理解陌生仓库”, “接手遗留系统”, “brownfield recon”, or when a design, migration, refactor, API change, incident fix, or dev-flow module needs a verified baseline of current and legacy behavior before work starts.
---

# Brownfield Recon

Build a reproducible baseline of existing behavior before proposing a design. Prefer evidence over inference and expose unknowns instead of silently choosing a contract.

## Boundaries

- Treat code and runtime contracts as higher authority than documentation or memory.
- Keep the investigation read-only except for two explicitly bounded writes: (a) artifacts under the selected `.artifacts/.../brownfield-recon/` directory, and (b) knowledge-use telemetry written only by the `knowledge-use` skill to its own telemetry location. No other write is permitted anywhere.
- Do not modify implementation code, formal knowledge-base pages, workflow state, remote systems, or external repositories unless separately authorized.
- Never read likely secret files such as `.env*`, credential files, private keys, or token dumps.
- Do not claim a cross-repository contract is verified when only one side is available.

## Workflow

### 1. Establish scope

Extract:

- the behavior or change under investigation;
- 2–6 exact business and code keywords, including aliases;
- the relevant entrypoint, data model, interface, error path, configuration, and persistence behavior;
- the base branch or pre-change commit when the current branch already contains changes.

Read repository instructions (`AGENTS.md`, project rules, and applicable workflow state) before scanning. Ask the user only when the missing scope would materially change the investigation.

### 2. Search existing knowledge first

If the `knowledge-use` skill is available and the repository has `.ai_knowledge/`, activate it with 2–4 high-signal keywords and the original question. Preserve result paths, confidence, staleness, and empty-recall gaps.

Knowledge is context, not proof. Cross-check important claims against code. If knowledge is absent or empty, continue with repository and Git archaeology and record the gap.

### 3. Collect the deterministic inventory

Run:

```bash
python3 <skill-dir>/scripts/collect_evidence.py \
  --repo-root <repo-root> \
  --keyword '<concept-1>' --keyword '<concept-2>' \
  --output <artifact-dir>/evidence.json
```

`<skill-dir>` is this skill's own directory (the one containing this `SKILL.md`); resolve it to an absolute path before running so the script is located reliably.

Use `.artifacts/<sanitized-branch>/brownfield-recon/` when a matching dev-flow state exists; otherwise use `.artifacts/brownfield-recon/<sanitized-branch>/`.

**Output path rule:** pass `--output` as an **absolute path** inside your own session/artifact workspace. Relative paths resolve against the current working directory (not `--repo-root`), and the collector emits a warning if the resolved output lands inside the scanned repository outside its `.artifacts/` — writing artifacts into the target repo violates the read-only guarantee.

Optional flags:

- `--base-ref <ref>` — base branch/commit for the branch diff. If the ref does not exist, the collector records a warning and falls back to `origin/master`/`main`; it never silently substitutes your requested base. Always check `warnings` and `git.base_ref` in the output.
- `--regex-keyword '<pattern>'` — regex content search (repeatable), only after you have learned local naming; prefer `--keyword` (fixed-string) first.

Read `git.diff_semantics` to know how branch-diff numbers were computed. The `candidates` map separates inbound `entrypoints` from `outbound_clients`; treat clients as downstream, not entrypoints.

The collector is a starting map, not the final analysis. Read `references/search-playbook.md` before deep tracing.

### 4. Trace each high-impact behavior end to end

For every behavior that can affect compatibility, data correctness, security, retry, routing, or capacity, locate as applicable:

1. public or inbound entrypoint;
2. core implementation and branch conditions;
3. downstream client or outbound call;
4. IDL/schema/data representation;
5. configuration, FG/TCC, defaults, and hard limits;
6. persistence and retry semantics;
7. unit, contract, smoke, or integration tests;
8. callers and adapters;
9. generated-code owner and regeneration path.

Record precise `path:line` evidence. If one layer is absent, record it as a gap rather than filling it with assumptions.

### 5. Reconstruct historical intent

Use Git archaeology selectively:

- `git log --follow -- <file>` for file evolution;
- `git log -S'<symbol-or-literal>' --all -- <scope>` for additions/removals;
- `git log -G'<regex>' --all -- <scope>` for semantic edits;
- `git blame -L <start>,<end> <file>` to identify the introducing commit;
- `git show <commit>:<path>` to compare the legacy implementation;
- `git diff <base>...HEAD` to separate pre-existing behavior from current work.

Read the surrounding code and tests; commit messages alone are not evidence of behavior.

### 6. Triangulate and assess readiness

Read `references/report-contract.md` and produce:

- `report.md` — system map, existing behavior, historical decisions, compatibility invariants, risks, and confidence;
- `contract-matrix.md` — field-level producer/consumer/owner/evidence/status matrix;
- `open-questions.md` — owner questions that cannot be answered locally;
- `evidence.json` — deterministic inventory from the collector.

Assign one readiness result:

- `READY`: every high-impact contract is verified and no blocking unknown remains.
- `READY_WITH_GAPS`: implementation can proceed within a stated boundary; gaps are non-contractual or have safe defaults.
- `BLOCKED`: ownership, field semantics, failure/retry behavior, compatibility, hard limits, or cross-repository wire contracts remain unverified.

Do not write `READY` merely because code was found. `READY` requires **all** of the following hard preconditions; if any fails, downgrade to `READY_WITH_GAPS` or `BLOCKED`:

1. Every high-impact conclusion is backed by code, IDL/schema, test, config, or Git evidence with `path:line`.
2. For each critical public interface, at least one caller **and** at least one failure path were inspected.
3. No generated file is treated as the sole contract owner.
4. Every documentation/code conflict is explicit (code wins provisionally).
5. No cross-repository wire contract is `unverified_external`.
6. `open-questions.md` contains no `P0` item.

### 7. Hand off

Summarize for the user:

- current and legacy behavior that matters;
- compatibility invariants;
- confirmed contracts and their owners;
- blocking questions;
- recommended design constraints and validation cases;
- artifact paths.

When used before dev-flow design, do not advance or approve the workflow. Hand the report to module split/design and require blocking questions to be resolved first.

## Quality gates

- Every high-impact conclusion has code, IDL/schema, test, config, or Git evidence.
- At least one caller and one failure path are inspected for each critical public interface.
- Generated files are never treated as the sole contract owner.
- Documentation/code conflicts are explicit and code wins provisionally.
- Cross-repository claims name which side was inspected and which side remains unverified.
- Sensitive paths are excluded from automated content search.
- The final report clearly separates fact, inference, and open question.
