from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Final


class Stage(StrEnum):
    IDEA = "Idea"
    RESEARCH = "Research"
    PROPOSED = "Proposed"
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"
    SUPERSEDED = "Superseded"


STAGE_DIRS: Final[dict[Stage, str]] = {
    Stage.IDEA: "ideas",
    Stage.RESEARCH: "research",
    Stage.PROPOSED: "proposed",
    Stage.ACCEPTED: "accepted",
    Stage.REJECTED: "rejected",
    Stage.SUPERSEDED: "superseded",
}

LIST_ALIASES: Final[dict[str, Stage]] = {
    "idea": Stage.IDEA,
    "ideas": Stage.IDEA,
    "research": Stage.RESEARCH,
    "researches": Stage.RESEARCH,
    "proposed": Stage.PROPOSED,
    "accepted": Stage.ACCEPTED,
    "rejected": Stage.REJECTED,
    "superseded": Stage.SUPERSEDED,
}

# Longest first so "Superseded" wins over shorter prefixes.
STAGE_PREFIXES: Final[tuple[Stage, ...]] = tuple(
    sorted(Stage, key=lambda s: len(s.value), reverse=True)
)

TPLS_DIR: Final[str] = "_tpls"
STATE_DIR: Final[str] = ".rfcman"
MARKER_FILE: Final[str] = "config.yaml"
PROJECT_FILE: Final[str] = "rfcman.yml"


def stage_dir(root: Path, stage: Stage) -> Path:
    return root / STAGE_DIRS[stage]
