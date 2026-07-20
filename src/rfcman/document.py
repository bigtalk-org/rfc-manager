from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from rfcman.constants import Stage


@dataclass
class FrontMatter:
    id: str
    title: str
    type: Stage
    author: str
    created: date
    updated: date
    version: str = "0.1.0"
    references: str | None = None
    related: list[str] = field(default_factory=list)
    supersedes: str | None = None
    superseded_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "version": self.version,
            "references": self.references,
            "type": self.type.value,
            "author": self.author,
            "created": self.created.isoformat(),
            "updated": self.updated.isoformat(),
            "related": list(self.related),
            "supersedes": self.supersedes,
            "superseded_by": self.superseded_by,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FrontMatter:
        related_raw = data.get("related") or []
        related = [str(x) for x in related_raw]
        created = _parse_date(data["created"])
        updated = _parse_date(data.get("updated", data["created"]))
        refs = data.get("references")
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            type=Stage(str(data["type"])),
            author=str(data["author"]),
            created=created,
            updated=updated,
            version=str(data.get("version", "0.1.0")),
            references=str(refs) if refs not in (None, "", "null") else None,
            related=related,
            supersedes=_opt_str(data.get("supersedes")),
            superseded_by=_opt_str(data.get("superseded_by")),
        )


@dataclass
class Document:
    path: Path
    meta: FrontMatter
    body: str

    @property
    def summary(self) -> str:
        return extract_summary(self.body)

    @property
    def user_ref(self) -> str:
        """User-facing token: Stage-filename-stem (e.g. Idea-new-idea)."""
        return f"{self.meta.type.value}-{self.path.stem}"


def _parse_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _opt_str(value: Any) -> str | None:
    if value in (None, "", "null"):
        return None
    return str(value)


def extract_summary(body: str) -> str:
    lines = body.splitlines()
    capturing = False
    collected: list[str] = []
    for line in lines:
        if line.strip().lower() == "## summary":
            capturing = True
            continue
        if capturing:
            if line.startswith("## "):
                break
            collected.append(line)
    text = "\n".join(collected).strip()
    if text:
        return text
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("---"):
            return stripped
    return "(no summary)"


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        msg = "missing YAML frontmatter"
        raise ValueError(msg)
    end = text.find("\n---", 3)
    if end == -1:
        msg = "unterminated YAML frontmatter"
        raise ValueError(msg)
    raw = text[3:end].strip()
    body = text[end + 4 :].lstrip("\n")
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        msg = "frontmatter must be a mapping"
        raise ValueError(msg)
    return data, body


def render_document(meta: FrontMatter, body: str) -> str:
    dumped = yaml.safe_dump(
        meta.to_dict(),
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).rstrip()
    body = body.lstrip("\n")
    if body and not body.endswith("\n"):
        body += "\n"
    return f"---\n{dumped}\n---\n\n{body}"


def read_document(path: Path) -> Document:
    text = path.read_text(encoding="utf-8")
    data, body = split_frontmatter(text)
    return Document(path=path, meta=FrontMatter.from_dict(data), body=body)


def write_document(path: Path, meta: FrontMatter, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_document(meta, body), encoding="utf-8")
