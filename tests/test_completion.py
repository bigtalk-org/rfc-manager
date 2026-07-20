from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from rfcman.cli import app
from rfcman.completion import (
    complete_accepted_id,
    complete_list_stage,
    complete_rfc_id,
    complete_upgradeable_id,
)
from rfcman.constants import Stage
from rfcman.lifecycle import create_document, upgrade_to
from rfcman.store import dump_user_templates
from rfcman.workspace import ensure_layout, write_project_file

runner = CliRunner()


@pytest.fixture
def rfcs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "rfcs"
    ensure_layout(root)
    dump_user_templates(root)
    write_project_file(tmp_path, root)
    monkeypatch.chdir(tmp_path)
    return root


def _vals(items: list[object]) -> list[str]:
    return [i.value for i in items]  # type: ignore[attr-defined]


def test_complete_shows_stage_stem_refs(rfcs: Path) -> None:
    create_document(rfcs, stage=Stage.IDEA, title="Alpha Channels")
    create_document(rfcs, stage=Stage.IDEA, title="Beta Buffer")
    assert _vals(complete_rfc_id(None, None, "")) == [
        "Idea-alpha-channels",
        "Idea-beta-buffer",
    ]
    assert _vals(complete_rfc_id(None, None, "Idea")) == [
        "Idea-alpha-channels",
        "Idea-beta-buffer",
    ]
    assert _vals(complete_rfc_id(None, None, "Ide")) == [
        "Idea-alpha-channels",
        "Idea-beta-buffer",
    ]
    assert _vals(complete_rfc_id(None, None, "alpha")) == ["Idea-alpha-channels"]
    assert _vals(complete_rfc_id(None, None, "Buf")) == ["Idea-beta-buffer"]


def test_complete_filters_irrelevant_prefixes(rfcs: Path) -> None:
    create_document(rfcs, stage=Stage.IDEA, title="Alpha Channels")
    create_document(rfcs, stage=Stage.RESEARCH, title="Beta Study")
    create_document(rfcs, stage=Stage.ACCEPTED, title="Gamma Done")
    assert _vals(complete_rfc_id(None, None, "e")) == []
    assert _vals(complete_rfc_id(None, None, "Re")) == ["Research-beta-study"]
    assert _vals(complete_rfc_id(None, None, "Acc")) == ["Accepted-gamma-done"]
    assert _vals(complete_rfc_id(None, None, "Ide")) == ["Idea-alpha-channels"]
    assert _vals(complete_rfc_id(None, None, "Gam")) == ["Accepted-gamma-done"]
    assert _vals(complete_rfc_id(None, None, "Al")) == ["Idea-alpha-channels"]
    assert _vals(complete_rfc_id(None, None, "xyz")) == []


def test_complete_type_prefix_ignores_title_word(rfcs: Path) -> None:
    """Typing a stage prefix must not match other docs that share the word in the title."""
    create_document(rfcs, stage=Stage.IDEA, title="New Idea")
    create_document(rfcs, stage=Stage.RESEARCH, title="New Idea")
    assert _vals(complete_upgradeable_id(None, None, "Ide")) == ["Idea-new-idea"]
    assert _vals(complete_upgradeable_id(None, None, "New")) == [
        "Idea-new-idea",
        "Research-new-idea",
    ]


def test_complete_upgradeable_excludes_terminal(rfcs: Path) -> None:
    idea = create_document(rfcs, stage=Stage.IDEA, title="Keep")
    upgrade_to(rfcs, idea, Stage.RESEARCH)
    create_document(rfcs, stage=Stage.REJECTED, title="Dead")
    create_document(rfcs, stage=Stage.SUPERSEDED, title="Old")
    assert set(_vals(complete_upgradeable_id(None, None, ""))) == {"Research-keep"}


def test_complete_accepted_only(rfcs: Path) -> None:
    create_document(rfcs, stage=Stage.IDEA, title="Idea")
    create_document(rfcs, stage=Stage.ACCEPTED, title="Done")
    assert _vals(complete_accepted_id(None, None, "")) == ["Accepted-done"]


def test_complete_list_stage() -> None:
    assert [a for a, _ in complete_list_stage("idea")] == ["idea", "ideas"]


def test_upgrade_accepts_stage_stem_ref(rfcs: Path) -> None:
    create_document(rfcs, stage=Stage.IDEA, title="Typed")
    result = runner.invoke(app, ["upgrade", "Idea-typed"])
    assert result.exit_code == 0, result.output
    assert "Research-typed" in result.output


def test_upgrade_accepts_uuid(rfcs: Path) -> None:
    idea = create_document(rfcs, stage=Stage.IDEA, title="Bare")
    result = runner.invoke(app, ["upgrade", idea.meta.id])
    assert result.exit_code == 0, result.output
    assert "Research-bare" in result.output


def test_upgrade_rejects_mismatched_type(rfcs: Path) -> None:
    create_document(rfcs, stage=Stage.IDEA, title="Mismatch")
    result = runner.invoke(app, ["upgrade", "Research-mismatch"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower() or "does not match" in result.output


def test_upgrade_once_only(rfcs: Path) -> None:
    create_document(rfcs, stage=Stage.IDEA, title="Once")
    first = runner.invoke(app, ["upgrade", "Idea-once"])
    assert first.exit_code == 0, first.output
    second = runner.invoke(app, ["upgrade", "Idea-once"])
    assert second.exit_code == 1
    assert "already been upgraded" in second.output
    assert _vals(complete_upgradeable_id(None, None, "")) == ["Research-once"]
