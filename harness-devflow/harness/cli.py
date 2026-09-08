"""Machine-readable CLI for skills, humans and CI."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

from . import __version__, gates, knowledge, runner, worktrees, capabilities
from . import git as vcs
from .engine import Workflow, current, init_project, stage_order
from .model import GATES, STAGES, PROFILES, TARGETS, SELECTABLE, CAPABILITY_STAGES, DOMAINS, HarnessError, require
from .storage import file_lock, inside


PLUGIN_ROOT = Path(__file__).resolve().parent.parent


def add_workflow_flags(command):
    command.add_argument("--domain", choices=DOMAINS)
    command.add_argument("--capability", action="append", default=[], metavar="SLOT=PROVIDER")
    command.add_argument("--profile", choices=PROFILES)
    command.add_argument("--target", choices=TARGETS)
    command.add_argument("--isolation", choices=("auto", "checkout", "worktree"))
    command.add_argument("--integration-position", choices=("before_push", "after_push"))
    command.add_argument("--enable", action="append", choices=sorted(SELECTABLE), default=[])
    command.add_argument("--disable", action="append", choices=sorted(SELECTABLE), default=[])
    command.add_argument("--knowledge-approval", action=argparse.BooleanOptionalAction, default=None)


def selected_options(args):
    require(not (set(args.enable) & set(args.disable)), "A stage cannot be both enabled and disabled")
    result = {key: getattr(args, key) for key in
              ("profile", "target", "isolation", "integration_position", "knowledge_approval", "domain")
              if getattr(args, key) is not None}
    if args.enable or args.disable:
        result["stages"] = {**dict.fromkeys(args.enable, True), **dict.fromkeys(args.disable, False)}
    if args.capability:
        bindings = {}
        for value in args.capability:
            slot, separator, provider = value.partition("=")
            require(separator and slot in CAPABILITY_STAGES and provider, "Use --capability SLOT=PROVIDER")
            require(slot not in bindings, "Duplicate capability binding")
            bindings[slot] = provider
        result["capabilities"] = bindings
    return result


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Provider-neutral development harness")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--repo", type=Path, default=Path.cwd(), help="Owning consumer Git checkout")
    p.add_argument("--task", help="Stable task ID (lowercase letters, numbers, hyphens)")
    commands = p.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Create project config without installing dependencies or hooks")
    init.add_argument("--base", help="Default integration branch/ref, e.g. main")
    doctor = commands.add_parser("doctor", help="Read-only diagnostics for the selected workflow")
    add_workflow_flags(doctor)
    commands.add_parser("stages", help="Print ordered stages and approval gates")
    start = commands.add_parser("start")
    start.add_argument("--goal", required=True)
    start.add_argument("--base")
    add_workflow_flags(start)
    configure = commands.add_parser("configure-flow", help="Change task scope with recorded evidence invalidation")
    configure.add_argument("--reason", required=True)
    add_workflow_flags(configure)
    plan = commands.add_parser("plan")
    plan.add_argument("--tasks", required=True, help="JSON mapping module IDs to concrete task lists")
    prepare_cap = commands.add_parser("prepare-capability", help="Select and snapshot a skill; the agent executes its method")
    prepare_cap.add_argument("slot", choices=sorted(CAPABILITY_STAGES))
    prepare_cap.add_argument("--reason", required=True)
    complete_cap = commands.add_parser("complete-capability", help="Record the professional skill's actual artifacts")
    complete_cap.add_argument("slot", choices=sorted(CAPABILITY_STAGES))
    complete_cap.add_argument("--report", required=True)
    collect = commands.add_parser("collect-recon", help="Run the bundled read-only collector and preserve its stdout")
    collect.add_argument("--scope", action="append", default=[])
    collect.add_argument("--keyword", action="append", default=[])
    for name in ("status", "resume", "merge-wave", "gate"):
        commands.add_parser(name)
    enter = commands.add_parser("enter")
    enter.add_argument("stage", choices=STAGES)
    for name in ("complete", "request-approval"):
        cmd = commands.add_parser(name)
        cmd.add_argument("stage", choices=STAGES)
        cmd.add_argument("--report", required=True)
    approve = commands.add_parser("approve")
    approve.add_argument("stage", choices=sorted(GATES))
    approve.add_argument("--actor", required=True)
    approve.add_argument("--note", required=True)
    for name in ("skip", "fail", "reopen"):
        cmd = commands.add_parser(name)
        cmd.add_argument("stage", choices=STAGES)
        cmd.add_argument("--reason", required=True)
    for name in ("abort", "sync-config"):
        cmd = commands.add_parser(name)
        cmd.add_argument("--reason", required=True)
    for name in ("run-check", "run-adapter"):
        cmd = commands.add_parser(name)
        cmd.add_argument("name")
        cmd.add_argument("--authorization")
        if name == "run-check":
            cmd.add_argument("--module")
    abandon = commands.add_parser("abandon-run")
    abandon.add_argument("run_id")
    abandon.add_argument("--reason", required=True)
    prepare = commands.add_parser("prepare-module")
    prepare.add_argument("module")
    done = commands.add_parser("complete-module")
    done.add_argument("module")
    done.add_argument("--report", required=True)
    export = commands.add_parser("export")
    export.add_argument("--output", required=True)
    commands.add_parser("install-git-hook")
    commands.add_parser("check-push")
    search = commands.add_parser("knowledge-search")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)
    record = commands.add_parser("record-monitor")
    record.add_argument("--provider", required=True)
    record.add_argument("--handle", required=True)
    return p


def execute(args: argparse.Namespace) -> dict:
    if args.command == "stages":
        return {"stage_catalog": list(STAGES), "profiles": list(PROFILES), "targets": list(TARGETS),
                "conditional_approval_gates": sorted(GATES), "instruction": "status shows this task's selected route"}
    root = vcs.repo_root(args.repo)
    if args.command == "init":
        return init_project(root, args.base)
    if args.command == "doctor":
        from .model import validate_config, resolve_workflow, ADAPTER_STAGES
        from .storage import read_json
        config_path = inside(root, ".harness/project.json")
        config = validate_config(read_json(config_path)) if config_path.exists() else None
        workflow = resolve_workflow(config, selected_options(args)) if config else None
        missing = []
        capability_choices = []
        missing_config = [] if config and config["stage_checks"].get("review") else ["stage_checks.review"]
        if config:
            probe = Workflow(root, "capability-doctor")
            for slot, stage in CAPABILITY_STAGES.items():
                if not workflow["enabled"][stage]:
                    continue
                try:
                    capability_choices.append({"slot": slot, **capabilities.selection(probe, {"workflow": workflow}, slot)})
                except HarnessError as error:
                    missing_config.append(f"capabilities.{slot}: {error}")
            if workflow["enabled"]["integration"] and not config["stage_checks"].get("integration"):
                missing_config.append("stage_checks.integration")
            missing_config.extend(f"adapters.{stage}" for stage in sorted(ADAPTER_STAGES)
                                  if workflow["enabled"][stage] and stage not in config["adapters"])
            required_checks = set(config["stage_checks"].get("review", []))
            if workflow["enabled"]["integration"]:
                required_checks.update(config["stage_checks"].get("integration", []))
            for category in ("checks", "adapters"):
                for name, spec in config[category].items():
                    if (category == "adapters" and not workflow["enabled"][name]) or (category == "checks" and name not in required_checks):
                        continue
                    command = spec["argv"][0].replace("{plugin_root}", str(PLUGIN_ROOT)).replace("{repo}", str(root))
                    exists = (root / command).is_file() if ("/" in command or "\\" in command) else shutil.which(command)
                    if not exists:
                        missing.append(f"{category}.{name}: {command}")
        return {"python": sys.version.split()[0], "git": vcs.git(root, "--version"),
                "repository": str(root), "branch": vcs.branch(root), "configured": bool(config),
                "workflow": workflow,
                "capability_choices": capability_choices,
                "checks_configured": config["stage_checks"] if config else {},
                "missing_executables": missing, "missing_configuration": missing_config,
                "status": "pass" if config and not missing and not missing_config else "needs_configuration"}
    if args.command == "install-git-hook":
        return gates.install(root, PLUGIN_ROOT)
    if args.command == "check-push":
        return gates.check_push(root, sys.stdin.read())
    if args.command == "knowledge-search":
        return knowledge.search(root, args.query, args.limit)
    require(args.task, "--task is required for workflow commands")
    w = Workflow(root, args.task)
    cmd = args.command
    if cmd == "start":
        return w.start(args.goal, args.base, options=selected_options(args))
    if cmd == "configure-flow":
        return w.configure_flow(selected_options(args), args.reason)
    if cmd in {"status", "resume"}:
        result = w.status()
        if cmd == "resume":
            result["next_skill"] = f"harness-devflow:{skill_for(result['current_stage'])}" if result["current_stage"] else None
            result["instruction"] = "Read state and execute the current stage skill; runtime does not invoke an LLM"
        return result
    if cmd == "enter":
        return w.enter(args.stage)
    if cmd in {"complete", "request-approval"}:
        return w.complete(args.stage, args.report, request_approval=cmd == "request-approval")
    if cmd == "approve":
        return w.approve(args.stage, args.actor, args.note)
    if cmd in {"skip", "fail", "reopen"}:
        return getattr(w, cmd)(args.stage, args.reason)
    if cmd in {"abort", "sync-config"}:
        return getattr(w, cmd.replace("-", "_"))(args.reason)
    if cmd == "plan":
        return w.plan(args.tasks)
    if cmd == "prepare-capability":
        return capabilities.prepare(w, args.slot, args.reason)
    if cmd == "complete-capability":
        return capabilities.complete(w, args.slot, args.report)
    if cmd == "collect-recon":
        return runner.run(w, "capability", "recon", scopes=args.scope, keywords=args.keyword)
    if cmd in {"run-check", "run-adapter"}:
        return runner.run(w, "check" if cmd == "run-check" else "adapter", args.name,
                          authorization=args.authorization, module=getattr(args, "module", None))
    if cmd == "abandon-run":
        return runner.abandon(w, args.run_id, args.reason)
    if cmd == "prepare-module":
        return worktrees.prepare(w, args.module)
    if cmd == "complete-module":
        return worktrees.complete(w, args.module, args.report)
    if cmd == "merge-wave":
        return worktrees.merge_wave(w)
    if cmd == "gate":
        return gates.gate(w)
    if cmd == "record-monitor":
        with file_lock(w.lock_path):
            state = w.load()
            require(current(state) == "monitor", "A monitor handle can only be attached at monitor")
            state["monitor"] = {"provider": args.provider, "handle": args.handle}
            w.save(state, "monitor_attached", provider=args.provider, handle=args.handle)
            return w.summary(state)
    if cmd == "export":
        with file_lock(w.lock_path):
            state = w.load(active=False, config_check=False)
            summary = w.summary(state)
            lines = [f"# Harness task: {w.task}", "", state["goal"], "",
                     f"Branch: `{state['branch']}` · Status: `{summary['status']}`", "",
                     f"Workflow: {state['workflow']['profile']} · Target: {state['workflow']['target']}", "",
                     "| Stage | Status | Evidence |", "| --- | --- | --- |"]
            for stage in stage_order(state):
                item = state["stages"][stage]
                evidence = item.get("report", item.get("reason", "")).replace("|", "\\|").replace("\n", " ")
                lines.append(f"| {stage} | {item['status']} | {evidence} |")
            if state.get("capability_uses"):
                lines.extend(["", "## Capability provenance", ""])
                for use in state["capability_uses"]:
                    lines.append(f"- {use['slot']}: {use['provider']} · {use['source_digest']} · {use['status']} · epoch {use['epoch']}")
            lines.extend(["", "## Events", "", "```json", json.dumps(state["events"], indent=2, ensure_ascii=False), "```", ""])
            path = inside(w.root, args.output)
            require(not path.exists(), "Export destination exists; choose a new output path")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(lines), encoding="utf-8")
            return {"output": str(path)}
    raise HarnessError(f"Unknown command {cmd}")


def skill_for(stage: str | None) -> str:
    return {"design_audit": "design-audit", "test_design": "test-design", "design_approval": "flow",
            "implement": "implement", "integration": "integration-test", "push": "delivery",
            "pr": "delivery", "monitor": "monitor", "deploy": "release"}.get(stage, stage or "flow")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = execute(args)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1 if result.get("status") == "failed" else 0
    except (HarnessError, OSError, ValueError) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
