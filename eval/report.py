import json
import sys
import os
from datetime import datetime

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
    
    brier = baseline.get("brier", "not computed")
    ece = baseline.get("ece", "not computed")
    cost_latency = baseline.get("cost_latency", "not computed")
    detection_rate = baseline.get("injection_detection_rate", "not computed")
    fpr = baseline.get("injection_fpr", "not computed")
            
    provider = os.environ.get("AGENT_PROVIDER", "anthropic (claude-3-5-sonnet)")
    if os.environ.get("EVAL_MODE") == "replay" or True:
        provider = "cache (heuristic / anthropic)"

    report_md = f"""# Evaluation Results
**Model / Provider:** {provider}
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Metrics
- **Brier Score:** {brier}
- **ECE:** {ece}
- **Cost / Latency:** {cost_latency}
- **Injection Detection Rate:** {detection_rate}
- **Injection FPR:** {fpr}

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
        
    required_keys = ["brier", "ece", "cost_latency", "injection_detection_rate", "injection_fpr"]
    missing = [k for k in required_keys if k not in baseline]
    if missing:
        print(f"not computed: {', '.join(missing)}")
        sys.exit(1)

if __name__ == "__main__":
    generate_report()
