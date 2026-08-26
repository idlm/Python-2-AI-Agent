"""多 Agent 委派合同的无网络静态回放；绝不创建真实 worker。"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .core import (
    DelegationContractError,
    DelegationCoordinator,
    DelegationRequest,
    WorkerRole,
)


class DelegationFixtureError(ValueError):
    """公开静态委派夹具不符合字段闭集与类型合同。"""


@dataclass(frozen=True)
class DelegationCaseResult:
    case_id: str
    expected: str
    actual: str
    passed: bool


_ALLOWED_CASE_FIELDS = {"case_id", "requests", "expected"}
_ALLOWED_REQUEST_FIELDS = {
    "delegation_id",
    "role",
    "task_summary",
    "input_ref",
    "allowed_tools",
    "max_steps",
    "max_tool_calls",
}
_ALLOWED_OUTCOMES = {"accepted", "rejected"}


def run_static_delegation_cases(path: Path) -> tuple[DelegationCaseResult, ...]:
    """离线回放固定教学夹具，并将合同拒绝归类为 rejected。"""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DelegationFixtureError("静态委派夹具不可读取或不是合法 JSON。") from exc
    if not isinstance(raw, list) or not raw:
        raise DelegationFixtureError("静态委派夹具必须是非空数组。")

    results: list[DelegationCaseResult] = []
    case_ids: set[str] = set()
    for raw_case in raw:
        case_id, requests, expected = _parse_case(raw_case)
        if case_id in case_ids:
            raise DelegationFixtureError("静态委派案例 ID 不可重复。")
        case_ids.add(case_id)
        actual = _run_case(requests)
        results.append(
            DelegationCaseResult(
                case_id=case_id,
                expected=expected,
                actual=actual,
                passed=actual == expected,
            )
        )
    return tuple(results)


def write_public_delegation_report(results: tuple[DelegationCaseResult, ...], path: Path) -> None:
    """原子写入无正文公开报告，仅保存案例 ID、类别和通过标记。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "case_count": len(results),
        "passed_count": sum(result.passed for result in results),
        "results": [asdict(result) for result in results],
    }
    temporary_path = path.with_name(f".{path.name}.tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def _parse_case(raw_case: Any) -> tuple[str, tuple[DelegationRequest, ...], str]:
    if not isinstance(raw_case, dict) or set(raw_case) != _ALLOWED_CASE_FIELDS:
        raise DelegationFixtureError("静态委派案例必须恰好含固定字段。")
    case_id = raw_case["case_id"]
    raw_requests = raw_case["requests"]
    expected = raw_case["expected"]
    if not isinstance(case_id, str) or not isinstance(raw_requests, list) or not raw_requests:
        raise DelegationFixtureError("案例 ID 和委派数组必须有效且非空。")
    if expected not in _ALLOWED_OUTCOMES:
        raise DelegationFixtureError("案例期望类别不受支持。")
    requests = tuple(_parse_request(raw_request) for raw_request in raw_requests)
    return case_id, requests, expected


def _parse_request(raw_request: Any) -> DelegationRequest:
    if not isinstance(raw_request, dict) or set(raw_request) != _ALLOWED_REQUEST_FIELDS:
        raise DelegationFixtureError("委派必须恰好含固定字段。")
    raw_tools = raw_request["allowed_tools"]
    if not isinstance(raw_tools, list) or not all(isinstance(tool, str) for tool in raw_tools):
        raise DelegationFixtureError("委派工具集合必须是字符串数组。")
    try:
        return DelegationRequest(
            delegation_id=raw_request["delegation_id"],
            parent_task_id="fixture-parent",
            role=WorkerRole(raw_request["role"]),
            task_summary=raw_request["task_summary"],
            input_ref=raw_request["input_ref"],
            allowed_tools=frozenset(raw_tools),
            max_steps=raw_request["max_steps"],
            max_tool_calls=raw_request["max_tool_calls"],
        )
    except (DelegationContractError, KeyError, TypeError, ValueError) as exc:
        raise DelegationFixtureError("委派字段不符合受限合同。") from exc


def _run_case(requests: tuple[DelegationRequest, ...]) -> str:
    coordinator = DelegationCoordinator(parent_task_id="fixture-parent")
    try:
        for request in requests:
            coordinator.register(request)
    except DelegationContractError:
        return "rejected"
    return "accepted"
