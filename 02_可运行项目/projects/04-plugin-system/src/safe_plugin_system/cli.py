"""安全插件系统的受控命令行入口（版本 0.3.0）。"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .core import JsonlAuditLog, PluginError, load_registry_from_json


def build_parser() -> argparse.ArgumentParser:
    """构造不接受任意模块或命令参数的最小 CLI。"""
    parser = argparse.ArgumentParser(
        description="仅执行配置中允许的内置文本插件；不会动态导入配置指定的代码。"
    )
    parser.add_argument("--config", type=Path, required=True, help="UTF-8 JSON 插件配置文件。")
    parser.add_argument("--list", action="store_true", help="列出允许调用的插件名称。")
    parser.add_argument("--plugin", help="要执行的已注册插件名称。")
    parser.add_argument("--text", help="要转换的文本；不会写入审计日志。")
    parser.add_argument(
        "--audit-log", type=Path, help="可选 JSON Lines 审计日志路径，只记录元数据。"
    )
    parser.add_argument("--verbose", action="store_true", help="输出 INFO 级别运行日志到标准错误。")
    return parser


def configure_logging(verbose: bool) -> None:
    """只为 CLI 配置日志；库本身不更改应用程序日志策略。"""
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )


def run(args: argparse.Namespace) -> int:
    """运行一次受控命令，并返回进程退出码。"""
    if args.list and (args.plugin is not None or args.text is not None):
        raise PluginError("--list 不能与 --plugin 或 --text 同时使用。")
    if not args.list and (args.plugin is None or args.text is None):
        raise PluginError("执行转换时必须同时提供 --plugin 和 --text，或单独使用 --list。")

    registry = load_registry_from_json(args.config)
    if args.list:
        for name in registry.names():
            print(name)
        return 0

    if args.audit_log is None:
        print(registry.apply(args.plugin, args.text))
        return 0

    with JsonlAuditLog(args.audit_log) as audit_log:
        print(registry.apply(args.plugin, args.text, audit_log=audit_log))
    return 0


def main(argv: list[str] | None = None) -> int:
    """解析参数并把可预期输入错误映射为退出码 2。"""
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)
    try:
        return run(args)
    except PluginError as exc:
        logging.getLogger(__name__).error("请求被拒绝：%s", exc)
        return 2
    except OSError as exc:
        logging.getLogger(__name__).error("文件操作失败：%s", exc)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
