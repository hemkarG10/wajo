from agent.models import InjectionSignals, Situation, TriageOutput
from agent.planner import PlannerOut


def test_no_additional_properties_in_schema():
    schemas = [
        Situation.model_json_schema(),
        InjectionSignals.model_json_schema(),
        PlannerOut.model_json_schema(),
        TriageOutput.model_json_schema()
    ]
    
    def check_dict(d: dict):
        if "additionalProperties" in d:
            assert d["additionalProperties"] is False or d["additionalProperties"] is None, f"Found additionalProperties: {d}"
        if d.get("type") == "object" and "properties" not in d:
            assert False, f"Found free-form dict: {d}"
        
        for k, v in d.items():
            if isinstance(v, dict):
                check_dict(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        check_dict(item)

    for s in schemas:
        check_dict(s)
