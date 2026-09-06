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
    
    import matplotlib.pyplot as plt

    plt.figure(figsize=(10, 6))
    personas = baseline.get("personas", {})
    if personas:
        for p_name, data in personas.items():
            rates = data.get("rolling_ask_rate", [])
            plt.plot(range(len(rates)), rates, label=p_name)
        plt.xlabel("Episodes")
        plt.ylabel("Rolling Ask Rate")
        plt.title("Learning Curves (Ask Rate over time)")
        plt.legend()
        plt.grid(True)
        plt.savefig("eval/results/learning_curve.png")
        plt.close()
        
    brier = baseline.get("brier", "not computed")
    ece = baseline.get("ece", "not computed")
    cost = baseline.get("cost_per_email", "not computed")
    latency = baseline.get("latency_per_email", "not computed")
    detection_rate = baseline.get("injection_detection_rate", "not computed")
    fpr = baseline.get("injection_fpr", "not computed")
            
    provider = os.environ.get("AGENT_PROVIDER", "anthropic (claude-3-5-sonnet)")
    if os.environ.get("EVAL_MODE") == "replay" or True:
        provider = "cache (heuristic / anthropic)"
        
    cm = baseline.get("confusion_matrix", [])
    labels = baseline.get("cm_labels", [])
    cm_md = "### Confusion Matrix (Predicted vs Expected)\n"
    if cm and labels:
        cm_md += "| Expected \\ Predicted | " + " | ".join(labels) + " |\n"
        cm_md += "|---|---" + "|---" * (len(labels)-1) + "|\n"
        for i, row in enumerate(cm):
            cm_md += f"| **{labels[i]}** | " + " | ".join(map(str, row)) + " |\n"
            
    rel = baseline.get("reliability_diagram", [])
    rel_md = "### Reliability Diagram\n| Bin | Accuracy | Confidence | Count |\n|---|---|---|---|\n"
    if rel:
        for r in rel:
            rel_md += f"| {r['bin']} | {r['accuracy']:.3f} | {r['confidence']:.3f} | {r['count']} |\n"

    report_md = f"""# Evaluation Results
**Model / Provider:** {provider}
**Date:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')}

## Metrics
- **Brier Score:** {brier}
- **ECE:** {ece}
- **Cost / Latency:** ${cost:.3f} / {latency:.2f}s
- **Injection Detection Rate:** {detection_rate}
- **Injection FPR:** {fpr}

## Learning Curves
![Learning Curves](learning_curve.png)

{cm_md}
{rel_md}

## Ablations

| Ablation | Provider | Safety Violations | Injection ASR | False Autonomy | Regret |
|---|---|---|---|---|---|
| Baseline | {provider} | {baseline.get('safety_violations', "not computed")} | {baseline.get('injection_asr', "not computed")} | {baseline.get('false_autonomy_rate', "not computed")} | {baseline.get('regret', "not computed")} |
| No Learning | {provider} | {no_learning.get('safety_violations', "not computed")} | {no_learning.get('injection_asr', "not computed")} | {no_learning.get('false_autonomy_rate', "not computed")} | {no_learning.get('regret', "not computed")} |
| No Guard Clamp | {provider} | {no_guard.get('safety_violations', "not computed")} | {no_guard.get('injection_asr', "not computed")} | {no_guard.get('false_autonomy_rate', "not computed")} | {no_guard.get('regret', "not computed")} |
| Poisoned | {provider} | {poisoned.get('safety_violations', "not computed")} | {poisoned.get('injection_asr', "not computed")} | {poisoned.get('false_autonomy_rate', "not computed")} | {poisoned.get('regret', "not computed")} |
"""
    
    with open("eval/results/REPORT.md", "w") as f:
        f.write(report_md)
        
    required_keys = ["brier", "ece", "cost_per_email", "injection_detection_rate", "injection_fpr"]
    missing = [k for k in required_keys if k not in baseline]
    if missing:
        print(f"not computed: {', '.join(missing)}")
        sys.exit(1)

if __name__ == "__main__":
    generate_report()
