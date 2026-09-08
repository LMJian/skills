"""Dependency-wave worktree execution, completion and resumable merging."""
from __future__ import annotations

from . import git as vcs
from .engine import Workflow, current
from .model import nonempty, now, require, strings
from .storage import file_lock, inside, read_json, snapshots, verify_snapshots


def executing(workflow: Workflow, state: dict) -> list[str]:
    workflow.consistent(state)
    require(current(state) == "implement" and state["stages"]["implement"]["status"] == "running",
            "Module execution is available only during implement, after the selected planning stages")
    require(state["wave_index"] < len(state["waves"]), "All waves are already merged")
    return state["waves"][state["wave_index"]]


def prepare(workflow: Workflow, module: str) -> dict:
    with file_lock(workflow.lock_path):
        state = workflow.load()
        wave = executing(workflow, state)
        require(module in wave, f"Module is not in the current wave: {wave}")
        item = state["modules"][module]
        require(item["status"] in {"pending", "running"}, "Module is already verified")
        if state["execution_mode"] == "checkout":
            if item.get("worktree"):
                require(vcs.branch(workflow.root) == item["branch"], "Owning checkout branch changed")
                return item
            require(vcs.clean(workflow.root), "Start the module from a clean owning checkout")
            item.update(status="running", branch=state["branch"], worktree=str(workflow.root),
                        execution_mode="checkout", base=vcs.head(workflow.root), started_at=now())
            workflow.save(state, "module_prepared", module=module, execution_mode="checkout")
            return item
        epoch = state["stages"]["implement"]["epoch"]
        path = inside(workflow.root, f".harness/worktrees/{workflow.task}/{epoch}/{module}")
        branch = f"harness/{workflow.task}/{epoch}/{module}"
        if item.get("worktree"):
            require(path.is_dir() and vcs.branch(path) == branch, "Worktree missing or branch changed")
            return item
        require(vcs.clean(workflow.root), "The owning branch must be clean before preparing a wave")
        base = state.setdefault("wave_bases", {}).setdefault(str(state["wave_index"]), vcs.head(workflow.root))
        require(vcs.head(workflow.root) == base, "Owning branch moved while preparing this wave")
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            # Recover a process death after git worktree add but before the state transaction.
            require(vcs.repo_root(path) == path and vcs.branch(path) == branch and
                    vcs.is_ancestor(path, base), "Existing path is not this module's worktree")
        else:
            vcs.git(workflow.root, "worktree", "add", "-b", branch, str(path), base)
        item.update(status="running", branch=branch, worktree=str(path), base=base, started_at=now())
        workflow.save(state, "module_prepared", module=module)
        return item


def complete(workflow: Workflow, module: str, source: str) -> dict:
    with file_lock(workflow.lock_path):
        state = workflow.load()
        wave = executing(workflow, state)
        require(module in wave, "Module is not in the current wave")
        item = state["modules"][module]
        require(item["status"] == "running", "Prepare the module before completing it")
        path = inside(workflow.root, item["worktree"])
        require(vcs.branch(path) == item["branch"] and vcs.clean(path), "Commit module changes on its worktree branch")
        sha = vcs.head(path)
        require(sha != item["base"] and vcs.is_ancestor(path, item["base"]), "Module needs its own implementation commit")
        report = read_json(inside(workflow.root, source))
        require(report.get("schema_version") == 1 and report.get("module") == module and
                report.get("status") == "pass", "Invalid module completion report")
        nonempty(report.get("summary"), "module.summary")
        tasks = strings(report.get("completed_tasks"), "module.completed_tasks")
        planned = workflow.report_for(state, "plan")["details"]["tasks"][module]
        require(set(tasks) == {t["id"] for t in planned}, "Completion must cover the planned task IDs")
        coverage = strings(report.get("acceptance"), "module.acceptance")
        require(set(coverage) == set(item["acceptance"]), "Module completion must cover its assigned acceptance criteria")
        artifact_names = strings(report.get("artifacts"), "module.artifacts")
        check_ids = strings(report.get("checks"), "module.checks")
        required = state["config"]["stage_checks"].get("review", [])
        require(required, "Configure review checks before implementing modules")
        found = set()
        code = vcs.fingerprint(path)
        for run_id in check_ids:
            receipt = next((r for r in state["runs"] if r["id"] == run_id), None)
            require(receipt and receipt["kind"] == "check" and receipt["module"] == module and
                    receipt["stage"] == "implement" and receipt["status"] == "passed" and
                    receipt["epoch"] == state["stages"]["implement"]["epoch"] and
                    receipt["config_hash"] == state["execution_hash"] and receipt["fingerprint"] == code,
                    f"Missing, failed or stale module check: {run_id}")
            found.add(receipt["name"])
        require(set(required) <= found, f"Missing module checks: {sorted(set(required) - found)}")
        item.update(status="verified", head=sha, fingerprint=code, completed_tasks=tasks,
                    evidence=snapshots(workflow.root, [source, *artifact_names]))
        if state["execution_mode"] == "checkout":
            item.update(status="merged", merged_at=now())
            state["wave_index"] += 1
        workflow.save(state, "module_verified", module=module)
        return item


def merge_wave(workflow: Workflow) -> dict:
    with file_lock(workflow.lock_path):
        state = workflow.load()
        wave = executing(workflow, state)
        require(all(state["modules"][mid]["status"] in {"verified", "merged"} for mid in wave),
                "Every module in the wave must be verified before merging")
        require(not any(r["status"] == "running" for r in state["runs"]), "Checks are still running")
        require(vcs.clean(workflow.root), "Resolve any merge conflicts and commit before resuming wave merge")
        for mid in wave:
            item = state["modules"][mid]
            path = inside(workflow.root, item["worktree"])
            verify_snapshots(workflow.root, item["evidence"])
            require(vcs.fingerprint(path) == item["fingerprint"], f"Module {mid} changed after verification")
            if not vcs.is_ancestor(workflow.root, item["head"]):
                try:
                    vcs.git(workflow.root, "merge", "--no-ff", "--no-edit", item["head"])
                except Exception:
                    workflow.save(state, "merge_interrupted", module=mid)
                    raise
            item.update(status="merged", merged_at=now())
            workflow.save(state, "module_merged", module=mid)
        state["wave_index"] += 1
        workflow.save(state, "wave_merged", wave_index=state["wave_index"] - 1)
        return workflow.summary(state)
