from __future__ import annotations

from typer.testing import CliRunner

from rfcman.cli import app

runner = CliRunner()


def test_bare_invocation_shows_help() -> None:
    result = runner.invoke(app, [])
    assert result.exit_code == 0, result.output
    assert "init" in result.output
    assert "╭─ Error" not in result.output
    assert "Try 'rfcman -h' for help" not in result.output


def test_top_level_help() -> None:
    result = runner.invoke(app, ["help"])
    assert result.exit_code == 0, result.output
    assert "init" in result.output
    assert "Elegant RFC" in result.output or "lifecycle" in result.output.lower()
    assert "BigTalk" in result.output


def test_help_for_command() -> None:
    result = runner.invoke(app, ["help", "init"])
    assert result.exit_code == 0, result.output
    assert "--path" in result.output or "-p" in result.output


def test_help_for_nested() -> None:
    result = runner.invoke(app, ["help", "new", "idea"])
    assert result.exit_code == 0, result.output
    assert "idea" in result.output.lower() or "title" in result.output.lower()


def test_command_help_subcommand() -> None:
    for args in (
        ["init", "help"],
        ["list", "help"],
        ["describe", "help"],
        ["upgrade", "help"],
        ["supersede", "help"],
        ["check", "help"],
        ["new", "help"],
        ["new", "idea", "help"],
    ):
        result = runner.invoke(app, list(args))
        assert result.exit_code == 0, (args, result.output)
        assert "Usage" in result.output or "usage" in result.output.lower()


def test_help_unknown_command() -> None:
    result = runner.invoke(app, ["help", "nope"])
    assert result.exit_code == 1
