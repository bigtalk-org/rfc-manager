from __future__ import annotations

from datetime import date

from rfcman.constants import Stage
from rfcman.document import FrontMatter, extract_summary, render_document, split_frontmatter


def test_roundtrip_frontmatter() -> None:
    meta = FrontMatter(
        id="550e8400-e29b-41d4-a716-446655440000",
        title="Hello",
        type=Stage.IDEA,
        author="Ada Lovelace <ada@example.com>",
        created=date(2026, 1, 2),
        updated=date(2026, 1, 3),
        references=None,
        related=["11111111-1111-1111-1111-111111111111"],
    )
    text = render_document(meta, "# Hello\n\n## Summary\n\nNice idea.\n")
    data, body = split_frontmatter(text)
    restored = FrontMatter.from_dict(data)
    assert restored.id == "550e8400-e29b-41d4-a716-446655440000"
    assert restored.author.startswith("Ada")
    assert "Nice idea" in extract_summary(body)
