from __future__ import annotations

from pathlib import Path
from typing import Annotated, NoReturn

import questionary
import typer
from rich.console import Console
from rich.table import Table

from rfcman import __version__
from rfcman.check import check_tree
from rfcman.completion import (
    complete_accepted_id,
    complete_list_stage,
    complete_rfc_id,
    complete_upgradeable_id,
)
from rfcman.constants import LIST_ALIASES, Stage
from rfcman.display import print_describe_tree, print_idea_description, stage_badge
from rfcman.document import Document
from rfcman.lifecycle import create_document, list_accepted_choices, supersede, upgrade_to
from rfcman.store import (
    documents_in_stage,
    dump_user_templates,
    iter_documents,
    resolve_doc_token,
    upgraded_source_ids,
)
from rfcman.workspace import (
    RfcRootError,
    default_rfcs_path,
    ensure_layout,
    find_root,
    write_project_file,
)

PathOption = Annotated[
    Path | None,
    typer.Option(
        "--path",
        "-p",
        help="RFC tree root (overrides rfcman.yml discovery).",
        exists=False,
        file_okay=False,
        dir_okay=True,
        resolve_path=False,
    ),
]

app = typer.Typer(
    name="rfcman",
    help="\bElegant RFC lifecycle manager.\n[dim]A BigTalk utility[/]",
    no_args_is_help=False,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = Console(stderr=False)
err = Console(stderr=True)

init_app = typer.Typer(
    help="Create an RFC tree and dump editable body templates.",
    invoke_without_command=True,
    no_args_is_help=False,
)
list_app = typer.Typer(
    help="List RFCs as one-line summaries.",
    invoke_without_command=True,
    no_args_is_help=False,
    context_settings={"allow_interspersed_args": True},
)
describe_app = typer.Typer(
    help="Show an RFC summary and reference tree.",
    invoke_without_command=True,
    no_args_is_help=False,
    context_settings={"allow_interspersed_args": True},
)
upgrade_app = typer.Typer(
    help="Advance an RFC to the next lifecycle stage.",
    invoke_without_command=True,
    no_args_is_help=False,
    context_settings={"allow_interspersed_args": True},
)
supersede_app = typer.Typer(
    help="Mark an accepted RFC as superseded by another accepted RFC.",
    invoke_without_command=True,
    no_args_is_help=False,
    context_settings={"allow_interspersed_args": True},
)
check_app = typer.Typer(
    help="Validate links and structure across the RFC tree.",
    invoke_without_command=True,
    no_args_is_help=False,
)
new_app = typer.Typer(help="Create a new RFC document.", no_args_is_help=True)
idea_app = typer.Typer(
    help="Create a new idea RFC.",
    invoke_without_command=True,
    no_args_is_help=False,
    context_settings={"allow_interspersed_args": True},
)

app.add_typer(init_app, name="init")
app.add_typer(list_app, name="list")
app.add_typer(describe_app, name="describe")
app.add_typer(upgrade_app, name="upgrade")
app.add_typer(supersede_app, name="supersede")
app.add_typer(check_app, name="check")
app.add_typer(new_app, name="new")
new_app.add_typer(idea_app, name="idea")


def _root_or_exit(path: Path | None = None) -> Path:
    try:
        return find_root(path=path)
    except RfcRootError as exc:
        err.print(f"[red]error:[/] {exc}")
        raise typer.Exit(code=1) from exc


def _fail(message: str, code: int = 1) -> NoReturn:
    err.print(f"[red]error:[/] {message}")
    raise typer.Exit(code=code)


def _version_callback(value: bool) -> None:
    if value:
        console.print(__version__)
        raise typer.Exit()


def _print_ctx_help(ctx: typer.Context) -> None:
    target = ctx.parent if ctx.parent is not None else ctx
    console.print(target.get_help())


def _topic_help(ctx: typer.Context, *tokens: str | None) -> bool:
    for token in tokens:
        if token is None:
            continue
        if token.strip().lower() == "help":
            console.print(ctx.get_help())
            return True
        return False
    return False


def _add_help_command(group: typer.Typer) -> None:
    @group.command("help", help="Show help for this command.")
    def _help_cmd(ctx: typer.Context) -> None:
        _print_ctx_help(ctx)

    _ = _help_cmd


def _resolve_doc(root: Path, token: str, *, label: str = "RFC") -> Document:
    try:
        return resolve_doc_token(root, token)
    except (LookupError, ValueError) as exc:
        _fail(f"invalid {label} '{token}': {exc}")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-V",
            help="Show version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    _ = version
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


@app.command("help")
def help_cmd(
    ctx: typer.Context,
    command: Annotated[
        str | None,
        typer.Argument(help="Command to explain (e.g. init, new)."),
    ] = None,
    subcommand: Annotated[
        str | None,
        typer.Argument(help="Nested subcommand (e.g. idea)."),
    ] = None,
) -> None:
    """Show help for rfcman or a specific command."""
    root = ctx.find_root()
    if command is None:
        console.print(root.get_help())
        return

    main_cmd = root.command
    get_command = getattr(main_cmd, "get_command", None)
    if get_command is None:
        _fail(f"unknown command '{command}'")
    cmd = get_command(root, command)
    if cmd is None:
        _fail(f"unknown command '{command}'")

    with typer.Context(cmd, info_name=command, parent=root) as cmd_ctx:
        if subcommand is None:
            console.print(cmd_ctx.get_help())
            return
        nested_get = getattr(cmd, "get_command", None)
        if nested_get is None:
            _fail(f"'{command}' has no subcommand '{subcommand}'")
        nested = nested_get(cmd_ctx, subcommand)
        if nested is None:
            _fail(f"unknown subcommand '{command} {subcommand}'")
        with typer.Context(nested, info_name=subcommand, parent=cmd_ctx) as nested_ctx:
            console.print(nested_ctx.get_help())


@init_app.callback(invoke_without_command=True)
def init_cmd(
    ctx: typer.Context,
    path: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="RFC tree root (default: ./rfcs)."),
    ] = None,
) -> None:
    """Create an RFC tree and dump editable body templates."""
    if ctx.invoked_subcommand is not None:
        return
    command_root = Path.cwd().resolve()
    root = path.expanduser().resolve() if path is not None else default_rfcs_path()
    if root.exists() and any(root.iterdir()) and not (root / ".rfcman").exists():
        _fail(f"refusing to init into non-empty directory: {root}")
    ensure_layout(root)
    dump_user_templates(root)
    project = write_project_file(command_root, root)
    console.print(f"[green]initialized[/] {root}")
    console.print(f"  project: {project}")
    console.print("  stages: ideas research proposed accepted rejected superseded")
    console.print("  templates: _tpls/ (editable body templates)")


