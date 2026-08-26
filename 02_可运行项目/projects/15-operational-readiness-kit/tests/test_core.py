from __future__ import annotations

import pytest

from operational_readiness_kit import (
    Capability,
    DeploymentProfile,
    DrillState,
    Environment,
    OperationalReadinessError,
    OperationalRunbook,
    ReadinessBlocker,
    ReadinessDecision,
    RecoveryPlan,
    SecretMetadata,
    SecretState,
    evaluate_operational_readiness,
)


def _profile(*, drain_supported: bool = True, version: str = "v1") -> DeploymentProfile:
    return DeploymentProfile(
        profile_id="profile-a",
        app_version=version,
        environment=Environment.STAGING,
        enabled_capabilities=frozenset(
            {Capability.MINIMAL_EVENTS, Capability.READINESS_STATUS, Capability.RECOVERY_VALIDATION}
        ),
        required_secret_ids=("secret-a",),
        drain_supported=drain_supported,
    )


def _secret(state: SecretState = SecretState.ACTIVE) -> SecretMetadata:
    return SecretMetadata(
        secret_id="secret-a",
        environment=Environment.STAGING,
        purpose="service-auth",
        state=state,
        rotation_version="r1",
    )


def _recovery(
    *, state: DrillState = DrillState.VERIFIED, versions: frozenset[str] | None = None
) -> RecoveryPlan:
    return RecoveryPlan(
        plan_id="recovery-a",
        backup_format_version="backup-v1",
        compatible_app_versions=versions if versions is not None else frozenset({"v1"}),
        drill_state=state,
    )


def _runbook(*, reviewed: bool = True) -> OperationalRunbook:
    return OperationalRunbook(
        runbook_id="runbook-a",
        has_pause_step=True,
        has_recovery_step=True,
        has_escalation_step=True,
        reviewed=reviewed,
    )


def test_complete_operational_profile_is_approved_without_secret_value() -> None:
    report = evaluate_operational_readiness(_profile(), (_secret(),), _recovery(), _runbook())

    assert report.decision is ReadinessDecision.APPROVED
    assert report.blockers == ()
    assert report.active_secret_count == 1
    assert not hasattr(_secret(), "value")


@pytest.mark.parametrize(
    ("secret_state", "expected"),
    [
        (SecretState.EXPIRED, ReadinessBlocker.SECRET_EXPIRED),
        (SecretState.REVOKED, ReadinessBlocker.SECRET_REVOKED),
    ],
)
def test_invalid_required_secret_blocks_readiness(
    secret_state: SecretState, expected: ReadinessBlocker
) -> None:
    report = evaluate_operational_readiness(
        _profile(),
        (_secret(secret_state),),
        _recovery(),
        _runbook(),
    )

    assert report.decision is ReadinessDecision.REJECTED
    assert report.blockers == (expected,)
    assert report.active_secret_count == 0


def test_missing_or_cross_environment_secret_is_not_accepted() -> None:
    missing = evaluate_operational_readiness(_profile(), (), _recovery(), _runbook())
    cross_environment = SecretMetadata(
        secret_id="secret-a",
        environment=Environment.TEST,
        purpose="service-auth",
        state=SecretState.ACTIVE,
        rotation_version="r1",
    )
    mismatched = evaluate_operational_readiness(
        _profile(),
        (cross_environment,),
        _recovery(),
        _runbook(),
    )

    assert missing.blockers == (ReadinessBlocker.SECRET_MISSING,)
    assert mismatched.blockers == (ReadinessBlocker.SECRET_MISSING,)


def test_drain_recovery_version_and_runbook_are_independent_blockers() -> None:
    report = evaluate_operational_readiness(
        _profile(drain_supported=False, version="v2"),
        (_secret(),),
        _recovery(state=DrillState.NOT_VERIFIED, versions=frozenset({"v1"})),
        _runbook(reviewed=False),
    )

    assert report.decision is ReadinessDecision.REJECTED
    assert report.blockers == (
        ReadinessBlocker.DRAIN_NOT_SUPPORTED,
        ReadinessBlocker.RECOVERY_NOT_VERIFIED,
        ReadinessBlocker.RUNBOOK_INCOMPLETE,
        ReadinessBlocker.VERSION_INCOMPATIBLE,
    )


def test_duplicate_secret_metadata_is_rejected_before_gate_evaluation() -> None:
    with pytest.raises(OperationalReadinessError, match="不可重复"):
        evaluate_operational_readiness(_profile(), (_secret(), _secret()), _recovery(), _runbook())


@pytest.mark.parametrize(
    "factory",
    [
        lambda: DeploymentProfile(
            profile_id="profile-a",
            app_version="v1",
            environment=Environment.STAGING,
            enabled_capabilities=frozenset(),
            required_secret_ids=("secret-a",),
            drain_supported=True,
        ),
        lambda: RecoveryPlan(
            plan_id="recovery-a",
            backup_format_version="backup-v1",
            compatible_app_versions=frozenset(),
            drill_state=DrillState.VERIFIED,
        ),
        lambda: OperationalRunbook(
            runbook_id="runbook-a",
            has_pause_step=True,
            has_recovery_step=True,
            has_escalation_step=True,
            reviewed="yes",  # type: ignore[arg-type]
        ),
    ],
)
def test_invalid_contract_shapes_are_rejected(factory: object) -> None:
    with pytest.raises(OperationalReadinessError):
        factory()  # type: ignore[operator]
