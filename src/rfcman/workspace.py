from __future__ import annotations

import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from rfcman.constants import (
    MARKER_FILE,
    PROJECT_FILE,
    STAGE_DIRS,
    STATE_DIR,
    TPLS_DIR,
)


class RfcRootError(RuntimeError):
    """Raised when an RFC tree cannot be located or created."""


def default_rfcs_path(parent: Path | None = None) -> Path:
    base = parent if parent is not None else Path.cwd()
    return (base / "rfcs").resolve()


def find_root(start: Path | None = None, *, path: Path | None = None) -> Path:
    if path is not None:
        root = path.expanduser().resolve()
        if not _looks_like_root(root):
            msg = f"not an RFC tree: {root}"
            raise RfcRootError(msg)
        return root

    cur = (start or Path.cwd()).resolve()
    for base in [cur, *cur.parents]:
        project = base / PROJECT_FILE
        if project.is_file():
            root = _root_from_project(project)
            if _looks_like_root(root):
                return root
            msg = f"{project} points to missing or invalid tree: {root}"
            raise RfcRootError(msg)
        candidate = base / "rfcs"
        if _looks_like_root(candidate):
            return candidate
        if _looks_like_root(base):
            return base
    msg = "no RFC tree found; run `rfcman init` first"
    raise RfcRootError(msg)


def _load_project(project: Path) -> dict[str, Any]:
    data = yaml.safe_load(project.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        msg = f"invalid {PROJECT_FILE}: expected a mapping"
        raise RfcRootError(msg)
    return data


def find_project_file(start: Path | None = None) -> Path | None:
    cur = (start or Path.cwd()).resolve()
    for base in [cur, *cur.parents]:
        project = base / PROJECT_FILE
        if project.is_file():
            return project
    return None


def _root_from_project(project: Path) -> Path:
    data = _load_project(project)
    location = data.get("location")
    if not location:
        msg = f"invalid {PROJECT_FILE}: missing location"
        raise RfcRootError(msg)
    loc = Path(str(location)).expanduser()
    if loc.is_absolute():
        return loc.resolve()
    return (project.parent / loc).resolve()


def write_project_file(command_root: Path, rfc_root: Path) -> Path:
    """Write rfcman.yml at the directory where `init` was run."""
    command_root = command_root.resolve()
    rfc_root = rfc_root.resolve()
    location = _rel_or_abs(command_root, rfc_root)
    payload: dict[str, Any] = {
        "location": location,
        "created": datetime.now(UTC).date().isoformat(),
        "author": git_author(),
    }
    target = command_root / PROJECT_FILE
    target.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return target


def resolve_author(start: Path | None = None) -> str:
    """Author from rfcman.yml when set; otherwise git config."""
    project = find_project_file(start)
    if project is not None:
        data = _load_project(project)
        author = data.get("author")
        if isinstance(author, str) and author.strip():
            return author.strip()
    return git_author()


def _rel_or_abs(base: Path, target: Path) -> str:
    try:
        return str(target.resolve().relative_to(base.resolve()))
    except ValueError:
        return str(target.resolve())


def _looks_like_root(path: Path) -> bool:
    if not path.is_dir():
        return False
    marker = path / STATE_DIR / MARKER_FILE
    if marker.is_file():
        return True
    return (path / TPLS_DIR).is_dir() and all((path / d).is_dir() for d in STAGE_DIRS.values())


def ensure_layout(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / STATE_DIR).mkdir(parents=True, exist_ok=True)
    (root / TPLS_DIR).mkdir(parents=True, exist_ok=True)
    for dirname in STAGE_DIRS.values():
        (root / dirname).mkdir(parents=True, exist_ok=True)
    marker = root / STATE_DIR / MARKER_FILE
    if not marker.exists():
        marker.write_text(
            yaml.safe_dump({"schema": 1, "tool": "rfcman"}, sort_keys=False),
            encoding="utf-8",
        )


def allocate_id() -> str:
    return str(uuid4())


def slugify(title: str) -> str:
    slug = title.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "untitled"


def document_filename(folder: Path, title: str) -> str:
    """Unique `{slug}.md` in folder; append short uuid on collision."""
    base = slugify(title)
    candidate = f"{base}.md"
    if not (folder / candidate).exists():
        return candidate
    short = uuid4().hex[:8]
    return f"{base}-{short}.md"


def git_author() -> str:
    name = _git_config("user.name") or "Unknown"
    email = _git_config("user.email") or "unknown@example.com"
    return f"{name} <{email}>"


def _git_config(key: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "config", "--get", key],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    value = result.stdout.strip()
    return value or None
