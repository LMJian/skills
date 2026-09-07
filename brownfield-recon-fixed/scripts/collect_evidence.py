#!/usr/bin/env python3
"""Collect a bounded, read-only evidence inventory for brownfield investigation."""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Iterable


SCHEMA_VERSION = "brownfield-recon-evidence-v1"
SKIP_DIRS = {
    ".git",
    ".artifacts",
    ".cache",
    ".idea",
    ".vscode",
    "build",
    "dist",
    "node_modules",
    "output",
    "target",
    "tmp",
    "vendor",
}
SENSITIVE_PART_RE = re.compile(
    r"(^|/)(\.env(?:\.[^/]*)?|[^/]*\.env(?:\.[^/]*)?|[^/]*credential[^/]*|[^/]*private[_-]?key[^/]*|id_(?:rsa|ed25519)(?:\.[^/]*)?|[^/]*\.(?:pem|key))($|/)",
    re.IGNORECASE,
)
GENERATED_RE = re.compile(r"(^|/)(gen|generated|kitex_gen|thrift_gen)(/|$)|\.pb\.go$", re.IGNORECASE)
CONTRACT_SUFFIXES = {".thrift", ".proto", ".avdl", ".graphql", ".gql"}
CONFIG_SUFFIXES = {".yaml", ".yml", ".toml", ".ini"}
TEST_RE = re.compile(r"(^|/)(test|tests|testing)(/|$)|(_test\.|\.test\.)", re.IGNORECASE)


def run(cmd: list[str], cwd: Path, timeout: int = 30) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)


def is_sensitive(rel: str) -> bool:
    return bool(SENSITIVE_PART_RE.search(rel.replace(os.sep, "/")))


def fallback_files(root: Path) -> list[str]:
    files: list[str] = []
    for current, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        current_path = Path(current)
        for name in names:
            rel = (current_path / name).relative_to(root).as_posix()
            if not is_sensitive(rel):
                files.append(rel)
    return sorted(files)


def list_files(root: Path, warnings: list[str]) -> list[str]:
    if shutil.which("rg"):
        cmd = ["rg", "--files", "-0", "--hidden", "--no-ignore-vcs"]
        for directory in sorted(SKIP_DIRS):
            cmd.extend(["-g", f"!{directory}/**", "-g", f"!**/{directory}/**"])
        rc, out, err = run(cmd, root)
        if rc in (0, 1):
            files = [p for p in out.split("\0") if p and not is_sensitive(p)]
            return sorted(p for p in files if not any(part in SKIP_DIRS for part in Path(p).parts))
        warnings.append(f"rg --files failed: {err.strip() or f'rc={rc}'}")
    else:
        warnings.append("rg unavailable; used os.walk fallback")
    return fallback_files(root)


def bounded(items: Iterable[str], limit: int) -> list[str]:
    return list(items)[:limit]


def classify(files: list[str], limit: int) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {
        "contracts": [],
        "configuration": [],
        "persistence": [],
        "generated": [],
        "tests": [],
        "documentation": [],
        "entrypoints": [],
        "outbound_clients": [],
    }
    for rel in files:
        low = rel.lower()
        path = Path(rel)
        suffix = path.suffix.lower()
        parts = set(path.parts)
        if suffix in CONTRACT_SUFFIXES or "idl" in parts or "schema" in parts:
            result["contracts"].append(rel)
        if suffix in CONFIG_SUFFIXES or any(k in low for k in ("config", "/conf/", "tcc", "feature_gate", "/fg")):
            result["configuration"].append(rel)
        if any(k in low for k in ("persistence", "migration", "repository", "/repo/", "leveldb", "redis", "mysql", ".sql")):
            result["persistence"].append(rel)
        if GENERATED_RE.search(rel):
            result["generated"].append(rel)
        if TEST_RE.search(rel):
            result["tests"].append(rel)
        if suffix in {".md", ".rst", ".adoc"} or parts.intersection({"docs", "requirements", "design"}):
            result["documentation"].append(rel)
        # Fix #4: 'client' is an outbound/downstream signal, not an inbound entrypoint.
        # Keep it in a dedicated bucket so the entrypoint map stays low-noise.
        if "client" in low:
            result["outbound_clients"].append(rel)
        # Inbound entrypoints: process mains, or inbound handlers whose path also
        # carries an inbound signal (api/rpc/http/cmd/server dir) to reduce noise.
        inbound_dir = any(k in low for k in ("/api/", "/rpc/", "/http/", "/cmd/", "/server/", "/entry"))
        inbound_role = any(k in low for k in ("handler", "controller", "router"))
        if path.name in {"main.go", "main.py", "main.rs", "index.ts", "index.js"} or (
            inbound_role and inbound_dir
        ) or (inbound_role and not any(k in low for k in ("client", "downstream", "outbound"))):
            result["entrypoints"].append(rel)
    return {name: bounded(sorted(set(paths)), limit) for name, paths in result.items()}


