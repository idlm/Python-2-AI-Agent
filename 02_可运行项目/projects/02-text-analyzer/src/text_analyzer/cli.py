"""文本分析命令行入口（版本 0.2.0，Python 3.11+）。"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from text_analyzer.core import TextInputError, analyze_text, format_report, read_text_file

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="统计文本的字符数、词数和行数。")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", help="要分析的直接文本。")
    source.add_argument("--file", type=Path, help="要以 UTF-8 读取的本地文本文件。")
    parser.add_argument("--json", action="store_true", help="以稳定 JSON 输出统计结果。")
    parser.add_argument("--verbose", action="store_true", help="在标准错误输出 DEBUG 诊断日志。")
    return parser


def configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        force=True,
    )


def main(argv: list[str] | None = None) -> int:
    """执行命令行工具；输入错误返回退出码 2。"""
    args = build_parser().parse_args(argv)
    configure_logging(args.verbose)
    try:
        text = args.text if args.text is not None else read_text_file(args.file)
        assert text is not None
        report = analyze_text(text)
    except TextInputError as exc:
        LOGGER.error("输入被拒绝：%s", exc)
        return 2

    LOGGER.info(
        "text_analyzed chars=%s words=%s lines=%s",
        report["characters"],
        report["words"],
        report["lines"],
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(format_report(text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
