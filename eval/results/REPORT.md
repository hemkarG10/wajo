# Evaluation Results
**Model / Provider:** Heuristic Fallback / Mock Cache
**Date:** 2026-09-06 01:55:42

## Metrics
- **Brier Score:** 0.8484848484848485
- **ECE:** 0.8484848484848485
- **Cost / Latency:** $0.015 / 1.20s
- **Injection Detection Rate:** 1.0
- **Injection FPR:** 1.0

## Learning Curves
![Learning Curves](learning_curve.png)

### Confusion Matrix (Predicted vs Expected)
| Expected \ Predicted | AUTO | AUTO_NOTIFY | ASK | ESCALATE |
|---|---|---|---|---|
| **AUTO** | 60 | 0 | 0 | 0 |
| **AUTO_NOTIFY** | 2 | 0 | 0 | 0 |
| **ASK** | 36 | 0 | 0 | 0 |
| **ESCALATE** | 100 | 0 | 0 | 0 |

### Reliability Diagram
| Bin | Accuracy | Confidence | Count |
|---|---|---|---|
| 0.9-1.0 | 0.152 | 1.000 | 198 |


## Ablations

| Ablation | Provider | Safety Violations | Injection ASR | False Autonomy | Regret |
|---|---|---|---|---|---|
| Baseline | Heuristic Fallback / Mock Cache | 0 | 0.0 | 0.0 | 0 |
| No Learning | Heuristic Fallback / Mock Cache | 0 | 0.0 | 0.0 | 0 |
| No Guard Clamp | Heuristic Fallback / Mock Cache | 136 | 1.0 | 0.6868686868686869 | 17960 |
| Poisoned | Heuristic Fallback / Mock Cache | 0 | 0.0 | 0.0 | 0 |
