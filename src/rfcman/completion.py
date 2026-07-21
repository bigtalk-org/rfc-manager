from __future__ import annotations

from collections.abc import Iterable

from rfcman.constants import LIST_ALIASES, Stage
from rfcman.document import Document
from rfcman.store import documents_in_stage, format_user_ref, iter_documents, upgradeable_documents
from rfcman.workspace import RfcRootError, find_root


def _safe_docs() -> list[Document]:
    try:
        root = find_root()
    except RfcRootError:
        return []
    return iter_documents(root)


def _ref(doc: Document) -> str:
    return format_user_ref(doc)


def _help(doc: Document) -> str:
    return doc.meta.title


def _is_type_prefix(needle: str) -> bool:
    return any(stage.value.casefold().startswith(needle) for stage in Stage)


def _match(doc: Document, incomplete: str) -> bool:
    if not incomplete:
        return True
    needle = incomplete.casefold()
    ref = _ref(doc).casefold()
    stage = doc.meta.type.value.casefold()
    stem = doc.path.stem.casefold()
    title = doc.meta.title.casefold()

    type_hit = stage.startswith(needle) or ref.startswith(needle)
    if _is_type_prefix(needle):
        return type_hit

    if type_hit:
        return True
    if stem.startswith(needle):
        return True
    if title.startswith(needle):
        return True
    return any(word.startswith(needle) for word in title.split())


def _items(docs: Iterable[Document], incomplete: str) -> list[tuple[str, str]]:
    """Return (value, help) pairs — works with Typer autocompletion across versions."""
    out: list[tuple[str, str]] = []
    for doc in sorted(docs, key=lambda d: d.path.stem):
        if _match(doc, incomplete):
            out.append((_ref(doc), _help(doc)))
    return out


def complete_rfc_id(incomplete: str) -> list[tuple[str, str]]:
    return _items(_safe_docs(), incomplete)


def complete_upgradeable_id(incomplete: str) -> list[tuple[str, str]]:
    try:
        root = find_root()
    except RfcRootError:
        return []
    return _items(upgradeable_documents(root), incomplete)


def complete_accepted_id(incomplete: str) -> list[tuple[str, str]]:
    try:
        root = find_root()
    except RfcRootError:
        return []
    return _items(documents_in_stage(root, Stage.ACCEPTED), incomplete)


def complete_list_stage(incomplete: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    needle = incomplete.lower()
    for alias, stage in sorted(LIST_ALIASES.items()):
        if alias in seen:
            continue
        if needle and not alias.startswith(needle):
            continue
        seen.add(alias)
        out.append((alias, stage.value))
    return out
