"""离线运行准备、恢复与运维合同；绝不启动服务或读取真实秘密。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

_MAX_ID_LENGTH: Final[int] = 64
_MAX_VERSION_LENGTH: Final[int] = 32


class OperationalReadinessError(ValueError):
    """部署准备、秘密元数据、恢复或 Runbook 输入违反受限合同。"""


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class Capability(StrEnum):
    MINIMAL_EVENTS = "minimal_events"
    READINESS_STATUS = "readiness_status"
    RECOVERY_VALIDATION = "recovery_validation"


class RuntimePhase(StrEnum):
    STARTING = "starting"
    READY = "ready"
    DRAINING = "draining"
    STOPPED = "stopped"
    RESULT_UNKNOWN = "result_unknown"


class SecretState(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class DrillState(StrEnum):
    VERIFIED = "verified"
    NOT_VERIFIED = "not_verified"


class ReadinessBlocker(StrEnum):
    DRAIN_NOT_SUPPORTED = "drain_not_supported"
    RECOVERY_NOT_VERIFIED = "recovery_not_verified"
    RUNBOOK_INCOMPLETE = "runbook_incomplete"
    SECRET_EXPIRED = "secret_expired"
    SECRET_MISSING = "secret_missing"
    SECRET_REVOKED = "secret_revoked"
    VERSION_INCOMPATIBLE = "version_incompatible"


class ReadinessDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class DeploymentProfile:
    """版本化部署元数据；只允许最小非执行能力。"""

    profile_id: str
    app_version: str
    environment: Environment
    enabled_capabilities: frozenset[Capability]
    required_secret_ids: tuple[str, ...]
    drain_supported: bool

    def __post_init__(self) -> None:
        _validate_identifier(self.profile_id, "部署 profile ID")
        _validate_version(self.app_version, "应用版本")
        if not isinstance(self.environment, Environment):
            raise OperationalReadinessError("环境必须是固定枚举。")
        if not self.enabled_capabilities:
            raise OperationalReadinessError("部署 profile 必须显式启用最小能力集合。")
        if not all(isinstance(capability, Capability) for capability in self.enabled_capabilities):
            raise OperationalReadinessError("能力必须来自固定允许列表。")
        if not isinstance(self.drain_supported, bool):
            raise OperationalReadinessError("drain 支持标记必须是布尔值。")
        if len(self.required_secret_ids) != len(set(self.required_secret_ids)):
            raise OperationalReadinessError("必需秘密 ID 不可重复。")
        for secret_id in self.required_secret_ids:
            _validate_identifier(secret_id, "必需秘密 ID")


@dataclass(frozen=True)
class SecretMetadata:
    """秘密元数据；刻意不提供秘密值字段。"""

    secret_id: str
    environment: Environment
    purpose: str
    state: SecretState
    rotation_version: str

    def __post_init__(self) -> None:
        _validate_identifier(self.secret_id, "秘密 ID")
        if not isinstance(self.environment, Environment):
            raise OperationalReadinessError("秘密环境必须是固定枚举。")
        _validate_identifier(self.purpose, "秘密用途")
        if not isinstance(self.state, SecretState):
            raise OperationalReadinessError("秘密状态必须是固定枚举。")
        _validate_version(self.rotation_version, "轮换版本")


@dataclass(frozen=True)
class RecoveryPlan:
    """恢复计划元数据；不含真实备份位置、数据或密钥。"""

    plan_id: str
    backup_format_version: str
    compatible_app_versions: frozenset[str]
    drill_state: DrillState

    def __post_init__(self) -> None:
        _validate_identifier(self.plan_id, "恢复计划 ID")
        _validate_version(self.backup_format_version, "备份格式版本")
        if not self.compatible_app_versions:
            raise OperationalReadinessError("恢复计划必须声明至少一个兼容应用版本。")
        for version in self.compatible_app_versions:
            _validate_version(version, "兼容应用版本")
        if not isinstance(self.drill_state, DrillState):
            raise OperationalReadinessError("恢复演练状态必须是固定枚举。")


@dataclass(frozen=True)
class OperationalRunbook:
    """运维 Runbook 的最小完成度合同。"""

    runbook_id: str
    has_pause_step: bool
    has_recovery_step: bool
    has_escalation_step: bool
    reviewed: bool

    def __post_init__(self) -> None:
        _validate_identifier(self.runbook_id, "Runbook ID")
        if not all(
            isinstance(value, bool)
            for value in (
                self.has_pause_step,
                self.has_recovery_step,
                self.has_escalation_step,
                self.reviewed,
            )
        ):
            raise OperationalReadinessError("Runbook 完成度字段必须是布尔值。")


@dataclass(frozen=True)
class ReadinessReport:
    """最小运行准备决定；不含配置正文、秘密、trace 或生产端点。"""

    profile_id: str
    app_version: str
    decision: ReadinessDecision
    blockers: tuple[ReadinessBlocker, ...]
    active_secret_count: int


def evaluate_operational_readiness(
    profile: DeploymentProfile,
    secrets: tuple[SecretMetadata, ...],
    recovery_plan: RecoveryPlan,
    runbook: OperationalRunbook,
) -> ReadinessReport:
    """比较部署 profile、秘密元数据、恢复计划与 Runbook，生成离线门禁决定。"""
    secret_ids = [secret.secret_id for secret in secrets]
    if len(secret_ids) != len(set(secret_ids)):
        raise OperationalReadinessError("秘密元数据 ID 不可重复。")
    blockers: set[ReadinessBlocker] = set()
    secret_by_id = {secret.secret_id: secret for secret in secrets}
    active_secret_count = 0
    for secret_id in profile.required_secret_ids:
        secret = secret_by_id.get(secret_id)
        if secret is None:
            blockers.add(ReadinessBlocker.SECRET_MISSING)
            continue
        if secret.environment is not profile.environment:
            blockers.add(ReadinessBlocker.SECRET_MISSING)
            continue
        if secret.state is SecretState.EXPIRED:
            blockers.add(ReadinessBlocker.SECRET_EXPIRED)
        elif secret.state is SecretState.REVOKED:
            blockers.add(ReadinessBlocker.SECRET_REVOKED)
        else:
            active_secret_count += 1
    if not profile.drain_supported:
        blockers.add(ReadinessBlocker.DRAIN_NOT_SUPPORTED)
    if recovery_plan.drill_state is not DrillState.VERIFIED:
        blockers.add(ReadinessBlocker.RECOVERY_NOT_VERIFIED)
    if profile.app_version not in recovery_plan.compatible_app_versions:
        blockers.add(ReadinessBlocker.VERSION_INCOMPATIBLE)
    if not (
        runbook.has_pause_step
        and runbook.has_recovery_step
        and runbook.has_escalation_step
        and runbook.reviewed
    ):
        blockers.add(ReadinessBlocker.RUNBOOK_INCOMPLETE)
    blocker_tuple = tuple(sorted(blockers, key=str))
    return ReadinessReport(
        profile_id=profile.profile_id,
        app_version=profile.app_version,
        decision=ReadinessDecision.REJECTED if blocker_tuple else ReadinessDecision.APPROVED,
        blockers=blocker_tuple,
        active_secret_count=active_secret_count,
    )


def _validate_identifier(value: str, label: str) -> None:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= _MAX_ID_LENGTH
        or not value.replace("-", "").replace("_", "").isalnum()
    ):
        raise OperationalReadinessError(f"{label}必须是 1–64 字符的字母数字、短横线或下划线。")


def _validate_version(value: str, label: str) -> None:
    if not isinstance(value, str) or not 1 <= len(value) <= _MAX_VERSION_LENGTH:
        raise OperationalReadinessError(f"{label}必须是 1–32 字符的受控字符串。")
