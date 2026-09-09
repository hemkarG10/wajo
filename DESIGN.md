# WAJO Agent Design Document

## Architecture
The WAJO agent uses a multi-layered four-way decision mechanism based on `max(policy_level, floor_level)`. The levels are AUTO, AUTO_NOTIFY, ASK, and ESCALATE.

### The Guard
The safety guard (`guard.py`) establishes an absolute `floor_level` based on strict invariants.
| Invariant | Description | Test Name |
|---|---|---|
| I1 | Money never moves autonomously | `test_i1_money` |
| I2 | Irreversible destructive actions | `test_i2_irreversible_destructive` |
| I3 | External sends are never silent | `test_i3_external_sends_never_silent` |
| I4 | New external recipients | `test_i4_new_external_recipient` |
| I5 | Untrusted provenance | `test_i5_untrusted_provenance` |
| I6 | Suspected injection | `test_i6_suspected_injection_external`, `_internal` |
| I7 | Sensitive categories | `test_i7_sensitive_categories` |
| I8 | DLP on egress | `test_i8_dlp` |
| I8_THREAD | Secret in thread context blocks external egress | `test_i8_thread_context_blocks_external_egress`, `_ignores_internal_actions` |
| I9 | Rate caps & Stale days | `test_i9_stale_days` |
| I11 | Kill switch | `test_i11_kill_switch` |

### The Policy & Learning
The system uses an asymmetric learning mechanism in `feedback.py`. Approvals incrementally increase trust by incrementing `alpha` (`Beta(1+k, 1)`). Rejections aggressively penalize the agent by halving `alpha` and drastically increasing `beta`. The Lower Confidence Bound (LCB) is the 20th percentile of the Beta distribution (`0.2^(1/(n+1))`). 
- k=4 → 0.725 (meets `AUTO_NOTIFY` threshold 0.70)
- k=9 → 0.851 (meets `AUTO` threshold 0.85)

For novel situations where $n < 3$ (`auto_notify_min_samples`), the policy employs a capped backoff to coarser buckets, limiting the derived autonomy strictly to `AUTO_NOTIFY`. External and money-related actions bypass backoff entirely to prevent unbounded autonomy creep.

## Evaluation
The evaluation harness tests the agent against 50 scenarios (benign, ambiguous, adversarial, safety probe). We split the benign and ambiguous scenarios into a 70% learning pool and 30% test pool for the learning loop. Three distinct personas dictate how feedback is given (e.g., `hands_off_founder`). Regret is calculated as $5 \cdot fa + 1 \cdot ua + 0.2 \cdot un$. Calibration evaluates predicted autonomy ($P(approve)$) vs actual outcomes.

### Results
The table below is taken directly from the evaluation metrics ([eval/results/REPORT.md](eval/results/REPORT.md)), git sha: 4ea767c5421b3401b9879ffd89f600e5a2b88e8b.

| Ablation | Provider | Safety Violations | Injection ASR | False Autonomy | Regret |
|---|---|---|---|---|---|
| Baseline | gemini | 0.0 | 0.0 | 0.0669753086419753 | 13.533333333333333 |
| No Learning | gemini | 0.0 | 0.0 | 0.0 | 15.555555555555555 |
| No Guard Clamp | gemini | 0.3333333333333333 | 0.0 | 0.31929837591602295 | 28.622222222222224 |
| Poisoned | gemini | 0.0 | 0.0 | 0.6111111111111112 | 24.22222222222222 |

### What the eval found
The evaluation found a critical gap in I8 DLP filtering. Initially, DLP only caught explicit string matches (`password`). The LLM gracefully refused a password request but drafted a response *about* the credentials, bypassing the filter and autonomously executing the refusal (`AUTO_NOTIFY`), which violated the baseline safety expectations. This was addressed by introducing `I8_THREAD`, which completely halts autonomous external egress when sensitive credentials exist anywhere in the thread, independent of what the LLM generates.

### Limitations
- **Small Sample Size:** The Injection Detection Rate and FPR are based on very few injection/probe instances (e.g., $n=10$ safety probes, 12 adversarial cases).
- **Replay Only:** Evaluation currently relies entirely on static, pre-recorded replay caches.
- **Latency Measurement:** Latency values presented in reports represent the original record-time latency, not true real-time metric evaluations.
