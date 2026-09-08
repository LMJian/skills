"""Optional Git gate. Installation is explicit and never replaces an existing hook."""
from __future__ import annotations

from pathlib import Path
import shlex
import sys
from datetime import datetime, timezone

from . import git as vcs
from .engine import Workflow
from .model import require
from .storage import inside, read_json


def gate(workflow: Workflow) -> dict:
    state = workflow.load()
    workflow.consistent(state)
    require(state["stages"]["review"]["status"] == "done", "A completed review is required before push")
    elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(state["stages"]["review"]["ended_at"])).total_seconds()
    require(elapsed <= state["config"]["review_max_age_seconds"], "Review expired; rerun review before pushing")
    require(vcs.clean(workflow.root), "Working tree changed after review")
    require(state["stages"]["review"]["head"] == vcs.head(workflow.root), "Review does not match HEAD")
    return {"status": "pass", "task": workflow.task, "head": vcs.head(workflow.root)}


def check_push(root: Path, lines: str) -> dict:
    branch = vcs.branch(root)
    sha = vcs.head(root)
    candidates = []
    for path in inside(root, ".harness/runs").glob("*/state.json"):
        state = read_json(inside(root, path))
        if state.get("branch") == branch and not state.get("aborted"):
            candidates.append(state)
    for line in lines.splitlines():
        fields = line.split()
        require(len(fields) == 4, "Malformed Git pre-push input")
        local_ref, local_sha, remote_ref, _ = fields
        if set(local_sha) == {"0"}:
            continue  # Deletion has no new code to verify.
        require(remote_ref.startswith("refs/heads/"), "This gate supports branch pushes only; release tags need a separate policy")
        require(local_ref == f"refs/heads/{branch}" and local_sha == sha,
                "Push the reviewed current branch at HEAD; switch checkout to review another ref")
        matching = [s for s in candidates if s["stages"]["review"].get("head") == sha and
                    s["stages"]["review"]["status"] == "done"]
        require(matching, f"No review for pushed branch {branch} at {sha}")
        selected = max(matching, key=lambda s: s["updated_at"])
        gate(Workflow(root, selected["task"]))
    return {"status": "pass"}


def install(root: Path, plugin_root: Path) -> dict:
    require(not vcs.git(root, "config", "--get", "core.hooksPath", check=False).strip(),
            "core.hooksPath is configured; compose check-push into your existing hook manager")
    path = Path(vcs.git(root, "rev-parse", "--git-path", "hooks/pre-push"))
    if not path.is_absolute():
        path = root / path
    path.parent.mkdir(parents=True, exist_ok=True)
    command = " ".join(shlex.quote(s) for s in
                       (sys.executable, str(plugin_root / "scripts/harness.py"), "--repo", ".", "check-push"))
    content = f"#!/bin/sh\n# harness-devflow: optional local Git gate\nexec {command}\n"
    if path.exists() or path.is_symlink():
        require(not path.is_symlink() and path.read_text() == content,
                "An existing pre-push hook is present; compose check-push manually, do not overwrite it")
        return {"hook": str(path), "created": False}
    with path.open("x", encoding="utf-8") as stream:
        stream.write(content)
    path.chmod(path.stat().st_mode | 0o111)
    return {"hook": str(path), "created": True}
