"""框架采用合同工具包的默认无执行 CLI。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluation import run_static_migration_cases, write_public_migration_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="框架采用合同的无网络教学 CLI")
    parser.add_argument("--status", action="store_true", help="显示能力边界，不执行回放。")
    parser.add_argument(
        "--run-static-migration",
        action="store_true",
        help="回放公开静态迁移夹具。",
    )
    parser.add_argument(
        "--write-static-report",
        action="store_true",
        help="回放公开夹具并在当前目录写入固定无正文报告。",
    )
    args = parser.parse_args(argv)
    selected_modes = sum((args.status, args.run_static_migration, args.write_static_report))
    if selected_modes > 1:
        parser.error("--status、--run-static-migration 和 --write-static-report 只能选择一个。")
    if args.run_static_migration or args.write_static_report:
        fixture = Path(__file__).parents[2] / "tests" / "fixtures" / "migration_cases.json"
        results = run_static_migration_cases(fixture)
        summary: dict[str, int | str] = {
            "case_count": len(results),
            "passed_count": sum(result.passed for result in results),
        }
        if args.write_static_report:
            report = Path.cwd() / "framework-adoption-migration-report.json"
            write_public_migration_report(results, report)
            summary["report_written"] = report.name
        print(json.dumps(summary, sort_keys=True))
        return 0
    print(
        json.dumps(
            {
                "mode": "framework_adoption_contracts",
                "not_supported": [
                    "framework_installation",
                    "models",
                    "dynamic_tools",
                    "network",
                    "persistence",
                    "tool_execution",
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
