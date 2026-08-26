"""将术语表中尚未出现在中英索引的条目附加为补充导航。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]
GLOSSARY = ROOT / "records" / "glossary.md"
INDEX = ROOT / "records" / "bilingual_index.md"
MARKER = "## 完整术语补充导航"


def parse_glossary(path: Path) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if len(cells) != 5 or cells[0] == "中文主名":
            continue
        chinese, english, _definition, first_chapter, _avoid = cells
        rows.append((chinese, english, first_chapter))
    return rows


def main() -> None:
    index = INDEX.read_text(encoding="utf-8")
    if MARKER in index:
        raise RuntimeError("supplemental navigation already exists")

    missing = [
        row for row in parse_glossary(GLOSSARY) if row[0] not in index
    ]
    lines = [
        "",
        MARKER,
        "",
        "下表补齐中英索引的长尾术语。定义、禁止混用和完整上下文仍以"
        " `records/glossary.md` 为准；本表仅提供从中文术语到英文名称和首现章节的反向定位。",
        "",
        "| 中文术语 | English / 缩写 | 首现章节 |",
        "|---|---|---|",
    ]
    lines.extend(f"| {cn} | {en} | {chapter} |" for cn, en, chapter in missing)
    lines.append("")
    INDEX.write_text(index.rstrip() + "\n" + "\n".join(lines), encoding="utf-8")
    print(f"appended {len(missing)} glossary navigation rows")


if __name__ == "__main__":
    main()
