# Calibrated-Autonomy Email Agent

This repository contains the implementation of a proactive AI email agent that manages an inbox with a calibrated autonomy decision model.

## Quickstart

This project uses `uv` for dependency management and Python 3.12.

1. **Setup:**
   ```bash
   make setup
   ```
   (This runs `uv sync` to install dependencies)

2. **Run on a sample inbox:**
   ```bash
   make run
   ```
   Alternatively:
   ```bash
   uv run python src/agent/cli.py run --inbox sample_inbox.json --mode replay
   ```

3. **Generate transcripts:**
   ```bash
   make transcripts
   ```

## How to Reproduce Eval Numbers

To evaluate the agent's performance, safety, and calibration offline, run the evaluation harness:

```bash
make eval
```

This runs the eval suites offline without an API key by using cached LLM responses in `eval/cache/`. The results, including safety violations (which are enforced to 0) and calibration metrics, are output to `eval/results/REPORT.md`.

## System Design

For a full breakdown of the architecture, trade-offs, and invariants enforced by the system, please see [DESIGN.md](./DESIGN.md).

## Glossary

- **Floor** — the minimum human involvement the Guard requires for a (situation, action). Static, versioned, unlearnable.
- **Policy level** — what the learned layer would do if unconstrained.
- **Final level** — `max(policy level, floor)`.
- **Bucket** — the context key for trust statistics: `(action, sender_class, intent)` with hierarchical backoff.
- **LCB** — lower confidence bound (10th percentile) of the Beta posterior over approval probability.
- **Provenance** — where each action parameter's value came from (user / system / thread / untrusted).
- **False autonomy** — an autonomous action the user would have rejected. The number the whole design exists to keep near zero.
