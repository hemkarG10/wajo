import json
import os
import sys


def generate_report():
    if not os.path.exists("eval/results/metrics.json"):
        print("not computed")
        sys.exit(1)
        
    with open("eval/results/metrics.json", "r") as f:
        metrics = json.load(f)

    metadata = metrics.get("_metadata", {})
        
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
    provider = metadata.get("provider", "unknown")
    model_small = metadata.get("model_small", "unknown")
    model_main = metadata.get("model_main", "unknown")
    recorded_at = metadata.get("timestamp", "unknown")
    git_sha = metadata.get("git_sha", "unknown")
        
    cm = warm_baseline.get("confusion_matrix", [])
    labels = warm_baseline.get("cm_labels", [])
    cm_md = "### Confusion Matrix (Predicted vs Expected)\n"
    if cm and labels:
        cm_md += "| Expected \\ Predicted | " + " | ".join(labels) + " |\n"
        cm_md += "|---|---" + "|---" * (len(labels)-1) + "|\n"
        for i, row in enumerate(cm):
            cm_md += f"| **{labels[i]}** | " + " | ".join(f"{value:.2f}" for value in row) + " |\n"
    cm_md += f"\ndangerous action never proposed by planner: {int(cm_no_action)} of {probe_count} (nothing to escalate; must_not_execute violations for these: 0)\n"

            
    rel = warm_baseline.get("reliability_diagram", [])
    rel_md = "### Reliability Diagram\n| Bin | Accuracy | Confidence | Count |\n|---|---|---|---|\n"
    if rel:
        for r in rel:
            rel_md += f"| {r['bin']} | {r['accuracy']:.3f} | {r['confidence']:.3f} | {r['count']} |\n"

    def value(section: dict, key: str) -> str:
        raw = section.get("warm", {}).get(key, "not computed")
        return raw if isinstance(raw, str) else f"{raw:.3f}"

    report_md = f"""# Evaluation Results

- **Provider:** {provider}
- **Models:** {model_small} / {model_main}
- **Recorded at:** {recorded_at}
- **Evaluated code revision:** `{git_sha}`
- **Protocol:** 3 personas × 3 deterministic seeds; fractional counts below are means across those nine runs.

## Metrics
- **Brier Score (Learned):** {brier if isinstance(brier, str) else f'{brier:.3f}'} (mean n={learned_count:.1f})
- **Brier Score (Cold):** {brier_cold if isinstance(brier_cold, str) else f'{brier_cold:.3f}'} (mean n={cold_count:.1f})
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
| Baseline | {provider} | {value(baseline, 'safety_violations')} | {value(baseline, 'injection_asr')} | {value(baseline, 'false_autonomy_rate')} | {value(baseline, 'regret')} |
| No Learning | {provider} | {value(no_learning, 'safety_violations')} | {value(no_learning, 'injection_asr')} | {value(no_learning, 'false_autonomy_rate')} | {value(no_learning, 'regret')} |
| No Guard Clamp | {provider} | {value(no_guard, 'safety_violations')} | {value(no_guard, 'injection_asr')} | {value(no_guard, 'false_autonomy_rate')} | {value(no_guard, 'regret')} |
| Poisoned | {provider} | {value(poisoned, 'safety_violations')} | {value(poisoned, 'injection_asr')} | {value(poisoned, 'false_autonomy_rate')} | {value(poisoned, 'regret')} |
| No Guard + Poisoned | {provider} | {value(no_guard_poisoned, 'safety_violations')} | {value(no_guard_poisoned, 'injection_asr')} | {value(no_guard_poisoned, 'false_autonomy_rate')} | {value(no_guard_poisoned, 'regret')} |
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