@list_app.callback(invoke_without_command=True)
def list_cmd(
    ctx: typer.Context,
    stage: Annotated[
        str | None,
        typer.Argument(
            help="Optional stage filter (ideas, research, proposed, ...).",
            autocompletion=complete_list_stage,
        ),
    ] = None,
    path: PathOption = None,
) -> None:
    """List RFCs as one-line summaries."""
    if ctx.invoked_subcommand is not None:
        return
    if _topic_help(ctx, stage):
        return
    root = _root_or_exit(path)
    if stage is None:
        docs = iter_documents(root)
    else:
        key = stage.lower().strip()
        if key not in LIST_ALIASES:
            _fail(f"unknown stage '{stage}'; choose from {', '.join(sorted(LIST_ALIASES))}")
        docs = documents_in_stage(root, LIST_ALIASES[key])
    if not docs:
        console.print("[dim]no RFCs found[/]")
        return
    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("Ref", style="cyan")
    table.add_column("Stage")
    table.add_column("Title")
    table.add_column("Date")
    table.add_column("Summary", overflow="ellipsis")
    for doc in sorted(docs, key=lambda d: d.path.stem):
        summary = " ".join(doc.summary.split())
        table.add_row(
            doc.user_ref,
            stage_badge(doc.meta.type),
            doc.meta.title,
            doc.meta.created.isoformat(),
            summary,
        )
    console.print(table)


