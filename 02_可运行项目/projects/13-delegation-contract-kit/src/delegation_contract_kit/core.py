"""无框架多 Agent 委派合同：纯状态和数据验证，绝不运行 Agent 或工具。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

_MAX_ID_LENGTH: Final[int] = 64
_MAX_SUMMARY_LENGTH: Final[int] = 120
_MAX_BUDGET: Final[int] = 10


def _is_identifier(value: object) -> bool:
    return (
        isinstance(value, str)
        and 1 <= len(value) <= _MAX_ID_LENGTH
        and value.replace("-", "").replace("_", "").isalnum()
    )


def _validate_budget(value: int, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= _MAX_BUDGET:
        raise DelegationContractError(f"{label}必须是 1–{_MAX_BUDGET} 的整数。")


class DelegationContractError(ValueError):
    """委派、角色、状态、预算或汇总输入违反受限合同。"""


class WorkerRole(StrEnum):
    PUBLIC_RESEARCHER = "public_researcher"
    POLICY_REVIEWER = "policy_reviewer"


class DelegationStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    REJECTED = "rejected"


class ResultCategory(StrEnum):
    SUPPORTED = "supported"
    NOT_SUPPORTED = "not_supported"
    NO_EVIDENCE = "no_evidence"


@dataclass(frozen=True)
class RolePolicy:
    """一个角色的最小工具与预算合同；不含 callable 或凭据。"""

    role: WorkerRole
    allowed_tools: frozenset[str]
    max_steps: int
    max_tool_calls: int

    def __post_init__(self) -> None:
        if not self.allowed_tools:
            raise DelegationContractError("角色至少需要一个固定工具名。")
        if not all(_is_identifier(tool) for tool in self.allowed_tools):
            raise DelegationContractError("角色工具名必须为受控标识。")
        _validate_budget(self.max_steps, "角色步骤预算")
        _validate_budget(self.max_tool_calls, "角色工具调用预算")


@dataclass(frozen=True)
class DelegationRequest:
    """提交给协调器的最小委派消息；摘要不是完整上下文。"""

    delegation_id: str
    parent_task_id: str
    role: WorkerRole
    task_summary: str
    input_ref: str
    allowed_tools: frozenset[str]
    max_steps: int
    max_tool_calls: int

    def __post_init__(self) -> None:
        _validate_identifier(self.delegation_id, "委派 ID")
        _validate_identifier(self.parent_task_id, "父任务 ID")
        if not isinstance(self.role, WorkerRole):
            raise DelegationContractError("角色必须是固定枚举。")
        if (
            not isinstance(self.task_summary, str)
            or not 1 <= len(self.task_summary) <= _MAX_SUMMARY_LENGTH
        ):
            raise DelegationContractError("任务摘要必须是 1–120 字符的受控字符串。")
        _validate_identifier(self.input_ref, "输入引用")
        if not self.allowed_tools or not all(_is_identifier(tool) for tool in self.allowed_tools):
            raise DelegationContractError("委派工具集合必须是非空受控标识集合。")
        _validate_budget(self.max_steps, "步骤预算")
        _validate_budget(self.max_tool_calls, "工具调用预算")

    @property
    def deduplication_key(self) -> tuple[str, WorkerRole, str, str]:
        """不含任务正文的稳定去重键。"""
        return (self.parent_task_id, self.role, self.input_ref, self.task_summary)


@dataclass(frozen=True)
class WorkerResult:
    """worker 的最小可汇总结果；没有自由正文、提示或工具返回。"""

    delegation_id: str
    parent_task_id: str
    role: WorkerRole
    input_ref: str
    category: ResultCategory
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_identifier(self.delegation_id, "委派 ID")
        _validate_identifier(self.parent_task_id, "父任务 ID")
        if not isinstance(self.role, WorkerRole) or not isinstance(self.category, ResultCategory):
            raise DelegationContractError("结果角色和类别必须是固定枚举。")
        _validate_identifier(self.input_ref, "输入引用")
        if not self.evidence_refs or not all(_is_identifier(ref) for ref in self.evidence_refs):
            raise DelegationContractError("结果必须含至少一个受控证据引用。")


@dataclass(frozen=True)
class AggregationSummary:
    """稳定汇总后的最小公开视图。"""

    result_count: int
    ordered_delegation_ids: tuple[str, ...]
    categories: tuple[ResultCategory, ...]
    has_conflict: bool


_DEFAULT_POLICIES: Final[dict[WorkerRole, RolePolicy]] = {
    WorkerRole.PUBLIC_RESEARCHER: RolePolicy(
        role=WorkerRole.PUBLIC_RESEARCHER,
        allowed_tools=frozenset({"read_public_fixture"}),
        max_steps=3,
        max_tool_calls=2,
    ),
    WorkerRole.POLICY_REVIEWER: RolePolicy(
        role=WorkerRole.POLICY_REVIEWER,
        allowed_tools=frozenset({"read_policy_fixture"}),
        max_steps=2,
        max_tool_calls=1,
    ),
}


class DelegationCoordinator:
    """内存教学协调器；只迁移状态，不运行并发任务或外部能力。"""

    def __init__(
        self,
        *,
        parent_task_id: str,
        max_delegations: int = 4,
        max_active: int = 2,
        policies: Mapping[WorkerRole, RolePolicy] | None = None,
    ) -> None:
        _validate_identifier(parent_task_id, "父任务 ID")
        _validate_budget(max_delegations, "总委派预算")
        _validate_budget(max_active, "活跃委派预算")
        if max_active > max_delegations:
            raise DelegationContractError("活跃委派预算不可超过总委派预算。")
        self._parent_task_id = parent_task_id
        self._max_delegations = max_delegations
        self._max_active = max_active
        self._policies = dict(_DEFAULT_POLICIES if policies is None else policies)
        if set(self._policies) != set(WorkerRole):
            raise DelegationContractError("角色策略必须恰好覆盖固定角色集合。")
        self._requests: dict[str, DelegationRequest] = {}
        self._statuses: dict[str, DelegationStatus] = {}
        self._deduplication_keys: set[tuple[str, WorkerRole, str, str]] = set()

    def register(self, request: DelegationRequest) -> None:
        """验证角色权限与去重，登记为 queued；不启动 worker。"""
        if request.parent_task_id != self._parent_task_id:
            raise DelegationContractError("委派父任务与协调器不匹配。")
        if request.delegation_id in self._requests:
            raise DelegationContractError("委派 ID 不可重复。")
        if len(self._requests) >= self._max_delegations:
            raise DelegationContractError("总委派预算已耗尽。")
        policy = self._policies[request.role]
        if not request.allowed_tools <= policy.allowed_tools:
            raise DelegationContractError("委派工具超出角色最小权限集合。")
        if request.max_steps > policy.max_steps or request.max_tool_calls > policy.max_tool_calls:
            raise DelegationContractError("委派预算超出角色预算。")
        if request.deduplication_key in self._deduplication_keys:
            raise DelegationContractError("委派工作范围重复。")
        self._requests[request.delegation_id] = request
        self._statuses[request.delegation_id] = DelegationStatus.QUEUED
        self._deduplication_keys.add(request.deduplication_key)

    def start(self, delegation_id: str) -> None:
        """从 queued 迁移到 running；在状态迁移前检查活跃预算。"""
        self._require_status(delegation_id, DelegationStatus.QUEUED)
        if self.active_count >= self._max_active:
            raise DelegationContractError("活跃委派预算已耗尽。")
        self._statuses[delegation_id] = DelegationStatus.RUNNING

    def finish(self, delegation_id: str, status: DelegationStatus) -> None:
        """从 running 迁移到受控终态；不接受任意状态写入。"""
        self._require_status(delegation_id, DelegationStatus.RUNNING)
        if status not in {
            DelegationStatus.COMPLETED,
            DelegationStatus.FAILED,
            DelegationStatus.CANCELLED,
            DelegationStatus.TIMED_OUT,
        }:
            raise DelegationContractError("运行中的委派只能迁移到固定终态。")
        self._statuses[delegation_id] = status

    def cancel_parent(self) -> None:
        """取消所有仍未终态的委派；不执行远端撤销或删除记录。"""
        for delegation_id, status in self._statuses.items():
            if status in {DelegationStatus.QUEUED, DelegationStatus.RUNNING}:
                self._statuses[delegation_id] = DelegationStatus.CANCELLED

    @property
    def active_count(self) -> int:
        return sum(status is DelegationStatus.RUNNING for status in self._statuses.values())

    def status_of(self, delegation_id: str) -> DelegationStatus:
        if delegation_id not in self._statuses:
            raise DelegationContractError("委派 ID 未登记。")
        return self._statuses[delegation_id]

    def aggregate(self, results: tuple[WorkerResult, ...]) -> AggregationSummary:
        """验证完成状态、身份和版本后稳定汇总最小结果。"""
        seen_ids: set[str] = set()
        ordered_results = sorted(results, key=lambda result: result.delegation_id)
        for result in ordered_results:
            if result.delegation_id in seen_ids:
                raise DelegationContractError("结果委派 ID 不可重复。")
            seen_ids.add(result.delegation_id)
            request = self._requests.get(result.delegation_id)
            if (
                request is None
                or self._statuses[result.delegation_id] is not DelegationStatus.COMPLETED
            ):
                raise DelegationContractError("仅可汇总已完成的已登记委派结果。")
            if (
                request.parent_task_id != result.parent_task_id
                or request.role is not result.role
                or request.input_ref != result.input_ref
            ):
                raise DelegationContractError("结果身份、角色或输入引用与委派不匹配。")
        categories = tuple(result.category for result in ordered_results)
        return AggregationSummary(
            result_count=len(ordered_results),
            ordered_delegation_ids=tuple(result.delegation_id for result in ordered_results),
            categories=categories,
            has_conflict=len(set(categories)) > 1,
        )

    def _require_status(self, delegation_id: str, expected: DelegationStatus) -> None:
        if self.status_of(delegation_id) is not expected:
            raise DelegationContractError("委派当前状态不允许该迁移。")


def _validate_identifier(value: str, label: str) -> None:
    if not _is_identifier(value):
        raise DelegationContractError(f"{label}必须是 1–64 字符的字母数字、短横线或下划线。")
