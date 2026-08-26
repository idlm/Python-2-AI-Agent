"""模块 12：框架采用前的无副作用 Agent 合同工具包。"""

from .contracts import (
    ActionCandidate,
    ApprovalDecision,
    ApprovalResume,
    CheckpointStatus,
    CheckpointView,
    FrameworkContractError,
    ToolDescriptor,
    candidate_fingerprint,
    validate_approved_resume,
    validate_candidate,
)

__all__ = [
    "ActionCandidate",
    "ApprovalDecision",
    "ApprovalResume",
    "CheckpointStatus",
    "CheckpointView",
    "FrameworkContractError",
    "ToolDescriptor",
    "candidate_fingerprint",
    "validate_approved_resume",
    "validate_candidate",
]
