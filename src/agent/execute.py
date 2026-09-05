from agent.models import AutonomyLevel, Decision, Provenance

class Executor:
    def __init__(self, action_registry: dict, dry_run: bool = True):
        self.registry = action_registry
        self.dry_run = dry_run

    def execute(self, decision: Decision) -> dict:
        action_def = self.registry.get(decision.action.type, {})
        is_external = action_def.get("external", False)

        # Pre-flight check: Untrusted provenance on external actions
        if is_external:
            for k, p in decision.action.provenance.items():
                if p == Provenance.UNTRUSTED and k in ("to", "amount", "url", "account"):
                    return {
                        "status": "blocked",
                        "reason": f"UNTRUSTED provenance for param '{k}' on external action."
                    }

        if decision.level == AutonomyLevel.ESCALATE:
            return {"status": "held", "reason": "ESCALATED to human"}

        if decision.level == AutonomyLevel.ASK:
            return {"status": "queued", "reason": "ASK requested, draft saved."}

        if self.dry_run:
            return {"status": "dry_run", "reason": f"Would execute {decision.level.name}"}

        # In a real system, it would dispatch to action handlers here
        return {"status": "executed"}
