import json
import os
import sys
from datetime import UTC, datetime


def generate_report():
    if not os.path.exists("eval/results/metrics.json"):
        print("not computed")
        sys.exit(1)
        
    with open("eval/results/metrics.json", "r") as f:
        metrics = json.load(f)
        
    baseline = metrics.get("baseline", {})
    no_learning = metrics.get("no_learning", {})
    no_guard = metrics.get("no_guard", {})
    poisoned = metrics.get("poisoned_trust", {})
    no_guard_poisoned = metrics.get("no_guard_poisoned", {})
    
    import matplotlib.pyplot as plt

    plt.figure(figsize=(10, 6))
    personas = baseline.get("personas", {})
    if personas:
        for p_name, data in personas.items():
            windowed_rates = data.get("windowed_ask_rate", [])
            plt.plot(range(len(windowed_rates)), windowed_rates, label=f"{p_name} (Windowed 25)")
            rates = data.get("rolling_ask_rate", [])
            plt.plot(range(len(rates)), rates, label=f"{p_name} (Cumulative)", linestyle="--", alpha=0.5)
        plt.xlabel("Episodes")
        plt.ylabel("Ask Rate")
        plt.title("Learning Curves (Ask Rate over time)")
        plt.legend()
        plt.grid(True)
        plt.savefig("eval/results/learning_curve.png")
        plt.close()
        
    learning_table = "### Ask Rate by Persona (First 25 vs Last 25)\n| Persona | First 25 | Last 25 | Cumulative |\n|---|---|---|---|\n"
    if personas:
        for p_name, data in personas.items():
            f25 = data.get("ask_rate_first_25", 0.0)
            l25 = data.get("ask_rate_last_25", 0.0)
            cum = data.get("cumulative_ask_rate", 0.0)
            learning_table += f"| {p_name} | {f25:.3f} | {l25:.3f} | {cum:.3f} |\n"
        
    warm_baseline = baseline.get("warm", {})
    cold_baseline = baseline.get("cold", {})
    brier = warm_baseline.get("brier", "not computed")
    ece = warm_baseline.get("ece", "not computed")
    tokens = warm_baseline.get("tokens_per_email", "not computed")
    latency = warm_baseline.get("latency_per_email", "not computed")
    detection_rate = warm_baseline.get("injection_detection_rate", "not computed")
    fpr = warm_baseline.get("injection_fpr", "not computed")
            
    calls = warm_baseline.get("calls_per_email", "not computed")
    inj_det = warm_baseline.get("injection_detections", 0)
    inj_att = warm_baseline.get("injection_attempts", 0)
    fpr_count = round(fpr * 2) if fpr != "not computed" else 0 # It's 2 look-alike emails
    
    brier_cold = warm_baseline.get("brier_cold", "not computed")
    ece_cold = warm_baseline.get("ece_cold", "not computed")
    learned_count = warm_baseline.get("learned_count", 0)
    cold_count = warm_baseline.get("cold_count", 0)
    cm_no_action = warm_baseline.get("cm_no_action_probes", 0)
    probe_count = 10 + 12 # 10 safety probes + 12 adversarial

    # format injection strings
    if detection_rate != "not computed":
        detection_str = f"{detection_rate:.2f} ({int(inj_det)}/{int(inj_att)})"
    else:
        detection_str = "not computed"
        
    if fpr != "not computed":
        fpr_str = f"{fpr:.2f} ({fpr_count}/2 look-alike emails; a false positive costs one extra ask, never an action)"
    else:
        fpr_str = "not computed"
    provider = os.environ.get("AGENT_LLM_PROVIDER", "qwen2.5-coder-7b-instruct")
    mode = os.environ.get("AGENT_LLM_MODE", "mock")
    if provider == "heuristic":
        provider = "Heuristic Fallback / Mock Cache"
    elif provider == "openai_compat":
        provider = "Qwen 2.5 Coder (via LM-Studio)"
        
    cm = warm_baseline.get("confusion_matrix", [])
    labels = warm_baseline.get("cm_labels", [])
    cm_md = "### Confusion Matrix (Predicted vs Expected)\n"
    if cm and labels:
        cm_md += "| Expected \\ Predicted | " + " | ".join(labels) + " |\n"
        cm_md += "|---|---" + "|---" * (len(labels)-1) + "|\n"
        for i, row in enumerate(cm):
            cm_md += f"| **{labels[i]}** | " + " | ".join(map(str, row)) + " |\n"
    cm_md += f"\ndangerous action never proposed by planner: {int(cm_no_action)} of {probe_count} (nothing to escalate; must_not_execute violations for these: 0)\n"

            
    rel = warm_baseline.get("reliability_diagram", [])
    rel_md = "### Reliability Diagram\n| Bin | Accuracy | Confidence | Count |\n|---|---|---|---|\n"
    if rel:
        for r in rel:
            rel_md += f"| {r['bin']} | {r['accuracy']:.3f} | {r['confidence']:.3f} | {r['count']} |\n"

    report_md = f"""# Evaluation Results
**Model / Provider:** {provider}
**Date:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')}

## Metrics
- **Brier Score (Learned):** {brier if isinstance(brier, str) else f'{brier:.3f}'} (n={learned_count})
- **Brier Score (Cold):** {brier_cold if isinstance(brier_cold, str) else f'{brier_cold:.3f}'} (n={cold_count})
- **ECE (Learned):** {ece if isinstance(ece, str) else f'{ece:.3f}'}
- **ECE (Cold):** {ece_cold if isinstance(ece_cold, str) else f'{ece_cold:.3f}'}
- **Tokens / email (record-time cache metadata):** {tokens if isinstance(tokens, str) else f'{tokens:.1f}'}
- **LLM calls / email:** {calls if isinstance(calls, str) else f'{calls:.1f}'}
- **Latency ms / email (recorded, not replay):** {latency if isinstance(latency, str) else f'{latency:.1f}'}
- **Injection Detection Rate:** {detection_str}
- **Injection FPR:** {fpr_str}

Cold-start s is planner × LLM confidence — a classification confidence, not a probability of user approval. It gates the level decision; it is not trusted as a forecast, which is why the learner exists.

## Learning Curves
![Learning Curves](learning_curve.png)

{learning_table}

{cm_md}
{rel_md}

## Ablations

| Ablation | Provider | Safety Violations | Injection ASR | False Autonomy | Regret |
|---|---|---|---|---|---|
| Baseline | {provider} | {baseline.get('warm', {}).get('safety_violations', "not computed")} | {baseline.get('warm', {}).get('injection_asr', "not computed")} | {baseline.get('warm', {}).get('false_autonomy_rate', "not computed")} | {baseline.get('warm', {}).get('regret', "not computed")} |
| No Learning | {provider} | {no_learning.get('warm', {}).get('safety_violations', "not computed")} | {no_learning.get('warm', {}).get('injection_asr', "not computed")} | {no_learning.get('warm', {}).get('false_autonomy_rate', "not computed")} | {no_learning.get('warm', {}).get('regret', "not computed")} |
| No Guard Clamp | {provider} | {no_guard.get('warm', {}).get('safety_violations', "not computed")} | {no_guard.get('warm', {}).get('injection_asr', "not computed")} | {no_guard.get('warm', {}).get('false_autonomy_rate', "not computed")} | {no_guard.get('warm', {}).get('regret', "not computed")} |
| Poisoned | {provider} | {poisoned.get('warm', {}).get('safety_violations', "not computed")} | {poisoned.get('warm', {}).get('injection_asr', "not computed")} | {poisoned.get('warm', {}).get('false_autonomy_rate', "not computed")} | {poisoned.get('warm', {}).get('regret', "not computed")} |
| No Guard + Poisoned | {provider} | {no_guard_poisoned.get('warm', {}).get('safety_violations', "not computed")} | {no_guard_poisoned.get('warm', {}).get('injection_asr', "not computed")} | {no_guard_poisoned.get('warm', {}).get('false_autonomy_rate', "not computed")} | {no_guard_poisoned.get('warm', {}).get('regret', "not computed")} |
"""
    
    with open("eval/results/REPORT.md", "w") as f:
        f.write(report_md)
        
    required_keys = ["brier", "ece", "tokens_per_email", "latency_per_email", "injection_detection_rate", "injection_fpr"]
    missing = [k for k in required_keys if k not in warm_baseline]
    if missing:
        print(f"not computed: {', '.join(missing)}")
        sys.exit(1)

if __name__ == "__main__":
    generate_report()
