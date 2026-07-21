# Changelog

All notable changes to this project will be documented in this file.

**rfcman** — a BigTalk utility.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.4] — 2026-07-21

### Fixed

- Bare `rfcman` shows help cleanly without an empty error panel

## [0.1.3] — 2026-07-21

### Fixed

- Import failure on older Typer versions (`typer._click` private path)

## [0.1.2] — 2026-07-21

### Fixed

- README logo sizing for GitHub and PyPI via absolute URL and width

## [0.1.1] — 2026-07-21

### Fixed

- README logo uses an absolute GitHub URL so it renders on PyPI

## [0.1.0] — 2026-07-21

### Added

- Initial `rfcman` CLI: `init`, `new idea`, `list`, `describe`, `upgrade`, `supersede`, `check`
- UUID document ids with user-facing `Stage-filename` refs (e.g. `Idea-typed-channels`)
- Editable body templates under `_tpls/` with locked frontmatter owned by the tool
- Shell completion support via Typer
- GitHub Actions CI for tests, Ruff, mypy, markdownlint, and commit message linting
