from __future__ import annotations

from datetime import date
from pathlib import Path

from rfcman.constants import Stage, stage_dir
from rfcman.document import Document, FrontMatter, read_document, write_document
from rfcman.store import (
    documents_in_stage,
    format_user_ref,
    index_by_id,
    iter_documents,
    render_body,
    upgraded_source_ids,
)
from rfcman.workspace import allocate_id, document_filename, resolve_author


def create_document(
    root: Path,
    *,
    stage: Stage,
    title: str,
    references: str | None = None,
    related: list[str] | None = None,
    supersedes: str | None = None,
    superseded_by: str | None = None,
    extra: dict[str, str] | None = None,
) -> Document:
    doc_id = allocate_id()
    today = date.today()
    meta = FrontMatter(
        id=doc_id,
        title=title,
        type=stage,
        author=resolve_author(),
        created=today,
        updated=today,
        references=references,
        related=related or [],
        supersedes=supersedes,
        superseded_by=superseded_by,
    )
    body_vars: dict[str, str] = {"title": title, **(extra or {})}
    if stage == Stage.SUPERSEDED and "replacement" not in body_vars:
        body_vars["replacement"] = superseded_by if superseded_by is not None else "TBD"
    body = render_body(root, stage, **body_vars)
    folder = stage_dir(root, stage)
    path = folder / document_filename(folder, title)
    write_document(path, meta, body)
    return Document(path=path, meta=meta, body=body)


def upgrade_to(
    root: Path,
    doc: Document,
    target: Stage,
    *,
    used: set[str] | None = None,
) -> Document:
    ref = format_user_ref(doc)
    if doc.meta.type in {Stage.REJECTED, Stage.SUPERSEDED}:
        raise ValueError(f"{ref} cannot be upgraded further")
    sources = used if used is not None else upgraded_source_ids(root)
    if doc.meta.id in sources:
        raise ValueError(f"{ref} has already been upgraded")
    return create_document(
        root,
        stage=target,
        title=doc.meta.title,
        references=ref,
        related=[doc.meta.id, *doc.meta.related],
    )


def supersede(root: Path, old_id: str, new_id: str) -> tuple[Document, Document]:
    docs = iter_documents(root)
    by_id = index_by_id(docs)
    if old_id not in by_id:
        raise LookupError(f"RFC {old_id} not found")
    if new_id not in by_id:
        raise LookupError(f"RFC {new_id} not found")
    old = by_id[old_id]
    new = by_id[new_id]
    if old.meta.type != Stage.ACCEPTED:
        raise ValueError(f"{format_user_ref(old)} must be Accepted")
    if new.meta.type != Stage.ACCEPTED:
        raise ValueError(f"{format_user_ref(new)} must be Accepted")
    if old_id == new_id:
        raise ValueError("cannot supersede an RFC with itself")

    today = date.today()
    replacement = format_user_ref(new)
    old.meta.type = Stage.SUPERSEDED
    old.meta.superseded_by = new_id
    old.meta.updated = today
    body = render_body(
        root,
        Stage.SUPERSEDED,
        title=old.meta.title,
        replacement=replacement,
    )
    dest = stage_dir(root, Stage.SUPERSEDED) / old.path.name
    if old.path.resolve() != dest.resolve():
        dest.parent.mkdir(parents=True, exist_ok=True)
        old.path.rename(dest)
    write_document(dest, old.meta, body)

    new.meta.supersedes = old_id
    new.meta.updated = today
    if old_id not in new.meta.related:
        new.meta.related.append(old_id)
    write_document(new.path, new.meta, new.body)

    return read_document(dest), read_document(new.path)


def list_accepted_choices(root: Path, *, exclude: str | None = None) -> list[Document]:
    docs = documents_in_stage(root, Stage.ACCEPTED)
    if exclude is None:
        return docs
    return [d for d in docs if d.meta.id != exclude]
