from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
from typer.testing import CliRunner

from rfcman.cli import app
from rfcman.constants import Stage
from rfcman.document import read_document
from rfcman.lifecycle import create_document, supersede, upgrade_to
from rfcman.store import dump_user_templates, find_by_id
from rfcman.workspace import ensure_layout

runner = CliRunner()


@pytest.fixture
def rfcs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "rfcs"
    ensure_layout(root)
    dump_user_templates(root)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")
    return root


def test_init_creates_layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0, result.output
    root = tmp_path / "rfcs"
    assert (root / "ideas").is_dir()
    assert (root / "_tpls" / "idea.md.j2").is_file()
    assert (tmp_path / "rfcman.yml").is_file()


def test_new_idea_and_list(rfcs: Path) -> None:
    result = runner.invoke(app, ["new", "idea", "Typed Channels"])
    assert result.exit_code == 0, result.output
    assert "Idea-typed-channels" in result.output
    docs = list((rfcs / "ideas").glob("*.md"))
    assert len(docs) == 1
    doc = read_document(docs[0])
    UUID(doc.meta.id)
    assert doc.meta.type == Stage.IDEA
    assert doc.meta.title == "Typed Channels"
    assert doc.path.name == "typed-channels.md"
    assert doc.user_ref == "Idea-typed-channels"

    listed = runner.invoke(app, ["list", "ideas"])
    assert listed.exit_code == 0
    assert "Typed Channels" in listed.output
    assert "Idea-typed-channels" in listed.output


def test_upgrade_chain(rfcs: Path) -> None:
    idea = create_document(rfcs, stage=Stage.IDEA, title="Lifecycle")
    research = upgrade_to(rfcs, idea, Stage.RESEARCH)
    assert research.meta.references == "Idea-lifecycle"
    proposed = upgrade_to(rfcs, research, Stage.PROPOSED)
    assert proposed.meta.references == "Research-lifecycle"
    accepted = upgrade_to(rfcs, proposed, Stage.ACCEPTED)
    assert accepted.meta.references == "Proposed-lifecycle"
    UUID(accepted.meta.id)
    assert accepted.user_ref == "Accepted-lifecycle"

    check = runner.invoke(app, ["check"])
    assert check.exit_code == 0, check.output
    assert "documents" in check.output


def test_describe_idea(rfcs: Path) -> None:
    create_document(rfcs, stage=Stage.IDEA, title="Describe Me")
    result = runner.invoke(app, ["describe", "Idea-describe-me"])
    assert result.exit_code == 0, result.output
    assert "Describe Me" in result.output


def test_supersede(rfcs: Path) -> None:
    a = create_document(rfcs, stage=Stage.ACCEPTED, title="Old Design")
    b = create_document(rfcs, stage=Stage.ACCEPTED, title="New Design")
    old, new = supersede(rfcs, a.meta.id, b.meta.id)
    assert old.meta.type == Stage.SUPERSEDED
    assert old.meta.superseded_by == b.meta.id
    assert new.meta.supersedes == a.meta.id
    assert (rfcs / "superseded" / old.path.name).exists()
    assert find_by_id(rfcs, a.meta.id).meta.type == Stage.SUPERSEDED
    assert "Accepted-new-design" in old.body
    assert "## Superseded By" in old.body


def test_check_dangling_reference(rfcs: Path) -> None:
    create_document(
        rfcs,
        stage=Stage.RESEARCH,
        title="Broken",
        references="Idea-missing-doc",
    )
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 1
    assert "dangling_reference" in result.output


def test_check_empty_tree(rfcs: Path) -> None:
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 0, result.output
    assert "empty" in result.output.lower()
    assert "consistent" not in result.output.lower()


def test_unique_ids(rfcs: Path) -> None:
    a = create_document(rfcs, stage=Stage.IDEA, title="One")
    b = create_document(rfcs, stage=Stage.IDEA, title="Two")
    assert a.meta.id != b.meta.id
    UUID(a.meta.id)
    UUID(b.meta.id)