def parse_commits(text: str) -> list[dict[str, str]]:
    commits: list[dict[str, str]] = []
    for line in text.splitlines():
        parts = line.split("\x1f")
        if len(parts) == 4:
            commits.append({"hash": parts[0], "date": parts[1], "author": parts[2], "subject": parts[3]})
    return commits


def git_ref_exists(root: Path, ref: str) -> bool:
    rc, _, _ = run(["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], root)
    return rc == 0


def detect_base_ref(root: Path, requested: str | None, warnings: list[str]) -> str | None:
    if requested:
        if git_ref_exists(root, requested):
            return requested
        # Fix #2: never silently downgrade an explicit --base-ref; surface it.
        fallback = None
        for ref in ("origin/master", "origin/main", "master", "main"):
            if git_ref_exists(root, ref):
                fallback = ref
                break
        warnings.append(
            f"requested base-ref {requested!r} not found; "
            + (
                f"falling back to {fallback!r}"
                if fallback
                else "no fallback base available, using recent-commit window"
            )
        )
        return fallback
    for ref in ("origin/master", "origin/main", "master", "main"):
        if git_ref_exists(root, ref):
            return ref
    return None


def parse_numstat(text: str, limit: int) -> list[dict[str, Any]]:
    stats: dict[str, dict[str, int]] = collections.defaultdict(lambda: {"added": 0, "deleted": 0, "touches": 0})
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) != 3 or not parts[0].isdigit() or not parts[1].isdigit():
            continue
        added, deleted, path = int(parts[0]), int(parts[1]), parts[2]
        stats[path]["added"] += added
        stats[path]["deleted"] += deleted
        stats[path]["touches"] += 1
    rows = [
        {
            "path": path,
            **values,
            "churn": values["added"] + values["deleted"],
            "generated": bool(GENERATED_RE.search(path)),
        }
        for path, values in stats.items()
    ]
    rows.sort(key=lambda row: (row["churn"], row["touches"], row["path"]), reverse=True)
    return rows[:limit]


def git_evidence(root: Path, base_ref: str | None, max_commits: int, limit: int, warnings: list[str]) -> dict[str, Any]:
    rc, top, _ = run(["git", "rev-parse", "--show-toplevel"], root)
    if rc != 0:
        warnings.append("not a Git worktree; Git history unavailable")
        return {"available": False}

    _, branch, _ = run(["git", "branch", "--show-current"], root)
    _, head, _ = run(["git", "rev-parse", "HEAD"], root)
    _, status, _ = run(["git", "status", "--short"], root)
    _, log_text, log_err = run(
        ["git", "log", f"-{max_commits}", "--date=iso-strict", "--format=%H%x1f%ad%x1f%an%x1f%s"], root
    )
    if log_err.strip():
        warnings.append(f"git log warning: {log_err.strip()}")

    base = detect_base_ref(root, base_ref, warnings)
    diff_files: list[dict[str, str]] = []
    diff_stat = ""
    # Fix #3: use merge-base (three-dot) semantics consistently for both the
    # name/stat diff and the churn window, so all branch-diff numbers agree.
    churn_range = f"-{max_commits}"
    diff_semantics = "recent-commit-window"
    if base:
        rc, names, err = run(["git", "diff", "--name-status", f"{base}...HEAD"], root)
        if rc == 0:
            for line in names.splitlines():
                parts = line.split("\t")
                if len(parts) >= 2:
                    diff_files.append({"status": parts[0], "path": parts[-1]})
        elif err.strip():
            warnings.append(f"git diff names failed: {err.strip()}")
        _, diff_stat, _ = run(["git", "diff", "--stat", f"{base}...HEAD"], root)
        churn_range = f"{base}...HEAD"
        diff_semantics = "merge-base (three-dot) vs HEAD"

    _, numstat, _ = run(["git", "log", "--numstat", "--format=", churn_range], root, timeout=60)
    return {
        "available": True,
        "root": top.strip(),
        "branch": branch.strip(),
        "head": head.strip(),
        "base_ref": base,
        "diff_semantics": diff_semantics,
        "churn_range": churn_range,
        "dirty_paths": [line[3:] if len(line) > 3 else line for line in status.splitlines()],
        "recent_commits": parse_commits(log_text),
        "branch_diff_files": diff_files[:limit],
        "branch_diff_truncated": max(0, len(diff_files) - limit),
        "branch_diff_stat": diff_stat.strip(),
        "history_hotspots": parse_numstat(numstat, limit),
    }


def keyword_hits(
    root: Path,
    keywords: list[str],
    max_hits: int,
    warnings: list[str],
    fixed: bool = True,
) -> dict[str, list[dict[str, Any]]]:
    results: dict[str, list[dict[str, Any]]] = {}
    if not keywords:
        return results
    if not shutil.which("rg"):
        mode = "fixed-string" if fixed else "regex"
        warnings.append(f"rg unavailable; {mode} keyword content search skipped")
        return results

    globs = [
        "!vendor/**",
        "!node_modules/**",
        "!.git/**",
        "!.artifacts/**",
        "!dist/**",
        "!build/**",
        "!.env*",
        "!**/.env*",
        "!**/*.env",
        "!**/*.env.*",
        "!*credential*",
        "!*private-key*",
        "!*private_key*",
        "!*.pem",
    ]
    for keyword in keywords:
        # Fix #5: support a regex channel (rg without -F) alongside fixed-string,
        # matching the search-playbook's "regex after learning local naming".
        cmd = ["rg", "-n", "--hidden", "--no-ignore-vcs", "--no-heading", "--color", "never"]
        if fixed:
            cmd.append("-F")
        for glob in globs:
            cmd.extend(["-g", glob])
        cmd.extend(["--", keyword, "."])
        rc, out, err = run(cmd, root, timeout=45)
        if rc not in (0, 1):
            label = "fixed" if fixed else "regex"
            warnings.append(f"{label} keyword search failed for {keyword!r}: {err.strip() or f'rc={rc}'}")
            continue
        hits: list[dict[str, Any]] = []
        for line in out.splitlines()[:max_hits]:
            match = re.match(r"^(.+?):(\d+):(.*)$", line)
            if match and not is_sensitive(match.group(1)):
                hits.append({"path": match.group(1).removeprefix("./"), "line": int(match.group(2)), "text": match.group(3)[:500]})
        results[keyword] = hits
    return results


def knowledge_evidence(root: Path, limit: int) -> dict[str, Any]:
    kb = root / ".ai_knowledge"
    if not kb.is_dir():
        return {"present": False, "files": [], "has_index": False}
    files = []
    for path in kb.rglob("*"):
        if path.is_file() and not is_sensitive(path.relative_to(root).as_posix()):
            files.append(path.relative_to(root).as_posix())
    return {
        "present": True,
        "files": sorted(files)[:limit],
        "files_truncated": max(0, len(files) - limit),
        "has_index": (kb / "index.md").is_file(),
        "has_meta": (kb / "meta.yaml").is_file(),
    }


def devflow_evidence(root: Path, limit: int, warnings: list[str]) -> list[dict[str, Any]]:
    artifacts = root / ".artifacts"
    if not artifacts.is_dir():
        return []
    states: list[dict[str, Any]] = []
    for path in sorted(artifacts.glob("*/state.json"))[:limit]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            stages = data.get("stages") or {}
            states.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "feature": data.get("feature"),
                    "branch": data.get("branch"),
                    "current_stage": data.get("current_stage"),
                    "revision": data.get("revision"),
                    "stage_statuses": {name: value.get("status") for name, value in stages.items() if isinstance(value, dict)},
                }
            )
        except (OSError, ValueError) as exc:
            warnings.append(f"cannot parse {path.relative_to(root)}: {exc}")
    return states


