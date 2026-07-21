# rfcman developer workflows
#
#   make push     — push commits (and any local tags) to origin
#   make release  — bump version, update CHANGELOG, tag, push → PyPI via CI

# Prefer the local venv when present.
PYTHON ?= $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)
CZ     ?= $(PYTHON) -m commitizen
export PATH := $(CURDIR)/.venv/bin:$(PATH)

.PHONY: help push release check test lint

help:
	@echo "Targets:"
	@echo "  make push     Push the current branch and tags to origin"
	@echo "  make release  Run checks, bump version + CHANGELOG, tag, push (PyPI via CI)"
	@echo "  make check    Lint, typecheck, and test"
	@echo "  make lint     Ruff + mypy only"
	@echo "  make test     Pytest only"

lint:
	ruff check src tests
	ruff format --check src tests
	mypy

test:
	pytest

check: lint test

push:
	@test -z "$$(git status --porcelain)" || { \
		echo "error: working tree is dirty; commit or stash first"; \
		exit 1; \
	}
	git push origin HEAD
	git push origin --tags

# Bumps SemVer from conventional commits, rewrites CHANGELOG.md, creates v* tag.
# Pushing the tag is the only release path — GitHub Actions publishes to PyPI
# via Trusted Publishing (.github/workflows/publish.yml). Do not twine upload locally.
release: check
	@test -z "$$(git status --porcelain)" || { \
		echo "error: working tree is dirty; commit or stash first"; \
		exit 1; \
	}
	$(CZ) bump --yes
	git push origin HEAD
	git push origin --tags
	@echo
	@echo "Release pushed. Watch Trusted Publishing here:"
	@echo "  https://github.com/bigtalk-org/rfc-manager/actions/workflows/publish.yml"
	@echo "  https://pypi.org/project/rfcman/"