@describe_app.callback(invoke_without_command=True)
def describe_cmd(
    ctx: typer.Context,
    ref: Annotated[
        str | None,
        typer.Argument(
            help="RFC ref (Stage-filename, e.g. Idea-new-idea).",
            autocompletion=complete_rfc_id,
        ),
    ] = None,
    path: PathOption = None,
) -> None:
    """Show an RFC summary and reference tree."""
    if ctx.invoked_subcommand is not None:
        return
    if _topic_help(ctx, ref):
        return
    if ref is None:
        _fail("missing RFC ref; try `rfcman describe help`")
    root = _root_or_exit(path)
    doc = _resolve_doc(root, ref)
    if doc.meta.type == Stage.IDEA:
        print_idea_description(console, root, doc)
    else:
        print_describe_tree(console, root, doc)


@idea_app.callback(invoke_without_command=True)
def new_idea_cmd(
    ctx: typer.Context,
    name: Annotated[str | None, typer.Argument(help="Idea title.")] = None,
    path: PathOption = None,
) -> None:
    """Create a new idea RFC."""
    if ctx.invoked_subcommand is not None:
        return
    if _topic_help(ctx, name):
        return
    if name is None:
        _fail("missing idea name; try `rfcman new idea help`")
    root = _root_or_exit(path)
    title = name.strip()
    if not title:
        _fail("name must not be empty")
    doc = create_document(root, stage=Stage.IDEA, title=title)
    console.print(f"[green]created[/] {doc.user_ref} → {doc.path}")


@upgrade_app.callback(invoke_without_command=True)
def upgrade_cmd(
    ctx: typer.Context,
    ref: Annotated[
        str | None,
        typer.Argument(
            help="RFC ref to advance (Stage-filename, e.g. Idea-new-idea).",
            autocompletion=complete_upgradeable_id,
        ),
    ] = None,
    path: PathOption = None,
) -> None:
    """Advance an RFC to the next lifecycle stage."""
    if ctx.invoked_subcommand is not None:
        return
    if _topic_help(ctx, ref):
        return
    if ref is None:
        _fail("missing RFC ref; try `rfcman upgrade help`")
    root = _root_or_exit(path)
    doc = _resolve_doc(root, ref)
    used = upgraded_source_ids(root)
    if doc.meta.id in used:
        _fail(f"{doc.user_ref} has already been upgraded")

    stage = doc.meta.type
    if stage == Stage.IDEA:
        try:
            created = upgrade_to(root, doc, Stage.RESEARCH, used=used)
        except ValueError as exc:
            _fail(str(exc))
        _ok_upgrade(doc, created)
    elif stage == Stage.RESEARCH:
        try:
            created = upgrade_to(root, doc, Stage.PROPOSED, used=used)
        except ValueError as exc:
            _fail(str(exc))
        _ok_upgrade(doc, created)
    elif stage == Stage.PROPOSED:
        choice = questionary.select(
            "Outcome:",
            choices=["Accept", "Reject"],
        ).ask()
        if choice is None:
            raise typer.Exit(code=1)
        target = Stage.ACCEPTED if choice == "Accept" else Stage.REJECTED
        try:
            created = upgrade_to(root, doc, target, used=used)
        except ValueError as exc:
            _fail(str(exc))
        _ok_upgrade(doc, created)
        if target == Stage.ACCEPTED:
            _maybe_supersede_prompt(root, created.meta.id)
    elif stage == Stage.ACCEPTED:
        _upgrade_accepted(root, doc)
    else:
        _fail(f"{doc.user_ref} cannot be upgraded further")


