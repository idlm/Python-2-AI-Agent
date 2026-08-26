from __future__ import annotations

import pytest

from delegation_contract_kit import (
    DelegationContractError,
    DelegationCoordinator,
    DelegationRequest,
    DelegationStatus,
    ResultCategory,
    WorkerResult,
    WorkerRole,
)


def _request(
    delegation_id: str = "delegation-a",
    *,
    role: WorkerRole = WorkerRole.PUBLIC_RESEARCHER,
    input_ref: str = "source-a",
    allowed_tools: frozenset[str] | None = None,
    max_steps: int = 2,
    max_tool_calls: int = 1,
) -> DelegationRequest:
    tools = allowed_tools
    if tools is None:
        tools = (
            frozenset({"read_public_fixture"})
            if role is WorkerRole.PUBLIC_RESEARCHER
            else frozenset({"read_policy_fixture"})
        )
    return DelegationRequest(
        delegation_id=delegation_id,
        parent_task_id="parent-1",
        role=role,
        task_summary=f"compare-{input_ref}",
        input_ref=input_ref,
        allowed_tools=tools,
        max_steps=max_steps,
        max_tool_calls=max_tool_calls,
    )


def _result(
    delegation_id: str,
    *,
    role: WorkerRole = WorkerRole.PUBLIC_RESEARCHER,
    input_ref: str = "source-a",
    category: ResultCategory = ResultCategory.SUPPORTED,
) -> WorkerResult:
    return WorkerResult(
        delegation_id=delegation_id,
        parent_task_id="parent-1",
        role=role,
        input_ref=input_ref,
        category=category,
        evidence_refs=("evidence-1",),
    )


def test_register_requires_role_minimal_tools_and_distinct_budgets() -> None:
    coordinator = DelegationCoordinator(parent_task_id="parent-1")
    coordinator.register(_request())

    assert coordinator.status_of("delegation-a") is DelegationStatus.QUEUED

    with pytest.raises(DelegationContractError, match="最小权限"):
        coordinator.register(
            _request(
                "delegation-b",
                allowed_tools=frozenset({"read_public_fixture", "read_policy_fixture"}),
            )
        )
    with pytest.raises(DelegationContractError, match="角色预算"):
        coordinator.register(_request("delegation-c", max_steps=4))


def test_duplicate_work_is_rejected_before_a_worker_can_start() -> None:
    coordinator = DelegationCoordinator(parent_task_id="parent-1")
    coordinator.register(_request())

    with pytest.raises(DelegationContractError, match="工作范围重复"):
        coordinator.register(_request("delegation-b"))


def test_active_budget_blocks_start_without_changing_queued_status() -> None:
    coordinator = DelegationCoordinator(parent_task_id="parent-1", max_active=1)
    coordinator.register(_request("delegation-a", input_ref="source-a"))
    coordinator.register(_request("delegation-b", input_ref="source-b"))
    coordinator.start("delegation-a")

    with pytest.raises(DelegationContractError, match="活跃委派预算"):
        coordinator.start("delegation-b")

    assert coordinator.status_of("delegation-b") is DelegationStatus.QUEUED


def test_only_running_delegation_can_reach_fixed_terminal_states() -> None:
    coordinator = DelegationCoordinator(parent_task_id="parent-1")
    coordinator.register(_request())

    with pytest.raises(DelegationContractError, match="当前状态"):
        coordinator.finish("delegation-a", DelegationStatus.COMPLETED)

    coordinator.start("delegation-a")
    coordinator.finish("delegation-a", DelegationStatus.COMPLETED)
    assert coordinator.status_of("delegation-a") is DelegationStatus.COMPLETED


def test_parent_cancellation_propagates_to_queued_and_running_only() -> None:
    coordinator = DelegationCoordinator(parent_task_id="parent-1")
    coordinator.register(_request("delegation-a", input_ref="source-a"))
    coordinator.register(_request("delegation-b", input_ref="source-b"))
    coordinator.start("delegation-a")
    coordinator.cancel_parent()

    assert coordinator.status_of("delegation-a") is DelegationStatus.CANCELLED
    assert coordinator.status_of("delegation-b") is DelegationStatus.CANCELLED


def test_aggregate_stably_sorts_results_and_marks_category_conflict() -> None:
    coordinator = DelegationCoordinator(parent_task_id="parent-1")
    coordinator.register(_request("delegation-b", input_ref="source-b"))
    coordinator.register(
        _request(
            "delegation-a",
            role=WorkerRole.POLICY_REVIEWER,
            input_ref="policy-a",
            max_steps=1,
        )
    )
    coordinator.start("delegation-b")
    coordinator.finish("delegation-b", DelegationStatus.COMPLETED)
    coordinator.start("delegation-a")
    coordinator.finish("delegation-a", DelegationStatus.COMPLETED)

    summary = coordinator.aggregate(
        (
            _result("delegation-b", input_ref="source-b"),
            _result(
                "delegation-a",
                role=WorkerRole.POLICY_REVIEWER,
                input_ref="policy-a",
                category=ResultCategory.NO_EVIDENCE,
            ),
        )
    )

    assert summary.ordered_delegation_ids == ("delegation-a", "delegation-b")
    assert summary.has_conflict is True


def test_aggregate_rejects_result_identity_mismatch_and_unfinished_work() -> None:
    coordinator = DelegationCoordinator(parent_task_id="parent-1")
    coordinator.register(_request())
    coordinator.start("delegation-a")
    coordinator.finish("delegation-a", DelegationStatus.COMPLETED)

    with pytest.raises(DelegationContractError, match="不匹配"):
        coordinator.aggregate((_result("delegation-a", input_ref="source-other"),))

    coordinator.register(_request("delegation-b", input_ref="source-b"))
    with pytest.raises(DelegationContractError, match="仅可汇总"):
        coordinator.aggregate((_result("delegation-b", input_ref="source-b"),))
