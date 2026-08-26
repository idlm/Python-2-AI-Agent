"""受限 Agent 教学项目的最小无网络 CLI。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluation import run_static_cases, write_public_evaluation_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="受限 Agent 无网络教学 CLI")
    parser.add_argument("--status", action="store_true", help="显示能力边界，不执行任务。")
    parser.add_argument("--run-static-evaluation", action="store_true", help="回放公开静态夹具。")
    parser.add_argument(
        "--write-static-report",
        action="store_true",
        help="回放公开夹具并写入固定、无正文的评测报告。",
    )
    args = parser.parse_args(argv)
    selected_modes = sum((args.status, args.run_static_evaluation, args.write_static_report))
    if selected_modes > 1:
        parser.error("--status、--run-static-evaluation 和 --write-static-report 只能选择一个。")
    if args.run_static_evaluation or args.write_static_report:
        fixture = Path(__file__).parents[2] / "tests" / "fixtures" / "agent_cases.json"
        results = run_static_cases(fixture)
        summary: dict[str, int | str] = {
            "case_count": len(results),
            "passed_count": sum(item.passed for item in results),
        }
        if args.write_static_report:
            report = Path.cwd() / "bounded-agent-static-evaluation.json"
            write_public_evaluation_report(results, report)
            summary["report_written"] = report.name
        print(json.dumps(summary, sort_keys=True))
        return 0
    print(
        json.dumps(
            {
                "version": "0.1.0",
                "mode": "framework_free_bounded_agent",
                "not_supported": [
                    "models",
                    "dynamic_tools",
                    "network",
                    "file_write",
                    "approval_bypass",
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
