"""受控静态评测：不调用真实模型，不把夹具正文写入报告。"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from .structured import (
    StructuredSummary,
    StructuredSummaryClient,
    StructuredTransportReply,
)


class EvaluationFixtureError(ValueError):
    """静态评测夹具缺少字段或违反课程夹具合同。"""


@dataclass(frozen=True)
class EvaluationCase:
    """一条课程自制、非生产输入的评测规格。"""

    case_id: str
    input_text: str
    expected_keywords: tuple[str, ...]
    expected_uncertainty: str
    max_attempts: int
    max_output_tokens: int
    tags: tuple[str, ...]


@dataclass(frozen=True)
class EvaluationCandidate:
    """固定的假模型 JSON 响应及其脱敏资源计数。"""

    case_id: str
    json_output: str
    input_tokens: int | None
    output_tokens: int | None


@dataclass(frozen=True)
class EvaluationResult:
    """单条结果；刻意不含输入、摘要、关键点或完整模型响应。"""

    case_id: str
    tags: tuple[str, ...]
    schema_valid: bool
    matched_keyword_count: int
    missing_keyword_count: int
    keyword_coverage: float
    uncertainty_matches_expected: bool
    attempts_within_limit: bool
    output_tokens_within_limit: bool
    passed: bool


@dataclass(frozen=True)
class EvaluationReport:
    """可复现评测摘要；适合保存或在 CI 中比较。"""

    suite_name: str
    case_count: int
    passed_count: int
    failed_count: int
    results: tuple[EvaluationResult, ...]

    def as_public_dict(self) -> dict[str, object]:
        """生成可持久化报告，排除原始输入、输出、提示和 token 文本。"""
        return {
            "suite_name": self.suite_name,
            "case_count": self.case_count,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "results": [asdict(result) for result in self.results],
        }


class _ReplayStructuredTransport:
    """把一个夹具候选回放给真实本地验证链路；不产生网络访问。"""

    def __init__(self, candidate: EvaluationCandidate) -> None:
        self._candidate = candidate
        self._used = False

    def complete_json(
        self,
        *,
        model: str,
        system_prompt: str,
        user_text: str,
        max_output_tokens: int,
        schema_name: str,
        schema: Mapping[str, object],
    ) -> StructuredTransportReply:
        del model, system_prompt, user_text, max_output_tokens, schema_name, schema
        if self._used:
            raise EvaluationFixtureError("单条评测候选只能被回放一次。")
        self._used = True
        return StructuredTransportReply(
            json_text=self._candidate.json_output,
            input_tokens=self._candidate.input_tokens,
            output_tokens=self._candidate.output_tokens,
        )


def load_cases(path: Path) -> tuple[EvaluationCase, ...]:
    """读取并验证静态案例；夹具输入只在内存中使用。"""
    raw = _load_list(path)
    cases = tuple(_parse_case(item) for item in raw)
    _require_unique_ids((case.case_id for case in cases), "案例")
    return cases


def load_candidates(path: Path) -> tuple[EvaluationCandidate, ...]:
    """读取并验证静态候选响应。"""
    raw = _load_list(path)
    candidates = tuple(_parse_candidate(item) for item in raw)
    _require_unique_ids((candidate.case_id for candidate in candidates), "候选")
    return candidates


def run_static_evaluation(
    cases: Sequence[EvaluationCase],
    candidates: Sequence[EvaluationCandidate],
    *,
    suite_name: str = "module-09-static-contract-suite",
) -> EvaluationReport:
    """对静态候选执行本地 Schema 和确定性质量门；不调用真实模型。"""
    if not cases:
        raise EvaluationFixtureError("评测至少需要一个案例。")
    by_case_id = {candidate.case_id: candidate for candidate in candidates}
    case_ids = {case.case_id for case in cases}
    if set(by_case_id) != case_ids:
        raise EvaluationFixtureError("案例与候选的 case_id 必须一一对应。")
    results = tuple(
        evaluate_case(
            case,
            _summarize_fixture(case, by_case_id[case.case_id]),
        )
        for case in cases
    )
    passed_count = sum(result.passed for result in results)
    return EvaluationReport(
        suite_name=suite_name,
        case_count=len(results),
        passed_count=passed_count,
        failed_count=len(results) - passed_count,
        results=results,
    )


def evaluate_case(case: EvaluationCase, summary: StructuredSummary) -> EvaluationResult:
    """按公开、确定性规则评估已通过本地 Schema 验证的结果。"""
    searchable = " ".join((summary.summary, *summary.key_points)).casefold()
    matched_count = sum(
        keyword.casefold() in searchable for keyword in case.expected_keywords
    )
    missing_count = len(case.expected_keywords) - matched_count
    keyword_coverage = matched_count / len(case.expected_keywords)
    uncertainty_matches = summary.uncertainty == case.expected_uncertainty
    attempts_within_limit = summary.attempts <= case.max_attempts
    output_tokens_within_limit = (
        summary.output_tokens is None or summary.output_tokens <= case.max_output_tokens
    )
    passed = (
        missing_count == 0
        and uncertainty_matches
        and attempts_within_limit
        and output_tokens_within_limit
    )
    return EvaluationResult(
        case_id=case.case_id,
        tags=case.tags,
        schema_valid=True,
        matched_keyword_count=matched_count,
        missing_keyword_count=missing_count,
        keyword_coverage=keyword_coverage,
        uncertainty_matches_expected=uncertainty_matches,
        attempts_within_limit=attempts_within_limit,
        output_tokens_within_limit=output_tokens_within_limit,
        passed=passed,
    )


def write_public_report(report: EvaluationReport, path: Path) -> None:
    """原子写入报告；报告中从设计上不存在输入和模型正文。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report.as_public_dict(), ensure_ascii=False, indent=2, sort_keys=True)
    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        temporary.write(f"{payload}\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def _summarize_fixture(case: EvaluationCase, candidate: EvaluationCandidate) -> StructuredSummary:
    client = StructuredSummaryClient(
        _ReplayStructuredTransport(candidate),
        max_attempts=1,
        max_output_tokens=case.max_output_tokens,
    )
    return client.summarize(case.input_text, request_id=f"evaluation-{case.case_id}")


def _load_list(path: Path) -> list[Mapping[str, object]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise EvaluationFixtureError("无法读取评测夹具。") from exc
    except json.JSONDecodeError as exc:
        raise EvaluationFixtureError("评测夹具不是合法 JSON。") from exc
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise EvaluationFixtureError("评测夹具顶层必须是对象数组。")
    return [item for item in payload if isinstance(item, dict)]


def _parse_case(item: Mapping[str, object]) -> EvaluationCase:
    return EvaluationCase(
        case_id=_required_string(item, "case_id"),
        input_text=_required_string(item, "input_text"),
        expected_keywords=_required_strings(item, "expected_keywords"),
        expected_uncertainty=_required_string(item, "expected_uncertainty"),
        max_attempts=_required_positive_int(item, "max_attempts"),
        max_output_tokens=_required_positive_int(item, "max_output_tokens"),
        tags=_required_strings(item, "tags"),
    )


def _parse_candidate(item: Mapping[str, object]) -> EvaluationCandidate:
    input_tokens = _optional_non_negative_int(item, "input_tokens")
    output_tokens = _optional_non_negative_int(item, "output_tokens")
    output = item.get("output")
    if not isinstance(output, dict):
        raise EvaluationFixtureError("候选 output 必须是 JSON 对象。")
    return EvaluationCandidate(
        case_id=_required_string(item, "case_id"),
        json_output=json.dumps(output, ensure_ascii=False, sort_keys=True),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def _required_string(item: Mapping[str, object], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise EvaluationFixtureError(f"夹具字段 {key} 必须是非空字符串。")
    return value


def _required_strings(item: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = item.get(key)
    if not isinstance(value, list) or not value:
        raise EvaluationFixtureError(f"夹具字段 {key} 必须是非空字符串数组。")
    if not all(isinstance(part, str) and part.strip() for part in value):
        raise EvaluationFixtureError(f"夹具字段 {key} 必须是非空字符串数组。")
    return tuple(value)


def _required_positive_int(item: Mapping[str, object], key: str) -> int:
    value = item.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise EvaluationFixtureError(f"夹具字段 {key} 必须是正整数。")
    return value


def _optional_non_negative_int(item: Mapping[str, object], key: str) -> int | None:
    value = item.get(key)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise EvaluationFixtureError(f"夹具字段 {key} 必须是非负整数或 null。")
    return value


def _require_unique_ids(ids: Iterable[str], label: str) -> None:
    collected = tuple(ids)
    if len(set(collected)) != len(collected):
        raise EvaluationFixtureError(f"{label} case_id 不可重复。")
