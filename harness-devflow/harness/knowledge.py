"""Optional local knowledge snapshots with explicit approval provenance."""
from __future__ import annotations

from pathlib import Path
import shutil
import uuid

from .model import now, require
from .storage import atomic_json, inside, read_json, snapshots, verify_snapshots


def archive(workflow, item: dict, report: dict) -> str:
    directory = inside(workflow.root, f".harness/knowledge/{workflow.task}/{uuid.uuid4().hex}")
    directory.mkdir(parents=True)
    notes = []
    for index, name in enumerate(report["artifacts"]):
        source = inside(workflow.root, name)
        target = directory / f"{index:03d}-{source.name}"
        shutil.copyfile(source, target)
        notes.append(str(target))
    path = directory / "record.json"
    atomic_json(path, {"schema_version": 2, "task": workflow.task, "archived_at": now(),
                       "summary": report["summary"], "approval": item.get("approval"),
                       "outcome": report["details"]["outcome"],
                       "evidence": snapshots(workflow.root, notes)})
    return path.relative_to(workflow.root).as_posix()


def search(root: Path, query: str, limit: int = 10) -> dict:
    require(query.strip(), "Search query cannot be empty")
    require(1 <= limit <= 100, "Search limit must be 1–100")
    terms = query.casefold().split()
    matches = []
    directory = inside(root, ".harness/knowledge")
    for path in sorted([*directory.glob("*/*/record.json"), *directory.glob("*/*/approved.json")]):
        record = read_json(inside(root, path))
        verify_snapshots(root, record["evidence"])
        for evidence in record["evidence"]:
            source = inside(root, evidence["path"])
            if source.suffix.lower() not in {".md", ".txt", ".json"} or source.stat().st_size > 1024 * 1024:
                continue
            content = source.read_text(encoding="utf-8", errors="replace")
            lines = [(i, line) for i, line in enumerate(content.splitlines(), 1)
                     if any(term in line.casefold() for term in terms)]
            if lines:
                matches.append({"task": record["task"], "path": str(source),
                                "archived_at": record.get("archived_at", record.get("approved_at")),
                                "human_approved": bool(record.get("approval")),
                                "matches": [{"line": i, "text": line[:500]} for i, line in lines[:8]]})
    return {"query": query, "results": matches[:limit], "truncated": len(matches) > limit}
