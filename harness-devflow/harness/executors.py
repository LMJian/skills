"""Replaceable command execution; all backends return the same observable result."""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess

from .model import HarnessError, require
from .storage import atomic_json


def terminate(process: subprocess.Popen) -> None:
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    else:
        process.kill()
    process.wait()


def local(argv, cwd, environment, timeout, stdout, stderr, on_spawn):
    process = None
    try:
        with stdout.open("wb") as out, stderr.open("wb") as err:
            process = subprocess.Popen(argv, cwd=cwd, env=environment, stdout=out, stderr=err,
                                       stdin=subprocess.DEVNULL, start_new_session=(os.name == "posix"))
            on_spawn(process.pid)
            try:
                return {"exit_code": process.wait(timeout=timeout), "timed_out": False, "outcome": "completed"}
            except subprocess.TimeoutExpired:
                terminate(process)
                return {"exit_code": process.returncode, "timed_out": True, "outcome": "unknown"}
    finally:
        if process is not None and process.poll() is None:
            terminate(process)


def execute(*, provider, host, run_id, argv, cwd, environment, timeout, directory, on_spawn, expand):
    stdout, stderr = directory / "stdout.log", directory / "stderr.log"
    if provider == "builtin":
        return local(argv, cwd, environment, timeout, stdout, stderr, on_spawn)
    # A native bridge is trusted executable integration code, never an agent-authored receipt.
    # Its stdout is transport JSON; command stdout/stderr remain separate evidence files.
    bridge = host["command"]["bridge"]
    request = {"schema_version": 1, "request_id": run_id, "operation": "command",
               "argv": argv, "cwd": str(cwd), "timeout_seconds": timeout,
               "environment": {k: v for k, v in environment.items() if k.startswith("HARNESS_")}}
    atomic_json(directory / "host-request.json", request)
    env = {**environment, "HARNESS_HOST_REQUEST": str(directory / "host-request.json")}
    transport = local(expand(bridge["argv"]), cwd, env,
                      bridge.get("timeout_seconds", timeout + 30),
                      directory / "host-stdout.json", directory / "host-stderr.log", on_spawn)
    require(transport["exit_code"] == 0 and not transport["timed_out"],
            "Host bridge outcome unknown; reconcile before retrying")
    response_file = directory / "host-stdout.json"
    require(response_file.stat().st_size <= 1024 * 1024, "Host bridge response exceeds 1 MiB")
    response = json.loads(response_file.read_text())
    require(isinstance(response, dict) and response.get("schema_version") == 1 and
            response.get("request_id") == run_id, "Host response does not match the command request")
    require(response.get("outcome") in {"completed", "denied", "unknown"}, "Invalid host command outcome")
    if response["outcome"] != "completed":
        raise HarnessError(f"Host command {response['outcome']}; inspect the host before retrying")
    require(type(response.get("exit_code")) is int and type(response.get("timed_out")) is bool,
            "Host response requires a real exit_code and timed_out flag")
    require(isinstance(response.get("stdout"), str) and isinstance(response.get("stderr"), str),
            "Host response requires command stdout and stderr")
    stdout.write_text(response["stdout"], encoding="utf-8")
    stderr.write_text(response["stderr"], encoding="utf-8")
    return {key: response[key] for key in ("exit_code", "timed_out", "outcome")}
