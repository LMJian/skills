"""Atomic state writes, bounded OS locks and confined artifact paths."""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time

from .model import HarnessError, require


def inside(root: Path, name: str | Path) -> Path:
    path = (root / name).resolve()
    require(path.is_relative_to(root.resolve()), f"Path escapes repository: {name}")
    return path


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise HarnessError(f"Cannot read JSON {path}: {error}") from error
    require(isinstance(data, dict), f"Expected JSON object: {path}")
    return data


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def file_digest(path: Path) -> str:
    require(path.is_file(), f"Artifact missing or not a regular file: {path}")
    require(path.stat().st_size > 0, f"Artifact is empty: {path}")
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def snapshots(root: Path, names: list[str]) -> list[dict]:
    result = []
    for name in dict.fromkeys(names):
        path = inside(root, name)
        relative = path.relative_to(root).as_posix()
        result.append({"path": relative, "sha256": file_digest(path)})
    return result


def verify_snapshots(root: Path, entries: list[dict]) -> None:
    for entry in entries:
        path = inside(root, entry["path"])
        require(file_digest(path) == entry["sha256"], f"Artifact changed: {entry['path']}")


@contextlib.contextmanager
def file_lock(path: Path, timeout: float = 5):
    """OS releases the lock even after process death; never delete its inode."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                if os.name == "nt":
                    import msvcrt
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except (BlockingIOError, OSError) as error:
                if time.monotonic() >= deadline:
                    raise HarnessError(f"Workflow is busy (lock timeout): {path}") from error
                time.sleep(0.05)
        try:
            yield
        finally:
            if os.name == "nt":
                import msvcrt
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