def inventory(files: list[str]) -> dict[str, Any]:
    suffixes = collections.Counter(Path(path).suffix.lower() or "<none>" for path in files)
    top_dirs = collections.Counter(Path(path).parts[0] if len(Path(path).parts) > 1 else "." for path in files)
    return {
        "file_count": len(files),
        "extensions": [{"extension": ext, "count": count} for ext, count in suffixes.most_common(20)],
        "top_level": [{"path": path, "count": count} for path, count in top_dirs.most_common(30)],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root to inspect")
    parser.add_argument("--base-ref", help="Base branch or commit for branch diff")
    parser.add_argument("--keyword", action="append", default=[], help="Exact fixed-string keyword; repeatable")
    parser.add_argument(
        "--regex-keyword",
        action="append",
        default=[],
        help="Regex keyword (rg without -F); use after learning local naming; repeatable",
    )
    parser.add_argument("--max-hits", type=int, default=50, help="Maximum content hits per keyword")
    parser.add_argument("--max-commits", type=int, default=40, help="Recent commits and fallback churn window")
    parser.add_argument("--limit", type=int, default=80, help="Maximum items per bounded inventory section")
    parser.add_argument("--output", default="-", help="JSON output path, or - for stdout")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.repo_root).expanduser().resolve()
    if not root.is_dir():
        print(f"repository root does not exist: {root}", file=sys.stderr)
        return 2
    if args.max_hits < 1 or args.max_commits < 1 or args.limit < 1:
        print("max-hits, max-commits, and limit must be positive", file=sys.stderr)
        return 2

    warnings: list[str] = []
    files = list_files(root, warnings)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "repo_root": str(root),
        "parameters": {
            "base_ref": args.base_ref,
            "keywords": args.keyword,
            "regex_keywords": args.regex_keyword,
            "max_hits": args.max_hits,
            "max_commits": args.max_commits,
            "limit": args.limit,
        },
        "inventory": inventory(files),
        "candidates": classify(files, args.limit),
        "keyword_hits": keyword_hits(root, args.keyword, args.max_hits, warnings, fixed=True),
        "regex_keyword_hits": keyword_hits(root, args.regex_keyword, args.max_hits, warnings, fixed=False),
        "git": git_evidence(root, args.base_ref, args.max_commits, args.limit, warnings),
        "knowledge": knowledge_evidence(root, args.limit),
        "devflow": devflow_evidence(root, args.limit, warnings),
        "warnings": warnings,
        "safety": {
            "read_only_scan": True,
            "skipped_directories": sorted(SKIP_DIRS),
            "sensitive_name_filter": SENSITIVE_PART_RE.pattern,
        },
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output == "-":
        sys.stdout.write(rendered)
    else:
        # Fix #1: resolve relative output against the CURRENT working directory,
        # not the scanned repo-root, so we never write artifacts into the target
        # repository. Warn if the resolved path still lands inside the repo
        # (outside its .artifacts/) to protect the read-only guarantee.
        output = Path(args.output).expanduser()
        if not output.is_absolute():
            output = (Path.cwd() / output).resolve()
        else:
            output = output.resolve()
        try:
            rel_to_repo = output.relative_to(root)
            inside_repo = True
        except ValueError:
            inside_repo = False
        if inside_repo and not str(rel_to_repo).startswith(".artifacts"):
            warnings.append(
                f"output path {output} is inside the scanned repo-root outside .artifacts/; "
                "this may pollute the target repository — prefer an absolute path in your session workspace"
            )
            # Re-render so the warning is captured in the written artifact too.
            payload["warnings"] = warnings
            rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        print(json.dumps({"written": str(output), "schema_version": SCHEMA_VERSION}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
