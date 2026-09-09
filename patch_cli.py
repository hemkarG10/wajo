import re
with open("src/agent/cli.py", "r") as f:
    code = f.read()

orig = """            p = Panel(
                f"ID: {decision.id}\\n"
                f"Action: {decision.action.type}\\n"
                f"Level: {decision.level.name} (Policy: {decision.policy_level.name}, Floor: {decision.floor.name})\\n"
                f"Outcome: {outcome.blocked_reason or 'executed'} - {', '.join(outcome.effects)}",
                title="Decision & Outcome",
                border_style="green" if decision.level != AutonomyLevel.ESCALATE else "red"
            )"""

new = """            floor_reasons = ", ".join(decision.floor_reasons) if decision.floor_reasons else "—"
            bucket = decision.policy_reason.get("bucket", "unknown") if decision.policy_reason else "unknown"
            n = decision.policy_reason.get("n", 0) if decision.policy_reason else 0
            s = decision.policy_reason.get("s", 0.0) if decision.policy_reason else 0.0
            
            p = Panel(
                f"ID: {decision.id}\\n"
                f"Action: {decision.action.type}\\n"
                f"Level: {decision.level.name} (Policy: {decision.policy_level.name}, Floor: {decision.floor.name})\\n"
                f"Floor reasons: {floor_reasons}\\n"
                f"Policy: bucket={bucket} n={n} s={s:.2f}\\n"
                f"Outcome: {outcome.blocked_reason or 'executed'} - {', '.join(outcome.effects)}",
                title="Decision & Outcome",
                border_style="green" if decision.level != AutonomyLevel.ESCALATE else "red"
            )"""
code = code.replace(orig, new)

with open("src/agent/cli.py", "w") as f:
    f.write(code)
