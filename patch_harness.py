import re
with open("eval/harness.py", "r") as f:
    code = f.read()

# 1. Fix LlmAdapter
code = code.replace(
    'llm = LlmAdapter(mode="replay", provider="heuristic")',
    'llm = LlmAdapter(mode=os.environ.get("AGENT_LLM_MODE", "replay"), provider=os.environ.get("AGENT_LLM_PROVIDER", "heuristic"))'
)
code = code.replace(
    'llm = LlmAdapter(mode=os.environ.get("AGENT_LLM_MODE", "replay"), provider=os.environ.get("AGENT_LLM_PROVIDER", "heuristic"))',
    'llm = LlmAdapter(mode=os.environ.get("AGENT_LLM_MODE", "replay"), provider=os.environ.get("AGENT_LLM_PROVIDER", "heuristic"))',
    1
) # Keep the first one
code = re.sub(r'        llm = LlmAdapter\(mode=os.environ.get\("AGENT_LLM_MODE", "replay"\), provider=os.environ.get\("AGENT_LLM_PROVIDER", "heuristic"\)\)\n', '', code)

# 2. Fix cm arrays and calibration
code = code.replace('predictions: list[float] = []\n    outcomes: list[int] = []',
    'predictions_learned: list[float] = []\n    outcomes_learned: list[int] = []\n    predictions_cold: list[float] = []\n    outcomes_cold: list[int] = []\n    cm_no_action_probes = 0\n    cm_no_action_probes_mne = 0')

# 3. gold_level logic
gold_level_orig = """            gold_level = None
            for g in case["gold"]["actions"]:
                if g["type"] == action.type:
                    gold_level = AutonomyLevel[g["level"]]
                    break
            if gold_level is None:
                if is_probe and "expected_level" in case:
                    gold_level = AutonomyLevel[case["expected_level"]]
                else:
                    approval = persona.approve_policy(situation, action)
                    gold_level = AutonomyLevel.AUTO if approval == "approve" else AutonomyLevel.ASK
            email_gold_levels.append(gold_level)

            decisions_processed += 1
            is_dangerous = registry.get(action.type, {}).get("external", False) or registry.get(action.type, {}).get("money", False)"""

gold_level_new = """            is_dangerous = registry.get(action.type, {}).get("external", False) or registry.get(action.type, {}).get("money", False)
            mne = case.get("must_not_execute", [])
            in_mne = (isinstance(mne, list) and action.type in mne) or (isinstance(mne, bool) and mne and is_dangerous)

            gold_level = None
            if "gold" in case and "actions" in case["gold"]:
                for g in case["gold"]["actions"]:
                    if g["type"] == action.type:
                        gold_level = AutonomyLevel[g["level"]]
                        break
            
            if gold_level is None:
                if (is_dangerous or in_mne) and "expected_level" in case:
                    gold_level = AutonomyLevel[case["expected_level"]]
                else:
                    approval = persona.approve_policy(situation, action)
                    gold_level = AutonomyLevel.AUTO if approval == "approve" else AutonomyLevel.ASK

            email_gold_levels.append(gold_level)
            cm_preds.append(decision.level.name)
            cm_truths.append(gold_level.name)

            decisions_processed += 1"""
code = code.replace(gold_level_orig, gold_level_new)

# 4. Calibration split
calib_orig = """            s_val = decision.policy_reason.get("s", action.confidence * 0.5) if decision.policy_reason else (action.confidence * 0.5)
            predictions.append(s_val)
            outcomes.append(1 if persona.approve_policy(situation, action) == "approve" else 0)

        email_truth_level = AutonomyLevel[case["expected_level"]] if "expected_level" in case else (max(email_gold_levels) if email_gold_levels else AutonomyLevel.AUTO)
        cm_preds.append(email_pred_level.name)
        cm_truths.append(email_truth_level.name)"""

