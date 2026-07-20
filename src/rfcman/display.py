from __future__ import annotations

from pathlib import Path

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree

from rfcman.constants import Stage
from rfcman.document import Document
from rfcman.store import load_indexes, resolve_in_indexes


def file_link(path: Path, label: str | None = None) -> Text:
    text = Text(label or str(path))
    try:
        uri = path.resolve().as_uri()
    except OSError:
        return text
    text.stylize(f"link {uri}")
    return text


def print_idea_description(console: Console, root: Path, doc: Document) -> None:
    _, by_id, _ = load_indexes(root)
    console.print(
        Panel(
            doc.summary,
            title=f"[bold]{doc.user_ref}[/] — {doc.meta.title}",
            border_style="cyan",
        )
    )
    _print_related_footer(console, doc, by_id=by_id)


def print_describe_tree(console: Console, root: Path, doc: Document) -> None:
    _, by_id, by_stage_stem = load_indexes(root)
    tree = Tree(_node_label(doc), guide_style="dim")
    _walk_references(tree, doc, by_id=by_id, by_stage_stem=by_stage_stem, visited=set())
    console.print(tree)
    console.print()
    console.print(
        Panel(
            doc.summary,
            title=f"[bold]{doc.user_ref}[/] — {doc.meta.title}",
            border_style="cyan",
        )
    )
    _print_related_footer(console, doc, by_id=by_id)


def _node_label(doc: Document) -> Group:
    title = Text.assemble(
        (doc.user_ref, "bold cyan"),
        " ",
        (doc.meta.title, "bold"),
    )
    link = file_link(doc.path, label=str(doc.path))
    link.stylize("dim")
    return Group(title, link)


def _walk_references(
    tree: Tree,
    doc: Document,
    *,
    by_id: dict[str, Document],
    by_stage_stem: dict[tuple[Stage, str], Document],
    visited: set[str],
) -> None:
    if doc.meta.id in visited:
        return
    visited.add(doc.meta.id)
    if not doc.meta.references:
        return
    try:
        parent = resolve_in_indexes(doc.meta.references, by_id=by_id, by_stage_stem=by_stage_stem)
    except (LookupError, ValueError):
        tree.add(Text(f"broken: {doc.meta.references}", style="red"))
        return
    branch = tree.add(_node_label(parent))
    _walk_references(branch, parent, by_id=by_id, by_stage_stem=by_stage_stem, visited=visited)


def _print_related_footer(
    console: Console,
    doc: Document,
    by_id: dict[str, Document] | None = None,
) -> None:
    ids = list(doc.meta.related)
    if doc.meta.supersedes is not None:
        ids.append(doc.meta.supersedes)
    if doc.meta.superseded_by is not None:
        ids.append(doc.meta.superseded_by)
    seen: set[str] = set()
    ordered: list[str] = []
    for related_id in ids:
        if related_id not in seen:
            seen.add(related_id)
            ordered.append(related_id)
    if not ordered:
        return
    parts: list[Text | str] = [Text("Related: ", style="dim")]
    for idx, related_id in enumerate(ordered):
        if idx:
            parts.append(Text(" · ", style="dim"))
        if by_id and related_id in by_id:
            related = by_id[related_id]
            parts.append(file_link(related.path, label=related.user_ref))
        else:
            parts.append(Text(related_id[:8] + "…"))
    console.print(Text.assemble(*parts))


def stage_badge(stage: Stage) -> str:
    colors = {
        Stage.IDEA: "blue",
        Stage.RESEARCH: "magenta",
        Stage.PROPOSED: "yellow",
        Stage.ACCEPTED: "green",
        Stage.REJECTED: "red",
        Stage.SUPERSEDED: "bright_black",
    }
    return f"[{colors[stage]}]{stage.value}[/]"
