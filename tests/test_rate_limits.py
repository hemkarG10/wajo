from datetime import UTC, datetime, timedelta

from agent.models import (
    AutonomyLevel,
    Decision,
    ExecutionOutcome,
    ProposedAction,
)
from agent.pipeline import _recent_action_counts, _record_autonomous_action


def _decision(level: AutonomyLevel, action_type: str) -> Decision:
    now = datetime.now(UTC)
    return Decision(
        id="d1",
        msg_id="m1",
        action=ProposedAction(
            type=action_type,
            params={},
            provenance={},
            rationale="test",
            confidence=1.0,
        ),
        level=level,
        policy_level=level,
        floor=AutonomyLevel.AUTO,
        floor_reasons=[],
        policy_reason={},
        guard_config_hash="",
        created_at=now,
    )


def _outcome(executed: bool, now: datetime) -> ExecutionOutcome:
    return ExecutionOutcome(
        decision_id="d1",
        executed=executed,
        blocked_reason=None if executed else "dry_run",
        effects=[],
        undo_token=None,
        notified=False,
        at=now,
    )


def test_records_only_executed_autonomous_actions():
    now = datetime.now(UTC)
    ctx = {}
    registry = {
        "send_reply_known": {"external": True},
        "archive": {"external": False},
    }

    _record_autonomous_action(
        ctx,
        _decision(AutonomyLevel.AUTO_NOTIFY, "send_reply_known"),
        _outcome(True, now),
        registry,
    )
    _record_autonomous_action(
        ctx,
        _decision(AutonomyLevel.AUTO, "archive"),
        _outcome(True, now),
        registry,
    )
    _record_autonomous_action(
        ctx,
        _decision(AutonomyLevel.ASK, "archive"),
        _outcome(False, now),
        registry,
    )

    assert _recent_action_counts(ctx, now) == {
        "AUTO_NOTIFY_sends_per_hour": 1,
        "AUTO_archives_per_hour": 1,
    }


def test_rate_window_resets_after_one_hour():
    now = datetime.now(UTC)
    ctx = {
        "_rate_state": {
            "window_started": now,
            "counts": {"AUTO_archives_per_hour": 50},
        }
    }

    assert _recent_action_counts(ctx, now + timedelta(hours=1)) == {}
