"""回放模块 15 公开静态运行准备夹具；不读取环境、秘密或启动服务。"""

from __future__ import annotations

import json
from pathlib import Path

from operational_readiness_kit.evaluation import (
    run_static_readiness_cases,
    write_public_readiness_report,
)


def main() -> None:
    project_root = Path(__file__).parents[1]
    fixture = project_root / "tests" / "fixtures" / "readiness_cases.json"
    results = run_static_readiness_cases(fixture)
    report = project_root / "operational-readiness-report.json"
    write_public_readiness_report(results, report)
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
