"""回放模块 14 公开静态门禁夹具；不执行 Agent、模型、追踪或工具。"""

from __future__ import annotations

import json
from pathlib import Path

from evaluation_gate_kit.evaluation import run_static_gate_cases, write_public_gate_report


def main() -> None:
    project_root = Path(__file__).parents[1]
    fixture = project_root / "tests" / "fixtures" / "gate_cases.json"
    results = run_static_gate_cases(fixture)
    report = project_root / "evaluation-gate-report.json"
    write_public_gate_report(results, report)
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
