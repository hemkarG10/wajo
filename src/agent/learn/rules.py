from typing import Literal


class RulesEngine:
    def __init__(self, rules: list[dict] | None = None):
        self.rules = rules or []

    def add_rule(self, bucket: str, kind: Literal["stop_asking", "always_ask"]):
        self.rules.append({
            "bucket": bucket,
            "kind": kind
        })

    def check(self, bucket: str) -> Literal["stop_asking", "always_ask", "none"]:
        # Find the most recent rule for this bucket
        for rule in reversed(self.rules):
            if rule["bucket"] == bucket:
                return rule["kind"]
        return "none"
