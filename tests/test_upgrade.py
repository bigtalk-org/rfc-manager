from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from rfcman.cli import app
from rfcman.constants import Stage
from rfcman.lifecycle import create_document, upgrade_to
from rfcman.store import dump_user_templates
from rfcman.workspace import ensure_layout

runner = CliRunner()


@pytest.fixture
def rfcs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "rfcs"
    ensure_layout(root)
    dump_user_templates(root)
    monkeypatch.chdir(tmp_path)
    return root


def test_upgrade_idea_via_cli(rfcs: Path) -> None:
    create_document(rfcs, stage=Stage.IDEA, title="Up")
    result = runner.invoke(app, ["upgrade", "Idea-up"])
    assert result.exit_code == 0, result.output
    assert "Research-up" in result.output
    assert list((rfcs / "research").glob("*.md"))
    assert list((rfcs / "ideas").glob("*.md"))


def test_upgrade_proposed_accept(rfcs: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    idea = create_document(rfcs, stage=Stage.IDEA, title="Chain")
    research = upgrade_to(rfcs, idea, Stage.RESEARCH)
    proposed = upgrade_to(rfcs, research, Stage.PROPOSED)

    class _Select:
        def ask(self) -> str:
            return "Accept"

    class _Confirm:
        def ask(self) -> bool:
            return False

    monkeypatch.setattr(
        "rfcman.cli.questionary.select",
        lambda *a, **k: _Select(),
    )
    monkeypatch.setattr(
        "rfcman.cli.questionary.confirm",
        lambda *a, **k: _Confirm(),
    )
    result = runner.invoke(app, ["upgrade", proposed.user_ref])
    assert result.exit_code == 0, result.output
    assert "Accepted" in result.output


def test_upgrade_proposed_reject(rfcs: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    idea = create_document(rfcs, stage=Stage.IDEA, title="Nope")
    research = upgrade_to(rfcs, idea, Stage.RESEARCH)
    proposed = upgrade_to(rfcs, research, Stage.PROPOSED)

    class _Select:
        def ask(self) -> str:
            return "Reject"

    monkeypatch.setattr(
        "rfcman.cli.questionary.select",
        lambda *a, **k: _Select(),
    )
    result = runner.invoke(app, ["upgrade", proposed.user_ref])
    assert result.exit_code == 0, result.output
    assert "Rejected" in result.output


def test_describe_tree(rfcs: Path) -> None:
    idea = create_document(rfcs, stage=Stage.IDEA, title="Root Idea")
    research = upgrade_to(rfcs, idea, Stage.RESEARCH)
    result = runner.invoke(app, ["describe", research.user_ref])
    assert result.exit_code == 0, result.output
    assert "Research" in result.output or "Root Idea" in result.output


def test_supersede_cli(rfcs: Path) -> None:
    a = create_document(rfcs, stage=Stage.ACCEPTED, title="Old")
    b = create_document(rfcs, stage=Stage.ACCEPTED, title="New")
    result = runner.invoke(app, ["supersede", a.user_ref, b.user_ref])
    assert result.exit_code == 0, result.output
    assert "superseded" in result.output.lower()


def test_list_unknown_stage(rfcs: Path) -> None:
    result = runner.invoke(app, ["list", "nope"])
    assert result.exit_code == 1


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.4" in result.output


def test_init_custom_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    dest = tmp_path / "custom-rfcs"
    result = runner.invoke(app, ["init", "--path", str(dest)])
    assert result.exit_code == 0, result.output
    assert (dest / "ideas").is_dir()


def test_missing_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 1


def test_render_uses_user_template(rfcs: Path) -> None:
    tpl = rfcs / "_tpls" / "idea.md.j2"
    tpl.write_text("# {{ title }}\n\n## Summary\n\nCUSTOM BODY\n", encoding="utf-8")
    doc = create_document(rfcs, stage=Stage.IDEA, title="Custom")
    assert "CUSTOM BODY" in doc.body
