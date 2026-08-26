"""回放模块 13 公开静态委派夹具；不运行真实 Agent、并发或工具。"""

from __future__ import annotations

import json
from pathlib import Path

from delegation_contract_kit.evaluation import (
    run_static_delegation_cases,
    write_public_delegation_report,
)


def main() -> None:
    project_root = Path(__file__).parents[1]
    fixture = project_root / "tests" / "fixtures" / "delegation_cases.json"
    results = run_static_delegation_cases(fixture)
    report = project_root / "delegation-contract-report.json"
    write_public_delegation_report(results, report)
    print(
        json.dumps(
            {
                "case_count": len(results),
                "passed_count": sum(result.passed for result in results),
                "report_written": report.name,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
