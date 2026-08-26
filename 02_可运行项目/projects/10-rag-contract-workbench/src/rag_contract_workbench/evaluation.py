"""受控静态检索评测：不调用模型、不把查询或块正文写入报告。"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from .core import InMemoryVectorIndex, QueryError


class EvaluationFixtureError(ValueError):
    """检索评测夹具违反课程评测合同。"""


@dataclass(frozen=True)
class RetrievalEvaluationCase:
    """公开静态检索案例；查询只在内存使用，报告不持久化查询正文。"""

    case_id: str
    query: str
    expected_document_ids: tuple[str, ...]
    top_k: int
    score_threshold: float
    min_precision: float
    tags: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.case_id or len(self.case_id) > 64:
            raise EvaluationFixtureError("case_id 必须是 1–64 个字符。")
        if not self.query or len(self.query) > 500:
            raise EvaluationFixtureError("评测 query 必须是 1–500 个字符。")
        if self.top_k < 1 or self.top_k > 5:
            raise EvaluationFixtureError("评测 top_k 必须在 1–5 之间。")
        if not -1.0 <= self.score_threshold <= 1.0:
            raise EvaluationFixtureError("评测 score_threshold 必须在 -1.0–1.0 之间。")
        if not 0.0 <= self.min_precision <= 1.0:
            raise EvaluationFixtureError("评测 min_precision 必须在 0.0–1.0 之间。")
        if len(set(self.expected_document_ids)) != len(self.expected_document_ids):
            raise EvaluationFixtureError("expected_document_ids 不可重复。")
        if not self.tags:
            raise EvaluationFixtureError("评测 tags 不可为空。")


@dataclass(frozen=True)
class RetrievalEvaluationResult:
    """公开报告中的单例结果；不保存 query、候选正文或文档标题。"""

    case_id: str
    tags: tuple[str, ...]
    expected_count: int
    matched_expected_count: int
    returned_count: int
    recall: float
    precision: float
    source_complete: bool
    passed: bool


@dataclass(frozen=True)
class RetrievalEvaluationReport:
    """可复现的检索评测报告；面向 CI 比较而非语料日志。"""

    suite_name: str
    case_count: int
    passed_count: int
    failed_count: int
    results: tuple[RetrievalEvaluationResult, ...]

    def as_public_dict(self) -> dict[str, object]:
        return {
            "suite_name": self.suite_name,
            "case_count": self.case_count,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "results": [asdict(result) for result in self.results],
        }


def run_retrieval_evaluation(
    index: InMemoryVectorIndex,
    cases: Sequence[RetrievalEvaluationCase],
    *,
    suite_name: str = "module-10-static-retrieval-suite",
) -> RetrievalEvaluationReport:
    """在已构建索引上运行静态案例；不吞没查询/索引合同错误。"""
    if not cases:
        raise EvaluationFixtureError("检索评测至少需要一个案例。")
    _require_unique_ids(case.case_id for case in cases)
    results = tuple(evaluate_case(index, case) for case in cases)
    passed_count = sum(result.passed for result in results)
    return RetrievalEvaluationReport(
        suite_name=suite_name,
        case_count=len(results),
        passed_count=passed_count,
        failed_count=len(results) - passed_count,
        results=results,
    )


def evaluate_case(
    index: InMemoryVectorIndex,
    case: RetrievalEvaluationCase,
) -> RetrievalEvaluationResult:
    """计算来源级召回/精度与来源字段完整性，分数并不解释为事实性。"""
    try:
        retrieval = index.search(
            case.query,
            top_k=case.top_k,
            score_threshold=case.score_threshold,
        )
    except QueryError as exc:
        raise EvaluationFixtureError("检索评测案例无法执行。") from exc
    returned_document_ids = tuple(item.chunk.document_id for item in retrieval.results)
    expected_ids = set(case.expected_document_ids)
    returned_ids = set(returned_document_ids)
    matched_count = len(expected_ids & returned_ids)
    expected_count = len(expected_ids)
    recall = (
        1.0
        if expected_count == 0 and not returned_ids
        else _safe_ratio(matched_count, expected_count)
    )
    precision = (
        1.0
        if not returned_ids and expected_count == 0
        else _safe_ratio(matched_count, len(returned_ids))
    )
    source_complete = all(
        item.chunk.document_id
        and item.chunk.chunk_id
        and item.chunk.source_version
        and item.chunk.char_end > item.chunk.char_start
        for item in retrieval.results
    )
    passed = recall == 1.0 and precision >= case.min_precision and source_complete
    return RetrievalEvaluationResult(
        case_id=case.case_id,
        tags=case.tags,
        expected_count=expected_count,
        matched_expected_count=matched_count,
        returned_count=len(returned_ids),
        recall=recall,
        precision=precision,
        source_complete=source_complete,
        passed=passed,
    )


def write_public_report(report: RetrievalEvaluationReport, path: Path) -> None:
    """原子保存评测汇总；内容模型不包含查询、文本块或向量。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(report.as_public_dict(), ensure_ascii=False, indent=2, sort_keys=True)
    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        temporary.write(f"{serialized}\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def _safe_ratio(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def _require_unique_ids(ids: Iterable[str]) -> None:
    collected = tuple(ids)
    if len(set(collected)) != len(collected):
        raise EvaluationFixtureError("检索评测 case_id 不可重复。")
