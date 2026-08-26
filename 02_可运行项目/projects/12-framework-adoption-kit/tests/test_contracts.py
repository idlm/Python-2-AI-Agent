from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from framework_adoption_kit import (
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


def _descriptor() -> ToolDescriptor:
    return ToolDescriptor(
        name="notify_preview",
        allowed_argument_fields=frozenset({"recipient_id", "template_id"}),
        required_argument_fields=frozenset({"recipient_id", "template_id"}),
    )


def _candidate() -> ActionCandidate:
    return ActionCandidate(
        tool_name="notify_preview",
        arguments={"recipient_id": "user-1", "template_id": "template-1"},
    )


def _resume(
    candidate: ActionCandidate,
    *,
    decision: ApprovalDecision = ApprovalDecision.APPROVED,
) -> ApprovalResume:
    return ApprovalResume(
        approval_id="approval-1",
        task_id="task-1",
        tenant_id="tenant-1",
        decision=decision,
        tool_name=candidate.tool_name,
        candidate_fingerprint=candidate_fingerprint(candidate),
        expires_at=datetime(2030, 1, 1, tzinfo=UTC),
    )


def _checkpoint(candidate: ActionCandidate) -> CheckpointView:
    return CheckpointView(
        task_id="task-1",
        tenant_id="tenant-1",
        status=CheckpointStatus.WAITING_FOR_APPROVAL,
        pending_tool_name=candidate.tool_name,
        candidate_fingerprint=candidate_fingerprint(candidate),
    )


def test_candidate_is_bound_to_fixed_descriptor_and_fingerprint_is_stable() -> None:
    candidate = _candidate()

    validate_candidate(candidate, _descriptor())

    assert candidate_fingerprint(candidate) == candidate_fingerprint(candidate)


@pytest.mark.parametrize(
    "candidate",
    [
        ActionCandidate(
            tool_name="notify_preview",
            arguments={"recipient_id": "user-1", "template_id": "template-1", "extra": "no"},
        ),
        ActionCandidate(tool_name="notify_preview", arguments={"recipient_id": "user-1"}),
    ],
)
def test_candidate_rejects_extra_or_missing_descriptor_fields(candidate: ActionCandidate) -> None:
    with pytest.raises(FrameworkContractError):
        validate_candidate(candidate, _descriptor())


def test_waiting_checkpoint_requires_only_minimal_bound_candidate_metadata() -> None:
    candidate = _candidate()
    checkpoint = _checkpoint(candidate)

    assert checkpoint.pending_tool_name == "notify_preview"
    assert "user-1" not in repr(checkpoint)


def test_approved_resume_requires_exact_task_tenant_and_candidate_binding() -> None:
    candidate = _candidate()

    validate_approved_resume(
        _checkpoint(candidate),
        candidate,
        _descriptor(),
        _resume(candidate),
        now=datetime(2029, 1, 1, tzinfo=UTC),
    )


@pytest.mark.parametrize(
    "resume",
    [
        _resume(_candidate(), decision=ApprovalDecision.REJECTED),
        ApprovalResume(
            approval_id="approval-1",
            task_id="task-1",
            tenant_id="tenant-other",
            decision=ApprovalDecision.APPROVED,
            tool_name="notify_preview",
            candidate_fingerprint=candidate_fingerprint(_candidate()),
            expires_at=datetime(2030, 1, 1, tzinfo=UTC),
        ),
    ],
)
def test_resume_rejects_not_approved_or_cross_tenant(resume: ApprovalResume) -> None:
    candidate = _candidate()
    with pytest.raises(FrameworkContractError):
        validate_approved_resume(
            _checkpoint(candidate),
            candidate,
            _descriptor(),
            resume,
            now=datetime(2029, 1, 1, tzinfo=UTC),
        )


def test_resume_rejects_expired_approval_before_any_tool_exists() -> None:
    candidate = _candidate()
    expired = ApprovalResume(
        approval_id="approval-1",
        task_id="task-1",
        tenant_id="tenant-1",
        decision=ApprovalDecision.APPROVED,
        tool_name="notify_preview",
        candidate_fingerprint=candidate_fingerprint(candidate),
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )

    with pytest.raises(FrameworkContractError, match="过期"):
        validate_approved_resume(
            _checkpoint(candidate),
            candidate,
            _descriptor(),
            expired,
            now=datetime.now(UTC),
        )


def test_checkpoint_rejects_waiting_state_without_candidate_binding() -> None:
    with pytest.raises(FrameworkContractError, match="等待审批"):
        CheckpointView(
            task_id="task-1",
            tenant_id="tenant-1",
            status=CheckpointStatus.WAITING_FOR_APPROVAL,
            pending_tool_name=None,
            candidate_fingerprint=None,
        )
