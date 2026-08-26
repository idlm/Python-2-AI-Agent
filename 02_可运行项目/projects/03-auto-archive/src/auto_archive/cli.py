"""自动归档命令行入口（版本 0.2.0，Python 3.11+）。"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from auto_archive.core import (
    ArchiveInputError,
    execute_archive,
    load_config,
    plan_archive,
    write_manifest,
)

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="仅归档指定目录中的匹配文件；默认仅 Dry Run。")
    parser.add_argument("source", type=Path, help="要扫描的本地源目录（不递归）。")
    parser.add_argument("destination", type=Path, help="归档目标目录。")
    parser.add_argument("--apply", action="store_true", help="实际执行移动；默认仅 Dry Run。")
    parser.add_argument("--config", type=Path, help="仅含 suffix 字段的受控 JSON 配置。")
    parser.add_argument("--manifest", type=Path, help="可选的 UTF-8 JSON 操作清单路径。")
    parser.add_argument("--verbose", action="store_true", help="在标准错误输出 DEBUG 日志。")
    return parser


def configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        force=True,
    )


def main(argv: list[str] | None = None) -> int:
    """执行归档或 Dry Run；输入错误返回退出码 2。"""
    args = build_parser().parse_args(argv)
    configure_logging(args.verbose)
    try:
        suffix = load_config(args.config)["suffix"] if args.config else ".txt"
        actions = plan_archive(args.source, args.destination, suffix=suffix)
        completed = execute_archive(actions, dry_run=not args.apply)
        if args.manifest is not None:
            write_manifest(completed, args.manifest)
    except (ArchiveInputError, FileExistsError, FileNotFoundError) as exc:
        LOGGER.error("归档被拒绝：%s", exc)
        return 2

    moved_count = sum(item.moved for item in completed)
    print(f"计划数量：{len(completed)}；实际移动：{moved_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
