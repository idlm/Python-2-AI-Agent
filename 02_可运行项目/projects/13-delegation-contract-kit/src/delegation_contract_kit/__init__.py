"""模块 13：无副作用多 Agent 委派、预算和汇总合同。"""

from .core import (
    AggregationSummary,
    DelegationContractError,
    DelegationCoordinator,
    DelegationRequest,
    DelegationStatus,
    ResultCategory,
    RolePolicy,
    WorkerResult,
    WorkerRole,
)

__all__ = [
    "AggregationSummary",
    "DelegationContractError",
    "DelegationCoordinator",
    "DelegationRequest",
    "DelegationStatus",
    "ResultCategory",
    "RolePolicy",
    "WorkerResult",
    "WorkerRole",
]
