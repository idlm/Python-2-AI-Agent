"""回放模块 12 公开静态迁移夹具；不调用模型、框架或真实工具。"""

from __future__ import annotations

import json
from pathlib import Path

from framework_adoption_kit.evaluation import (
    run_static_migration_cases,
    write_public_migration_report,
)


def main() -> None:
    project_root = Path(__file__).parents[1]
    fixture = project_root / "tests" / "fixtures" / "migration_cases.json"
    results = run_static_migration_cases(fixture)
    report = project_root / "framework-adoption-migration-report.json"
    write_public_migration_report(results, report)
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