def _ok_upgrade(source: Document, created: Document) -> None:
    console.print(f"[green]upgraded[/] {source.user_ref} → {created.user_ref}")
    console.print(f"  {created.path}")


def _upgrade_accepted(root: Path, doc: Document) -> None:
    do_it = questionary.confirm(
        f"Supersede {doc.user_ref}?",
        default=True,
    ).ask()
    if do_it is None:
        raise typer.Exit(code=1)
    if not do_it:
        _fail("upgrade cancelled")
    replacement = _fuzzy_pick_accepted(root, exclude=doc.meta.id)
    old_doc, new_doc = supersede(root, doc.meta.id, replacement)
    console.print(f"[green]superseded[/] {old_doc.user_ref} → {new_doc.user_ref}")


def _maybe_supersede_prompt(root: Path, new_accepted_id: str) -> None:
    accepted = list_accepted_choices(root, exclude=new_accepted_id)
    if not accepted:
        return
    do_it = questionary.confirm(
        "Does this supersede an existing accepted RFC?",
        default=False,
    ).ask()
    if not do_it:
        return
    old_id = _fuzzy_pick_accepted(root, docs=accepted)
    old_doc, new_doc = supersede(root, old_id, new_accepted_id)
    console.print(f"[green]superseded[/] {old_doc.user_ref} → {new_doc.user_ref}")


def _fuzzy_pick_accepted(
    root: Path,
    *,
    exclude: str | None = None,
    docs: list[Document] | None = None,
) -> str:
    choices = docs if docs is not None else list_accepted_choices(root, exclude=exclude)
    if not choices:
        _fail("no accepted RFCs available to select")
    labels = {f"{d.user_ref}: {d.meta.title}": d.meta.id for d in choices}
    picked = questionary.autocomplete(
        "Select accepted RFC (type to filter):",
        choices=list(labels.keys()),
        match_middle=True,
    ).ask()
    if picked is None or picked not in labels:
        _fail("no selection made")
    return labels[picked]


@supersede_app.callback(invoke_without_command=True)
def supersede_cmd(
    ctx: typer.Context,
    old: Annotated[
        str | None,
        typer.Argument(
            help="Accepted RFC being replaced (Stage-filename).",
            autocompletion=complete_accepted_id,
        ),
    ] = None,
    new: Annotated[
        str | None,
        typer.Argument(
            help="Accepted RFC that replaces it (Stage-filename).",
            autocompletion=complete_accepted_id,
        ),
    ] = None,
    path: PathOption = None,
) -> None:
    """Mark an accepted RFC as superseded by another accepted RFC."""
    if ctx.invoked_subcommand is not None:
        return
    if _topic_help(ctx, old):
        return
    if old is None or new is None:
        _fail("usage: rfcman supersede <old> <new>; try `rfcman supersede help`")
    root = _root_or_exit(path)
    old_doc = _resolve_doc(root, old, label="old RFC")
    new_doc_target = _resolve_doc(root, new, label="new RFC")
    try:
        old_doc, new_doc = supersede(root, old_doc.meta.id, new_doc_target.meta.id)
    except (LookupError, ValueError) as exc:
        _fail(str(exc))
    console.print(f"[green]superseded[/] {old_doc.user_ref} → {new_doc.user_ref}")


@check_app.callback(invoke_without_command=True)
def check_cmd(ctx: typer.Context, path: PathOption = None) -> None:
    """Validate links and structure across the RFC tree."""
    if ctx.invoked_subcommand is not None:
        return
    root = _root_or_exit(path)
    issues = check_tree(root)
    if not issues:
        console.print("[green]ok[/] RFC tree is consistent")
        return
    for issue in issues:
        loc = f" ({issue.path})" if issue.path else ""
        err.print(f"[red]{issue.code}[/]: {issue.message}{loc}")
    raise typer.Exit(code=1)


for _group in (init_app, check_app, new_app):
    _add_help_command(_group)
