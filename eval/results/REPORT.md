# Evaluation Results
**Model / Provider:** Heuristic Fallback / Mock Cache
**Date:** 2026-09-06 05:32:59

## Metrics
- **Brier Score:** 0.16490985576923076
- **ECE:** 0.060817307692307664
- **Cost / Latency:** not computed / not computed
- **Injection Detection Rate:** 0.0
- **Injection FPR:** 0.0

## Learning Curves
![Learning Curves](learning_curve.png)

### Confusion Matrix (Predicted vs Expected)
| Expected \ Predicted | AUTO | AUTO_NOTIFY | ASK | ESCALATE |
|---|---|---|---|---|
| **AUTO** | 0 | 0 | 34 | 11 |
| **AUTO_NOTIFY** | 0 | 0 | 2 | 0 |
| **ASK** | 0 | 0 | 16 | 9 |
| **ESCALATE** | 0 | 0 | 28 | 4 |

### Reliability Diagram
| Bin | Accuracy | Confidence | Count |
|---|---|---|---|
| 0.1-0.2 | 0.105 | 0.200 | 19 |
| 0.2-0.3 | 0.364 | 0.254 | 77 |
| 0.3-0.4 | 0.250 | 0.372 | 8 |


## Ablations

| Ablation | Provider | Safety Violations | Injection ASR | False Autonomy | Regret |
|---|---|---|---|---|---|
| Baseline | Heuristic Fallback / Mock Cache | 0 | 0.0 | 0.0 | 47.0 |
| No Learning | Heuristic Fallback / Mock Cache | 0 | 0.0 | 0.0 | 47.0 |
| No Guard Clamp | Heuristic Fallback / Mock Cache | 0 | 0.0 | 0.0 | 47.0 |
| Poisoned | Heuristic Fallback / Mock Cache | 0 | 0.0 | 0.0 | 47.0 |
