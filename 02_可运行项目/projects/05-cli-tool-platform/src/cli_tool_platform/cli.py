"""CLI 工具平台环境检查入口（版本 0.2.0，Python 3.11+）。"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from cli_tool_platform.settings import ConfigurationError, configure_logging, load_settings

LOGGER = logging.getLogger(__name__)


def environment_summary() -> dict[str, str]:
    """返回便于诊断的解释器、版本和当前目录摘要。"""
    return {
        "executable": sys.executable,
        "python_version": sys.version.split()[0],
        "cwd": str(Path.cwd()),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="输出当前 CLI 工具平台的运行环境摘要。")
    parser.add_argument("--config", type=Path, help="可选、可信的 TOML 运行配置文件。")
    parser.add_argument("--json", action="store_true", help="以稳定 JSON 输出环境摘要。")
    parser.add_argument("--verbose", action="store_true", help="临时将应用日志级别提升为 DEBUG。")
    return parser


def main(argv: list[str] | None = None) -> int:
    """执行命令行入口，返回受控退出码。"""
    args = build_parser().parse_args(argv)
    try:
        settings = load_settings(config_path=args.config)
    except ConfigurationError as exc:
        logging.basicConfig(level=logging.ERROR, format="%(levelname)s %(message)s", force=True)
        LOGGER.error("配置被拒绝：%s", exc)
        return 2

    configure_logging(settings, verbose=args.verbose)
    summary = environment_summary()
    LOGGER.info("environment_summary_requested", extra={"app_name": settings.app_name})
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    else:
        for key, value in summary.items():
            print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
