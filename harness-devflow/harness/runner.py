"""Execute configured commands and record real, code-bound receipts."""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import time
import uuid

from . import git as vcs
from .engine import Workflow, current
from .model import HarnessError, digest, nonempty, now, require
from .storage import atomic_json, file_lock, inside


MAX_RESPONSE_BYTES = 1024 * 1024


def terminate(process: subprocess.Popen) -> None:
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    else:
        process.kill()
    process.wait()


def validate_response(response: object, stage: str) -> dict:
    require(isinstance(response, dict) and response.get("schema_version") == 1,
            "Adapter stdout must be one JSON object with schema_version=1")
    require(response.get("status") in {"pass", "pending", "fail"}, "Invalid adapter status")
    nonempty(response.get("summary"), "adapter.summary")
    if response["status"] == "pass":
        if stage == "pr":
            nonempty(response.get("url"), "adapter.url")
            nonempty(response.get("external_id"), "adapter.external_id")
        if stage == "monitor":
            require(response.get("state") in {"open", "merged", "closed"}, "Invalid PR state")
        if stage == "deploy":
            nonempty(response.get("deployment_id"), "adapter.deployment_id")
    return response


def run(workflow: Workflow, kind: str, name: str, *, authorization: str | None = None,
        module: str | None = None, scopes: list[str] | None = None, keywords: list[str] | None = None) -> dict:
    require(kind in {"check", "adapter", "capability"}, "Unknown command kind")
    with file_lock(workflow.lock_path):
        state = workflow.load()
        workflow.consistent(state)
        stage = current(state)
        require(stage and state["stages"][stage]["status"] == "running", "Enter a stage before running commands")
        capability_use = None
        if kind == "capability":
            require(name == "recon" and module is None, "Only the recon collector is a capability tool")
            from .capabilities import collector_spec
            spec, capability_use = collector_spec(workflow, state, scopes or [], keywords or [])
        else:
            config_key = "checks" if kind == "check" else "adapters"
            require(name in state["config"][config_key], f"No configured {kind}: {name}")
            spec = state["config"][config_key][name]
        if kind == "adapter":
            require(name == stage and module is None, "Adapters run only in their matching stage")
            if stage == "push":
                from .gates import gate
                gate(workflow)
            if spec["effect"] == "external":
                nonempty(authorization, "authorization (quote the user's existing authorization)")
            if stage == "deploy":
                require(state["stages"]["release"]["status"] == "done", "Release approval is required")
        elif kind == "check":
            require(stage in {"implement", "review", "integration"}, "Checks cannot run in this stage")
            if stage != "implement":
                require(module is None and name in state["config"]["stage_checks"].get(stage, []),
                        "Check is not assigned to this stage")
        cwd = workflow.root
        if module is not None:
            require(stage == "implement" and module in state["modules"], "Unknown implementation module")
            item = state["modules"][module]
            require(item["status"] == "running" and item.get("worktree"), "Prepare the module first")
            cwd = inside(workflow.root, item["worktree"])
            require(vcs.branch(cwd) == item["branch"], "Module worktree branch changed")
        elif stage == "implement":
            raise HarnessError("Implementation checks need --module to bind them to the prepared checkout/worktree")
        running = [r for r in state["runs"] if r["status"] == "running" and
                   (r.get("module") == module or kind == "adapter")]
        require(not running, "A command is already in flight; inspect/recover it instead of duplicating effects")
        if module is not None:
            require(sum(r["status"] == "running" and r.get("module") is not None
                        for r in state["runs"]) < state["config"]["parallel_max"],
                    "Module command concurrency limit reached; wait for a running check")
        epoch = state["stages"][stage]["epoch"]
        failures = [r for r in state["runs"] if r["name"] == name and r["kind"] == kind and
                    r.get("module") == module and r["epoch"] == epoch and r["status"] == "failed"]
        require(len(failures) < state["config"]["max_attempts"],
                "Command retry budget exhausted; inspect evidence and explicitly reopen the stage")
        run_id = uuid.uuid4().hex
        code = vcs.fingerprint(cwd)
        token = digest({"task": workflow.task, "stage": stage, "epoch": epoch,
                        "name": name, "module": module, "code": code, "config": state["execution_hash"],
                        "capability": capability_use["source_digest"] if capability_use else None,
                        "argv": spec["argv"]})
        directory = inside(workflow.root, workflow.directory / "commands" / run_id)
        directory.mkdir(parents=True)
        receipt = {"id": run_id, "kind": kind, "name": name, "stage": stage, "epoch": epoch,
                   "module": module, "status": "running", "fingerprint": code,
                   "config_hash": state["execution_hash"], "started_at": now(), "owner_pid": os.getpid(),
                   "authorization": authorization, "idempotency_key": token,
                   "argv": spec["argv"], "cwd": str(cwd),
                   "stdout": str(directory / "stdout.log"), "stderr": str(directory / "stderr.log")}
        if capability_use:
            receipt["capability_id"] = capability_use["id"]
        state["runs"].append(receipt)
        request = {"schema_version": 1, "task": workflow.task, "goal": state["goal"],
                   "stage": stage, "repository": str(workflow.root), "branch": state["branch"],
                   "head": vcs.head(cwd), "base_ref": state["base_ref"], "base_sha": state["base_sha"],
                   "artifact_directory": str(workflow.directory / "artifacts"),
                   "idempotency_key": token,
                   "prior_results": [r.get("response") for r in state["runs"]
                                     if r["kind"] == "adapter" and r["status"] == "passed"]}
        atomic_json(directory / "request.json", request)
        workflow.save(state, "command_started", run_id=run_id, stage=stage)
    # Do not hold a state lock over external I/O. Parallel module checks remain independent.
    environment = os.environ.copy()
    environment.update(HARNESS_REQUEST=str(directory / "request.json"),
                       HARNESS_TASK=workflow.task, HARNESS_STAGE=stage,
                       HARNESS_IDEMPOTENCY_KEY=token)
    result = {"exit_code": None, "timed_out": False, "response": None, "error": None}
    began = time.monotonic()
    process = None
    replacements = {"{plugin_root}": str(Path(__file__).resolve().parent.parent),
                    "{repo}": str(workflow.root), "{artifact_dir}": str(workflow.directory / "artifacts"),
                    "{task}": workflow.task}
    argv = []
    for arg in spec["argv"]:
        for token, value in replacements.items():
            arg = arg.replace(token, value)
        argv.append(arg)
    try:
        with (directory / "stdout.log").open("wb") as out, (directory / "stderr.log").open("wb") as err:
            process = subprocess.Popen(argv, cwd=cwd, env=environment, stdout=out, stderr=err,
                                       stdin=subprocess.DEVNULL, start_new_session=(os.name == "posix"))
            with file_lock(workflow.lock_path):
                latest = workflow.load()
                next(r for r in latest["runs"] if r["id"] == run_id)["child_pid"] = process.pid
                workflow.save(latest, "command_spawned", run_id=run_id)
            try:
                result["exit_code"] = process.wait(timeout=spec.get("timeout_seconds", state["config"]["check_timeout_seconds"]))
            except subprocess.TimeoutExpired:
                terminate(process)
                result.update(exit_code=process.returncode, timed_out=True, error="Command timed out")
            except BaseException:
                terminate(process)
                raise
        if result["exit_code"] != 0 and not result["error"]:
            result["error"] = f"Command exited with code {result['exit_code']}"
        if kind == "adapter" and result["exit_code"] == 0:
            require((directory / "stdout.log").stat().st_size <= MAX_RESPONSE_BYTES,
                    "Adapter response exceeds 1 MiB; put diagnostics on stderr")
            result["response"] = validate_response(json.loads((directory / "stdout.log").read_text()), stage)
            if result["response"]["status"] == "fail":
                result["error"] = result["response"]["summary"]
        if kind == "capability" and result["exit_code"] == 0:
            require((directory / "stdout.log").stat().st_size <= MAX_RESPONSE_BYTES, "Collector output exceeds 1 MiB; narrow its scope")
            result["response"] = json.loads((directory / "stdout.log").read_text())
            require(isinstance(result["response"], dict) and result["response"].get("schema_version") == "brownfield-recon-evidence-v1",
                    "Collector did not return the expected evidence schema")
    except (OSError, ValueError, HarnessError) as error:
        result["error"] = str(error)
    except KeyboardInterrupt:
        result["error"] = "Interrupted; inspect command logs and external state before retrying"
    finally:
        if process is not None and process.poll() is None:
            terminate(process)
    with file_lock(workflow.lock_path):
        latest = workflow.load(active=False, config_check=False)
        receipt = next(r for r in latest["runs"] if r["id"] == run_id)
        receipt.update(result, finished_at=now(), duration_seconds=round(time.monotonic() - began, 3))
        receipt["status"] = "failed" if result["error"] else (
            "pending" if kind == "adapter" and result["response"]["status"] == "pending" else "passed")
        # A check cannot validate bytes that it mutated. An interface adapter may deliberately
        # generate/commit code; bind its successful receipt to the resulting checkout instead.
        after = vcs.fingerprint(cwd)
        if after != code and not (kind == "adapter" and stage == "interfaces"):
            receipt.update(status="failed", error="Code changed during command execution; commit and rerun")
        receipt["fingerprint"] = after
        if latest["config_hash"] != digest(workflow.config):
            receipt.update(status="failed", error="Configuration changed during command execution")
        workflow.save(latest, "command_finished", run_id=run_id, status=receipt["status"])
        return receipt


def abandon(workflow: Workflow, run_id: str, reason: str) -> dict:
    nonempty(reason, "reason (include external reconciliation when applicable)")
    with file_lock(workflow.lock_path):
        state = workflow.load()
        receipt = next((r for r in state["runs"] if r["id"] == run_id), None)
        require(receipt and receipt["status"] == "running", "No such interrupted running command")
        for pid in (receipt.get("owner_pid"), receipt.get("child_pid")):
            if not pid:
                continue
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                continue
            except PermissionError:
                raise HarnessError("Command process may still be alive; inspect it first")
            raise HarnessError(f"Process {pid} is still alive; do not abandon live commands")
        receipt.update(status="failed", error=reason, finished_at=now())
        workflow.save(state, "command_abandoned", run_id=run_id, reason=reason)
        return receipt
