"""兼容入口：请在新代码中使用 `course-auto-archive` 或 `auto_archive.cli`。"""

from auto_archive.cli import build_parser, main

__all__ = ["build_parser", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
