# Evaluation Results
**Model / Provider:** Heuristic Fallback / Mock Cache
**Date:** 2026-09-06 06:09:06

## Metrics
- **Brier Score:** 0.190171568627451
- **ECE:** 0.13758169934640524
- **Cost / Latency:** 0.0 / 0.0
- **Injection Detection Rate:** 0.6666666666666666
- **Injection FPR:** 0.0

## Learning Curves
![Learning Curves](learning_curve.png)

### Confusion Matrix (Predicted vs Expected)
| Expected \ Predicted | AUTO | AUTO_NOTIFY | ASK | ESCALATE |
|---|---|---|---|---|
| **AUTO** | 0 | 0 | 67 | 23 |
| **AUTO_NOTIFY** | 0 | 0 | 2 | 0 |
| **ASK** | 0 | 0 | 36 | 8 |
| **ESCALATE** | 0 | 0 | 16 | 1 |

### Reliability Diagram
| Bin | Accuracy | Confidence | Count |
|---|---|---|---|


## Ablations

| Ablation | Provider | Safety Violations | Injection ASR | False Autonomy | Regret |
|---|---|---|---|---|---|
| Baseline | Heuristic Fallback / Mock Cache | 0 | 0.0 | 0.46511627906976744 | 173.2 |
| No Learning | Heuristic Fallback / Mock Cache | 0 | 0.0 | 0.0 | 92.0 |
| No Guard Clamp | Heuristic Fallback / Mock Cache | 20 | 0.0 | 0.4027777777777778 | 202.2 |
| Poisoned | Heuristic Fallback / Mock Cache | 0 | 0.0 | 0.0 | 92.0 |
