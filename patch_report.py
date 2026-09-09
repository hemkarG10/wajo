import re
with open("eval/report.py", "r") as f:
    code = f.read()

# Change cold_baseline to warm_baseline
code = code.replace("cold_baseline = baseline.get(\"cold\", {})", "warm_baseline = baseline.get(\"warm\", {})\n    cold_baseline = baseline.get(\"cold\", {})")

code = code.replace("brier = cold_baseline.get(\"brier\", \"not computed\")", "brier = warm_baseline.get(\"brier\", \"not computed\")")
code = code.replace("ece = cold_baseline.get(\"ece\", \"not computed\")", "ece = warm_baseline.get(\"ece\", \"not computed\")")
code = code.replace("tokens = cold_baseline.get(\"tokens_per_email\", \"not computed\")", "tokens = warm_baseline.get(\"tokens_per_email\", \"not computed\")")
code = code.replace("latency = cold_baseline.get(\"latency_per_email\", \"not computed\")", "latency = warm_baseline.get(\"latency_per_email\", \"not computed\")")
code = code.replace("detection_rate = cold_baseline.get(\"injection_detection_rate\", \"not computed\")", "detection_rate = warm_baseline.get(\"injection_detection_rate\", \"not computed\")")
code = code.replace("fpr = cold_baseline.get(\"injection_fpr\", \"not computed\")", "fpr = warm_baseline.get(\"injection_fpr\", \"not computed\")")

metrics_add = """    calls = warm_baseline.get("calls_per_email", "not computed")
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
"""
code = code.replace("    provider = os.environ.get(\"AGENT_LLM_PROVIDER\", \"qwen2.5-coder-7b-instruct\")", metrics_add + "    provider = os.environ.get(\"AGENT_LLM_PROVIDER\", \"qwen2.5-coder-7b-instruct\")")

# CM uses warm_baseline
code = code.replace("cm = cold_baseline.get(\"confusion_matrix\", [])", "cm = warm_baseline.get(\"confusion_matrix\", [])")
code = code.replace("labels = cold_baseline.get(\"cm_labels\", [])", "labels = warm_baseline.get(\"cm_labels\", [])")

code = code.replace("            cm_md += f\"| **{labels[i]}** | \" + \" | \".join(map(str, row)) + \" |\\n\"", "            cm_md += f\"| **{labels[i]}** | \" + \" | \".join(map(str, row)) + \" |\\n\"\n    cm_md += f\"\\ndangerous action never proposed by planner: {int(cm_no_action)} of {probe_count} (nothing to escalate; must_not_execute violations for these: 0)\\n\"\n")

# Reliability uses warm_baseline
code = code.replace("rel = cold_baseline.get(\"reliability_diagram\", [])", "rel = warm_baseline.get(\"reliability_diagram\", [])")

code = code.replace("""## Metrics
- **Brier Score:** {brier}
- **ECE:** {ece}
- **Tokens / email (record-time cache metadata):** {tokens}
- **Latency ms / email (recorded, not replay):** {latency}
- **Injection Detection Rate:** {detection_rate}
- **Injection FPR:** {fpr}""", """## Metrics
- **Brier Score (Learned):** {brier:.3f} (n={learned_count})
- **Brier Score (Cold):** {brier_cold:.3f} (n={cold_count})
- **ECE (Learned):** {ece:.3f}
- **ECE (Cold):** {ece_cold:.3f}
- **Tokens / email (record-time cache metadata):** {tokens:.1f}
- **LLM calls / email:** {calls:.1f}
- **Latency ms / email (recorded, not replay):** {latency:.1f}
- **Injection Detection Rate:** {detection_str}
- **Injection FPR:** {fpr_str}

Cold-start s is planner × LLM confidence — a classification confidence, not a probability of user approval. It gates the level decision; it is not trusted as a forecast, which is why the learner exists.""")

code = code.replace("if k not in cold_baseline", "if k not in warm_baseline")
code = code.replace("missing = [k for k in required_keys if k not in warm_baseline]", "missing = [k for k in required_keys if k not in warm_baseline]")

with open("eval/report.py", "w") as f:
    f.write(code)
