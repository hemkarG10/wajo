# WAJO: Calibrated Autonomy Email Agent

An email agent with calibrated autonomy, safety guardrails, and asymmetric learning.

## Glossary
- **LCB (Lower Confidence Bound):** The 20th percentile (0.80) of the underlying Beta distribution used for trust scoring.
- **Autonomy Levels:** AUTO, AUTO_NOTIFY, ASK, ESCALATE.

## Reproducing the Evaluation
To reproduce the evaluation results completely offline from cache (no key needed):
```bash
make setup
make test
make eval
```

## Transcripts
Transcripts of agent behavior during evaluation can be found in `transcripts/`:
- `01_ask_newsletter.md`
- `02_auto_notify_known_client.md`
- `03_ask_unknown_sender.md`
- `04_escalate_invoice_redirect.md`
- `05_injection_blocked.md`
- `06_dlp_blocks_cofounder.md`
- `07_learning_progression.md`
