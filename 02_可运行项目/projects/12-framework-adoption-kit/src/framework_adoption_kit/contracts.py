"""框架采用前可独立验证的状态、工具和审批合同；绝不调用真实工具。"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Final

_MAX_ID_LENGTH: Final[int] = 64
_MAX_ARGUMENT_LENGTH: Final[int] = 120
_CHECKPOINT_VERSION: Final[int] = 1


class FrameworkContractError(ValueError):
    """框架映射输入、状态、候选或审批恢复值违反受限合同。"""


class CheckpointStatus(StrEnum):
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    STOPPED = "stopped"


class ApprovalDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ToolDescriptor:
    """一个固定工具的最小公开合同；没有 callable 或权限令牌。"""

    name: str
    allowed_argument_fields: frozenset[str]
    required_argument_fields: frozenset[str]
    requires_approval: bool = True

    def __post_init__(self) -> None:
        _validate_identifier(self.name, "工具名")
        if not self.required_argument_fields <= self.allowed_argument_fields:
            raise FrameworkContractError("必填参数必须是允许参数字段的子集。")
        if not all(_is_field_name(field) for field in self.allowed_argument_fields):
            raise FrameworkContractError("工具参数字段必须为 1–64 字符的字母数字或下划线。")


@dataclass(frozen=True)
class ActionCandidate:
    """模型或图节点提出的行动候选，尚未获得执行资格。"""

    tool_name: str
    arguments: Mapping[str, str]

    def __post_init__(self) -> None:
        _validate_identifier(self.tool_name, "候选工具名")
        if not isinstance(self.arguments, Mapping):
            raise FrameworkContractError("候选参数必须是对象。")
        if not self.arguments:
            raise FrameworkContractError("候选参数不可为空。")
        for field, value in self.arguments.items():
            if not _is_field_name(field):
                raise FrameworkContractError("候选参数字段不合法。")
            if not isinstance(value, str) or not value.strip() or len(value) > _MAX_ARGUMENT_LENGTH:
                raise FrameworkContractError("候选参数值必须是 1–120 字符的非空字符串。")


@dataclass(frozen=True)
class CheckpointView:
    """可持久化的最小审批暂停快照；不含目标、提示或工具结果正文。"""

    task_id: str
    tenant_id: str
    status: CheckpointStatus
    pending_tool_name: str | None
    candidate_fingerprint: str | None
    schema_version: int = _CHECKPOINT_VERSION

    def __post_init__(self) -> None:
        _validate_identifier(self.task_id, "任务 ID")
        _validate_identifier(self.tenant_id, "租户 ID")
        if self.schema_version != _CHECKPOINT_VERSION:
            raise FrameworkContractError("checkpoint 版本不受当前实现支持。")
        if self.status is CheckpointStatus.WAITING_FOR_APPROVAL:
            if self.pending_tool_name is None or self.candidate_fingerprint is None:
                raise FrameworkContractError("等待审批快照必须含受控工具名和候选指纹。")
            _validate_identifier(self.pending_tool_name, "待审批工具名")
            if not _is_digest(self.candidate_fingerprint):
                raise FrameworkContractError("候选指纹必须是 SHA-256 十六进制摘要。")
        elif self.pending_tool_name is not None or self.candidate_fingerprint is not None:
            raise FrameworkContractError("非等待审批快照不可携带待审批候选。")


@dataclass(frozen=True)
class ApprovalResume:
    """恢复输入的最小字段；应用仍必须比对快照、时间和候选摘要。"""

    approval_id: str
    task_id: str
    tenant_id: str
    decision: ApprovalDecision
    tool_name: str
    candidate_fingerprint: str
    expires_at: datetime

    def __post_init__(self) -> None:
        for value, label in (
            (self.approval_id, "审批 ID"),
            (self.task_id, "任务 ID"),
            (self.tenant_id, "租户 ID"),
            (self.tool_name, "工具名"),
        ):
            _validate_identifier(value, label)
        if not isinstance(self.decision, ApprovalDecision):
            raise FrameworkContractError("审批决定必须是允许枚举。")
        if not _is_digest(self.candidate_fingerprint):
            raise FrameworkContractError("审批候选指纹必须是 SHA-256 十六进制摘要。")
        if self.expires_at.tzinfo is None:
            raise FrameworkContractError("审批过期时间必须带时区。")


def candidate_fingerprint(candidate: ActionCandidate) -> str:
    """生成稳定摘要，只用于绑定候选与审批，不持久化原始参数。"""
    canonical = json.dumps(
        {"tool_name": candidate.tool_name, "arguments": dict(sorted(candidate.arguments.items()))},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_candidate(candidate: ActionCandidate, descriptor: ToolDescriptor) -> None:
    """在审批或执行前验证固定工具名及参数字段闭集。"""
    if candidate.tool_name != descriptor.name:
        raise FrameworkContractError("候选工具不在固定目录条目中。")
    fields = set(candidate.arguments)
    if not fields <= descriptor.allowed_argument_fields:
        raise FrameworkContractError("候选含未允许参数字段。")
    if not descriptor.required_argument_fields <= fields:
        raise FrameworkContractError("候选缺少必填参数字段。")


def validate_approved_resume(
    checkpoint: CheckpointView,
    candidate: ActionCandidate,
    descriptor: ToolDescriptor,
    resume: ApprovalResume,
    *,
    now: datetime,
) -> None:
    """执行前再次核验审批绑定、候选、目录、状态和过期时间；不执行工具。"""
    if now.tzinfo is None:
        raise FrameworkContractError("当前时间必须带时区。")
    validate_candidate(candidate, descriptor)
    fingerprint = candidate_fingerprint(candidate)
    if checkpoint.status is not CheckpointStatus.WAITING_FOR_APPROVAL:
        raise FrameworkContractError("只有等待审批快照可恢复。")
    if not descriptor.requires_approval:
        raise FrameworkContractError("当前对照合同只接受需要审批的工具。")
    if (
        checkpoint.task_id != resume.task_id
        or checkpoint.tenant_id != resume.tenant_id
        or checkpoint.pending_tool_name != candidate.tool_name
        or checkpoint.candidate_fingerprint != fingerprint
        or resume.tool_name != candidate.tool_name
        or resume.candidate_fingerprint != fingerprint
    ):
        raise FrameworkContractError("审批恢复值与当前任务、租户或候选不匹配。")
    if resume.decision is not ApprovalDecision.APPROVED:
        raise FrameworkContractError("审批未批准，工具不得执行。")
    if resume.expires_at <= now.astimezone(UTC):
        raise FrameworkContractError("审批已过期，工具不得执行。")


def _validate_identifier(value: str, label: str) -> None:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= _MAX_ID_LENGTH
        or not value.replace("-", "").replace("_", "").isalnum()
    ):
        raise FrameworkContractError(f"{label}必须是 1–64 字符的字母数字、短横线或下划线。")


def _is_field_name(value: object) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= _MAX_ID_LENGTH and value.isidentifier()


def _is_digest(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)
