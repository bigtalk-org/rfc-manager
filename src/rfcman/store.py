from __future__ import annotations

from importlib import resources
from pathlib import Path
from uuid import UUID

from jinja2 import BaseLoader, Environment, StrictUndefined

from rfcman.constants import STAGE_DIRS, STAGE_PREFIXES, TPLS_DIR, Stage, stage_dir
from rfcman.document import Document, read_document


def is_uuid(token: str) -> bool:
    try:
        UUID(token.strip())
    except ValueError:
        return False
    return True


def parse_user_ref(token: str) -> tuple[Stage, str]:
    """Parse `Idea-new-idea` → (Idea, 'new-idea')."""
    text = token.strip()
    lower = text.casefold()
    for stage in STAGE_PREFIXES:
        prefix = f"{stage.value}-"
        p = prefix.casefold()
        if lower.startswith(p):
            stem = text[len(prefix) :]
            if stem:
                return stage, stem
    msg = f"invalid reference '{token}'; expected Stage-filename (e.g. Idea-new-idea)"
    raise ValueError(msg)


def format_user_ref(doc: Document) -> str:
    return doc.user_ref


def iter_documents(root: Path) -> list[Document]:
    docs: list[Document] = []
    for dirname in STAGE_DIRS.values():
        folder = root / dirname
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.md")):
            docs.append(read_document(path))
    return docs


def index_by_id(docs: list[Document]) -> dict[str, Document]:
    by_id: dict[str, Document] = {}
    for doc in docs:
        if doc.meta.id in by_id:
            msg = f"duplicate id {doc.meta.id}: {by_id[doc.meta.id].path} and {doc.path}"
            raise ValueError(msg)
        by_id[doc.meta.id] = doc
    return by_id


def index_by_stage_stem(docs: list[Document]) -> dict[tuple[Stage, str], Document]:
    return {(doc.meta.type, doc.path.stem): doc for doc in docs}


def load_indexes(
    root: Path,
) -> tuple[list[Document], dict[str, Document], dict[tuple[Stage, str], Document]]:
    docs = iter_documents(root)
    return docs, index_by_id(docs), index_by_stage_stem(docs)


def find_by_id(root: Path, doc_id: str) -> Document:
    docs = iter_documents(root)
    by_id = index_by_id(docs)
    if doc_id not in by_id:
        msg = f"RFC {doc_id} not found"
        raise LookupError(msg)
    return by_id[doc_id]


def find_by_user_ref(root: Path, token: str) -> Document:
    stage, stem = parse_user_ref(token)
    path = stage_dir(root, stage) / f"{stem}.md"
    if not path.is_file():
        msg = f"RFC {token} not found"
        raise LookupError(msg)
    doc = read_document(path)
    if doc.meta.type != stage:
        msg = f"'{token}' does not match: file is {doc.meta.type.value}"
        raise ValueError(msg)
    return doc


def resolve_in_indexes(
    token: str,
    *,
    by_id: dict[str, Document],
    by_stage_stem: dict[tuple[Stage, str], Document],
) -> Document:
    text = token.strip()
    if is_uuid(text):
        if text not in by_id:
            msg = f"RFC {text} not found"
            raise LookupError(msg)
        return by_id[text]
    stage, stem = parse_user_ref(text)
    key = (stage, stem)
    if key not in by_stage_stem:
        msg = f"RFC {token} not found"
        raise LookupError(msg)
    return by_stage_stem[key]


def resolve_doc_token(root: Path, token: str) -> Document:
    """Resolve a UUID or Stage-filename token to a document."""
    text = token.strip()
    if is_uuid(text):
        return find_by_id(root, text)
    return find_by_user_ref(root, text)


def documents_in_stage(root: Path, stage: Stage) -> list[Document]:
    folder = stage_dir(root, stage)
    if not folder.is_dir():
        return []
    return [read_document(p) for p in sorted(folder.glob("*.md"))]


def upgraded_source_ids(
    root: Path,
    *,
    docs: list[Document] | None = None,
) -> set[str]:
    """UUIDs that already have a child pointing at them via `references`."""
    if docs is None:
        docs, by_id, by_stage_stem = load_indexes(root)
    else:
        by_id = index_by_id(docs)
        by_stage_stem = index_by_stage_stem(docs)
    used: set[str] = set()
    for doc in docs:
        if not doc.meta.references:
            continue
        try:
            src = resolve_in_indexes(doc.meta.references, by_id=by_id, by_stage_stem=by_stage_stem)
        except (LookupError, ValueError):
            continue
        used.add(src.meta.id)
    return used


def is_upgradeable(doc: Document, *, used: set[str] | None = None) -> bool:
    if doc.meta.type in {Stage.REJECTED, Stage.SUPERSEDED}:
        return False
    return used is None or doc.meta.id not in used


def upgradeable_documents(root: Path) -> list[Document]:
    docs = iter_documents(root)
    used = upgraded_source_ids(root, docs=docs)
    return [d for d in docs if is_upgradeable(d, used=used)]


_TEMPLATE_NAMES: dict[Stage, str] = {
    Stage.IDEA: "idea.md.j2",
    Stage.RESEARCH: "research.md.j2",
    Stage.PROPOSED: "proposed.md.j2",
    Stage.ACCEPTED: "accepted.md.j2",
    Stage.REJECTED: "rejected.md.j2",
    Stage.SUPERSEDED: "superseded.md.j2",
}


def builtin_template(stage: Stage) -> str:
    filename = _TEMPLATE_NAMES[stage]
    base = resources.files("rfcman.templates")
    return (base / filename).read_text(encoding="utf-8")


def dump_user_templates(root: Path) -> None:
    tpls = root / TPLS_DIR
    tpls.mkdir(parents=True, exist_ok=True)
    for stage in Stage:
        target = tpls / _TEMPLATE_NAMES[stage]
        if not target.exists():
            target.write_text(builtin_template(stage), encoding="utf-8")


def load_body_template(root: Path, stage: Stage) -> str:
    user = root / TPLS_DIR / _TEMPLATE_NAMES[stage]
    if user.is_file():
        return user.read_text(encoding="utf-8")
    return builtin_template(stage)


def render_body(root: Path, stage: Stage, *, title: str, **extra: str) -> str:
    env = Environment(loader=BaseLoader(), undefined=StrictUndefined, autoescape=False)
    template = env.from_string(load_body_template(root, stage))
    return str(template.render(title=title, **extra))
