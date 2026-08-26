"""运行项目 9 的离线静态评测并写出脱敏报告。"""

from __future__ import annotations

import json
from pathlib import Path

from llm_contract_client.evaluation import (
    load_candidates,
    load_cases,
    run_static_evaluation,
    write_public_report,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = PROJECT_ROOT / "tests" / "fixtures"
REPORT_PATH = PROJECT_ROOT / "reports" / "module_09_static_evaluation.json"


def main() -> int:
    report = run_static_evaluation(
        load_cases(FIXTURES / "evaluation_cases.json"),
        load_candidates(FIXTURES / "evaluation_candidates.json"),
    )
    write_public_report(report, REPORT_PATH)
    print(
        json.dumps(
            {
                "report_path": str(REPORT_PATH),
                "case_count": report.case_count,
                "passed_count": report.passed_count,
                "failed_count": report.failed_count,
                "contains_input_or_output_bodies": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if report.failed_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
