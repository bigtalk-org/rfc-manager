from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rfcman.constants import MARKER_FILE, STAGE_DIRS, STATE_DIR, Stage
from rfcman.store import load_indexes, resolve_in_indexes


@dataclass(frozen=True)
class CheckIssue:
    code: str
    message: str
    path: Path | None = None


def check_tree(root: Path) -> list[CheckIssue]:
    issues: list[CheckIssue] = []

    for dirname in STAGE_DIRS.values():
        if not (root / dirname).is_dir():
            issues.append(CheckIssue("missing_dir", f"missing stage directory: {dirname}"))

    marker = root / STATE_DIR / MARKER_FILE
    if not marker.is_file():
        issues.append(CheckIssue("missing_marker", f"missing marker file: {marker}"))

    try:
        docs, by_id, by_stage_stem = load_indexes(root)
    except ValueError as exc:
        issues.append(CheckIssue("duplicate_id", str(exc)))
        return issues

    for doc in docs:
        expected_dir = STAGE_DIRS[doc.meta.type]
        if doc.path.parent.name != expected_dir:
            issues.append(
                CheckIssue(
                    "stage_mismatch",
                    (
                        f"RFC {doc.user_ref} type {doc.meta.type.value} "
                        f"lives in {doc.path.parent.name}/"
                    ),
                    doc.path,
                )
            )

        if doc.meta.references:
            try:
                resolve_in_indexes(doc.meta.references, by_id=by_id, by_stage_stem=by_stage_stem)
            except (LookupError, ValueError) as exc:
                issues.append(CheckIssue("dangling_reference", str(exc), doc.path))

        for related_id in doc.meta.related:
            if related_id not in by_id:
                issues.append(
                    CheckIssue(
                        "dangling_related",
                        f"RFC {doc.user_ref} related entry {related_id} does not exist",
                        doc.path,
                    )
                )

        if doc.meta.supersedes is not None and doc.meta.supersedes not in by_id:
            issues.append(
                CheckIssue(
                    "dangling_supersedes",
                    f"RFC {doc.user_ref} supersedes missing id {doc.meta.supersedes}",
                    doc.path,
                )
            )

        if doc.meta.superseded_by is not None:
            if doc.meta.superseded_by not in by_id:
                issues.append(
                    CheckIssue(
                        "dangling_superseded_by",
                        f"RFC {doc.user_ref} superseded_by missing id {doc.meta.superseded_by}",
                        doc.path,
                    )
                )
            elif doc.meta.type != Stage.SUPERSEDED:
                issues.append(
                    CheckIssue(
                        "superseded_type",
                        f"RFC {doc.user_ref} has superseded_by but type is {doc.meta.type.value}",
                        doc.path,
                    )
                )

    return issues
