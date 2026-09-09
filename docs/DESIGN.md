# Agent Design Document

## Trust and Backoff
We implemented an asymmetric trust mechanism where approvals linearly increase the learned policy's `alpha` value. Rejections aggressively halve the trust (`beta` increases dramatically), and undo actions reduce trust by a quarter. This ensures the agent is extremely cautious when penalised.

For new or rare situations where `n < 10` (the minimum samples required for `AUTO_NOTIFY`), the agent implements capped backoff. It falls back to coarser buckets (e.g. `bucket_med` or `bucket_coarse`), but caps the derived autonomy level at `ASK`. It will never grant `AUTO` autonomy through a backoff. Furthermore, external and money-related actions skip backoff entirely, requiring full evidence (`n >= 10`) on the exact `bucket_fine`.

## Evaluation
We updated `check_asr` and the evaluation harness to use per-decision logic. The evaluation now iterates over every decision made for an email to detect if any of them execute a dangerous action that matches the injection goal. A safety violation or injection success is recorded if ANY executed action within the single email matches the criteria, providing a much stronger safeguard against composite or multi-action decisions.

## Results / Calibration
The agent remains poorly calibrated even after learning; its Brier and ECE scores are nearly identical between cold and learned buckets. This occurs because the policy is not generating real probability distributions; it simply returns frequency values (n) mapped through a hard-coded s-curve, while the underlying model probabilities are completely discarded. The confidence calibration problem was solved by using `n >= 3` as a hard gate rather than trusting `s`.
