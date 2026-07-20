# rfcman

<img src="docs/assets/rfcman-logo.png" width="320" alt="Description">

**rfcman** — a BigTalk utility.

A fast, elegant CLI for managing RFC lifecycles.

Incubated for [BigTalk](https://github.com/bigtalk-org); usable for any project that needs structured proposal workflows.

## Install

```bash
pip install rfcman
```

Requires Python 3.12+.

## Quick start

```bash
rfcman init
rfcman new idea "Faster module loading"
rfcman list ideas
rfcman describe Idea-faster-module-loading
rfcman upgrade Idea-faster-module-loading
rfcman check
```

## Lifecycle

```text
Idea → Research → Proposed → Accepted
                           ↘ Rejected
Accepted → Superseded
```

- `upgrade` keeps the previous document and creates the next stage with a `references` link (`Idea-new-idea`, `Research-new-idea`, …).
- From **Proposed**, choose **Accept** or **Reject**.
- Accepting can optionally supersede an existing accepted RFC (type-to-filter picker).
- `rfcman supersede <old> <new>` does the same non-interactively.

Each document stores a UUID in frontmatter. CLI args, completions, and `references` use `Stage-filename` (e.g. `Idea-typed-channels` for `ideas/typed-channels.md`). Cross-links in `related` / `supersedes` / `superseded_by` store UUIDs so they survive renames and stage moves.

`rfcman init` writes `rfcman.yml` in the directory where you ran the command, recording the tree `location`, `created` date, and `author` (from `git config`). Later commands discover that file (walking up from cwd) unless you pass `--path` / `-p`. Change `author` in `rfcman.yml` to override the byline on new documents.

| Command | Purpose |
| --- | --- |
| `rfcman help [CMD]` | Show help for rfcman or a command |
| `rfcman init [-p PATH]` | Create an RFC tree (`./rfcs` by default) |
| `rfcman new idea NAME` | Create an idea (author from `rfcman.yml`, else git) |
| `rfcman list [STAGE]` | One-line listing |
| `rfcman describe REF` | Summary + reference tree (terminal hyperlinks) |
| `rfcman upgrade REF` | Advance to the next stage |
| `rfcman supersede OLD NEW` | Mark accepted OLD superseded by accepted NEW |
| `rfcman check` | Integrity check for links and layout |

Every command also accepts `help` (e.g. `rfcman init help`, `rfcman describe help`).

## Templates

`init` dumps editable **body** templates into `rfcs/_tpls/`. Frontmatter is owned by rfcman and is not dumped or overridable.

## Shell completions

```bash
rfcman --install-completion bash
rfcman --install-completion zsh
rfcman --install-completion fish
```

Or print a script to source yourself:

```bash
rfcman --show-completion bash > completions/rfcman.bash
```

Pre-generated scripts also live in [`completions/`](completions/).

After install, tab-complete:

- commands and options
- `list` stage names
- RFC refs for `describe`, `upgrade`, and `supersede` (match by stage, filename stem, or title)

## Development

```bash
python -m pip install -e ".[dev]"
ruff check .
ruff format .
mypy
pytest
```

Versioning and changelog use [Commitizen](https://commitizen-tools.github.io/commitizen/) (Conventional Commits):

```bash
cz bump
```

## License

Apache-2.0
