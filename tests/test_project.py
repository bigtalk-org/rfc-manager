from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from rfcman.cli import app
from rfcman.constants import PROJECT_FILE
from rfcman.workspace import find_root

runner = CliRunner()


def test_init_writes_project_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0, result.output
    project = tmp_path / PROJECT_FILE
    assert project.is_file()
    data = yaml.safe_load(project.read_text(encoding="utf-8"))
    assert data["location"] == "rfcs"
    assert "created" in data
    assert "author" in data
    assert "<" in data["author"]
    assert find_root() == (tmp_path / "rfcs").resolve()


def test_custom_path_discovered_via_yml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    tree = tmp_path / "elsewhere" / "docs"
    result = runner.invoke(app, ["init", "--path", str(tree)])
    assert result.exit_code == 0, result.output
    assert (tree / "ideas").is_dir()
    project = tmp_path / PROJECT_FILE
    data = yaml.safe_load(project.read_text(encoding="utf-8"))
    assert data["location"] == "elsewhere/docs"

    created = runner.invoke(app, ["new", "idea", "From Yml"])
    assert created.exit_code == 0, created.output
    assert list((tree / "ideas").glob("*.md"))

    listed = runner.invoke(app, ["list"])
    assert listed.exit_code == 0, listed.output
    assert "From Yml" in listed.output


def test_path_flag_overrides_yml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    primary = tmp_path / "primary"
    secondary = tmp_path / "secondary"

    class _Confirm:
        def ask(self) -> bool:
            return True

    monkeypatch.setattr(
        "rfcman.cli.questionary.confirm",
        lambda *a, **k: _Confirm(),
    )
    assert runner.invoke(app, ["init", "--path", str(primary)]).exit_code == 0
    assert runner.invoke(app, ["init", "--path", str(secondary)]).exit_code == 0
    # last init rewrote rfcman.yml → secondary; override back to primary
    result = runner.invoke(
        app,
        ["new", "idea", "Override", "--path", str(primary)],
    )
    assert result.exit_code == 0, result.output
    assert list((primary / "ideas").glob("*.md"))
    assert not list((secondary / "ideas").glob("*.md"))


def test_init_prompts_before_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["init"]).exit_code == 0

    class _ConfirmNo:
        def ask(self) -> bool:
            return False

    monkeypatch.setattr(
        "rfcman.cli.questionary.confirm",
        lambda *a, **k: _ConfirmNo(),
    )
    cancelled = runner.invoke(app, ["init"])
    assert cancelled.exit_code == 1
    assert "warning" in cancelled.output.lower() or "existing" in cancelled.output.lower()
    assert "cancelled" in cancelled.output.lower()

    class _ConfirmYes:
        def ask(self) -> bool:
            return True

    monkeypatch.setattr(
        "rfcman.cli.questionary.confirm",
        lambda *a, **k: _ConfirmYes(),
    )
    ok = runner.invoke(app, ["init"])
    assert ok.exit_code == 0, ok.output
    assert "initialized" in ok.output


def test_yml_author_used_for_new_docs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["init"]).exit_code == 0
    project = tmp_path / PROJECT_FILE
    data = yaml.safe_load(project.read_text(encoding="utf-8"))
    data["author"] = "Ada Lovelace <ada@example.com>"
    project.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    result = runner.invoke(app, ["new", "idea", "Authored"])
    assert result.exit_code == 0, result.output
    doc_path = next((tmp_path / "rfcs" / "ideas").glob("*.md"))
    text = doc_path.read_text(encoding="utf-8")
    assert "Ada Lovelace <ada@example.com>" in text
