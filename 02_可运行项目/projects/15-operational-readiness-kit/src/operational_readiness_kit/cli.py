"""模块 15 的受控命令行入口；默认不执行部署、健康检查或恢复。"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .evaluation import (
    StaticReadinessResult,
    run_static_readiness_cases,
    write_public_readiness_report,
)

_REPORT_NAME = "operational-readiness-report.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="模块 15 无副作用运行准备合同工具包")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--status", action="store_true", help="输出默认无执行范围")
    mode.add_argument("--run-static-readiness", action="store_true", help="回放固定公开静态夹具")
    mode.add_argument("--write-static-report", action="store_true", help="写入固定名称的无正文报告")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.run_static_readiness:
        results = run_static_readiness_cases(_fixture_path())
        print(json.dumps(_summary(results), sort_keys=True))
        return 0
    if arguments.write_static_report:
        results = run_static_readiness_cases(_fixture_path())
        output_path = Path.cwd() / _REPORT_NAME
        write_public_readiness_report(results, output_path)
        summary: dict[str, int | str] = dict(_summary(results))
        summary["report_written"] = output_path.name
        print(json.dumps(summary, sort_keys=True))
        return 0
    print(
        json.dumps(
            {
                "default_mode": "no_execution",
                "not_supported": [
                    "environment_reading",
                    "secret_values",
                    "health_servers",
                    "network_listeners",
                    "cloud_deployment",
                    "backup_or_restore",
                    "model_or_tool_calls",
                ],
            },
            sort_keys=True,
        )
    )
    return 0


def _fixture_path() -> Path:
    return Path(__file__).parents[2] / "tests" / "fixtures" / "readiness_cases.json"


def _summary(results: tuple[StaticReadinessResult, ...]) -> dict[str, int]:
    passed_count = sum(result.passed for result in results)
    return {"case_count": len(results), "passed_count": passed_count}


if __name__ == "__main__":
    raise SystemExit(main())
