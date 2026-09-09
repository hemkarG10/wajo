import os

from agent.models import (
    AutonomyLevel,
    Clock,
    Decision,
    ExecutionOutcome,
    Provenance,
)


class Executor:
    def __init__(self, action_registry: dict, clock: Clock, dry_run: bool = True):
        self.registry = action_registry
        self.clock = clock
        self.dry_run = dry_run
        
    def _is_killed(self) -> bool:
        return os.environ.get("AGENT_PAUSED") == "1"

    def execute(self, decision: Decision, disable_preflight: bool = False) -> ExecutionOutcome:
        action_def = self.registry.get(decision.action.type, {})
        is_external = action_def.get("external", False)
        now = self.clock.now()
        
        # Kill switch
        if self._is_killed():
            return ExecutionOutcome(
                decision_id=decision.id,
                executed=False,
                blocked_reason="kill_switch",
                effects=[],
                undo_token=None,
                notified=False,
                at=now
            )

        if decision.level == AutonomyLevel.ESCALATE:
            return ExecutionOutcome(
                decision_id=decision.id,
                executed=False,
                blocked_reason="held_escalate",
                effects=[],
                undo_token=None,
                notified=False,
                at=now
            )

        if decision.level == AutonomyLevel.ASK:
            return ExecutionOutcome(
                decision_id=decision.id,
                executed=False,
                blocked_reason="queued_ask",
                effects=[f"Drafted {decision.action.type} for review"],
                undo_token=None,
                notified=False,
                at=now
            )

        # Pre-flight check: Untrusted provenance on external actions
        if is_external and not disable_preflight:
            for k, p in decision.action.provenance.items():
                if p == Provenance.UNTRUSTED and k in ("to", "destination", "amount", "url", "account"):
                    return ExecutionOutcome(
                        decision_id=decision.id,
                        executed=False,
                        blocked_reason="untrusted_destination",
                        effects=[],
                        undo_token=None,
                        notified=False,
                        at=now
                    )

        if self.dry_run:
            return ExecutionOutcome(
                decision_id=decision.id,
                executed=False,
                blocked_reason="dry_run",
                effects=[f"Would execute {decision.action.type}"],
                undo_token=None,
                notified=decision.level == AutonomyLevel.AUTO_NOTIFY,
                at=now
            )

        # In a real system, it would dispatch to action handlers here
        return ExecutionOutcome(
            decision_id=decision.id,
            executed=True,
            blocked_reason=None,
            effects=[f"Executed {decision.action.type}"],
            undo_token="undo_123" if action_def.get("reversible") else None,
            notified=decision.level == AutonomyLevel.AUTO_NOTIFY,
            at=now
        )