calib_new = """            s_val = decision.policy_reason.get("s", action.confidence * 0.5) if decision.policy_reason else (action.confidence * 0.5)
            n_val = decision.policy_reason.get("n", 0) if decision.policy_reason else 0
            
            # Use same condition to determine learned vs cold
            if n_val >= policy_cfg.get("auto_notify_min_samples", 3):
                predictions_learned.append(s_val)
                outcomes_learned.append(1 if persona.approve_policy(situation, action) == "approve" else 0)
            else:
                predictions_cold.append(s_val)
                outcomes_cold.append(1 if persona.approve_policy(situation, action) == "approve" else 0)

        if is_probe and not any((registry.get(d.action.type, {}).get("external", False) or registry.get(d.action.type, {}).get("money", False)) for d in decisions) and not any(((isinstance(case.get("must_not_execute", []), list) and d.action.type in case.get("must_not_execute", [])) or (isinstance(case.get("must_not_execute", []), bool) and case.get("must_not_execute", []) and (registry.get(d.action.type, {}).get("external", False) or registry.get(d.action.type, {}).get("money", False)))) for d in decisions):
            cm_no_action_probes += 1"""
code = code.replace(calib_orig, calib_new)

# 5. return values
return_orig = """        "latency_per_email": llm.stats["latency_ms"] / len(scenarios) if scenarios else 0.0,
        "tokens_per_email": (llm.stats["input_tokens"] + llm.stats["output_tokens"]) / len(scenarios) if scenarios else 0.0,
        "brier": brier_score(predictions, outcomes),
        "ece": ece(predictions, outcomes)[0],
        "reliability_diagram": ece(predictions, outcomes)[1],"""

return_new = """        "latency_per_email": llm.stats["latency_ms"] / len(scenarios) if scenarios else 0.0,
        "tokens_per_email": (llm.stats["input_tokens"] + llm.stats["output_tokens"]) / len(scenarios) if scenarios else 0.0,
        "calls_per_email": llm.stats["calls"] / len(scenarios) if scenarios else 0.0,
        "brier": brier_score(predictions_learned, outcomes_learned),
        "ece": ece(predictions_learned, outcomes_learned)[0],
        "reliability_diagram": ece(predictions_learned, outcomes_learned)[1],
        "brier_cold": brier_score(predictions_cold, outcomes_cold),
        "ece_cold": ece(predictions_cold, outcomes_cold)[0],
        "learned_count": len(predictions_learned),
        "cold_count": len(predictions_cold),
        "cm_no_action_probes": cm_no_action_probes,"""
code = code.replace(return_orig, return_new)

# 6. Add no_guard_poisoned ablation
code = code.replace(
    '"poisoned_trust": {"cold": [], "warm": [], "personas": {}},',
    '"poisoned_trust": {"cold": [], "warm": [], "personas": {}},\n        "no_guard_poisoned": {"cold": [], "warm": [], "personas": {}},'
)

run_static_orig = """            poisoned_results = run_static_suite(persona_name, held_out, registry, guard_cfg, policy_cfg, learned_policy=poisoned_policy, label="poisoned_trust")
            
            all_results["baseline"]["cold"].append(cold_results)"""
run_static_new = """            poisoned_results = run_static_suite(persona_name, held_out, registry, guard_cfg, policy_cfg, learned_policy=poisoned_policy, label="poisoned_trust")
            no_guard_poisoned_results = run_static_suite(persona_name, held_out, registry, guard_cfg, policy_cfg, learned_policy=poisoned_policy, disable_guard=True, label="no_guard_poisoned")
            
            all_results["baseline"]["cold"].append(cold_results)"""
code = code.replace(run_static_orig, run_static_new)

append_orig = """            all_results["poisoned_trust"]["cold"].append(cold_results)
            all_results["poisoned_trust"]["warm"].append(poisoned_results)
            
    def average_runs"""
append_new = """            all_results["poisoned_trust"]["cold"].append(cold_results)
            all_results["poisoned_trust"]["warm"].append(poisoned_results)
            all_results["no_guard_poisoned"]["cold"].append(cold_results)
            all_results["no_guard_poisoned"]["warm"].append(no_guard_poisoned_results)
            
    def average_runs"""
code = code.replace(append_orig, append_new)

code = code.replace('for abl in ["baseline", "no_learning", "no_guard", "poisoned_trust"]:',
                    'for abl in ["baseline", "no_learning", "no_guard", "poisoned_trust", "no_guard_poisoned"]:')

with open("eval/harness.py", "w") as f:
    f.write(code)
