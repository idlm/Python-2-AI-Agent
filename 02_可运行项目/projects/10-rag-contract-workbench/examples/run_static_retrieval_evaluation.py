"""运行模块 10 的公开静态检索评测；不调用网络、模型或外部嵌入服务。"""

from __future__ import annotations

import json
from pathlib import Path

from rag_contract_workbench.core import (
    CourseDocument,
    HashingEmbeddingProvider,
    InMemoryVectorIndex,
)
from rag_contract_workbench.evaluation import (
    RetrievalEvaluationCase,
    run_retrieval_evaluation,
    write_public_report,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "retrieval_evaluation.json"
REPORT_PATH = PROJECT_ROOT / "reports" / "module_10_static_retrieval_evaluation.json"


def main() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    documents = tuple(CourseDocument(**item) for item in fixture["documents"])
    cases = tuple(
        RetrievalEvaluationCase(
            case_id=item["case_id"],
            query=item["query"],
            expected_document_ids=tuple(item["expected_document_ids"]),
            top_k=item["top_k"],
            score_threshold=item["score_threshold"],
            min_precision=item["min_precision"],
            tags=tuple(item["tags"]),
        )
        for item in fixture["cases"]
    )
    index = InMemoryVectorIndex(HashingEmbeddingProvider(dimensions=1024))
    index.build(documents, chunk_size=80, overlap=0)
    report = run_retrieval_evaluation(index, cases)
    write_public_report(report, REPORT_PATH)
    print(
        json.dumps(
            {
                "report": REPORT_PATH.name,
                "case_count": report.case_count,
                "passed_count": report.passed_count,
                "failed_count": report.failed_count,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
