# WAJO: Calibrated-Autonomy Email Agent

WAJO is a reference email agent that chooses one of four autonomy levels for every proposed action:

- `AUTO` — execute silently and retain an audit record.
- `AUTO_NOTIFY` — execute, notify the user, and expose undo when possible.
- `ASK` — prepare the action but wait for approval.
- `ESCALATE` — hold the action and surface the risk.

The learned policy may become more autonomous after repeated approvals, but the final decision is always `max(policy_level, safety_floor)`. Learning therefore cannot weaken the hard guard.

## Quick start

Requirements: Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
make setup
make lint
make test
make run
make eval
```

`make run` is a no-key, JSON-mailbox demonstration using the deterministic heuristic provider. It is dry-run by default and never sends real email. `make eval` replays committed Gemini responses completely offline, requires no API key, regenerates `eval/results/metrics.json` and `eval/results/REPORT.md`, and exits nonzero if a safety assertion fails.

The package and console entry point can also be checked directly:

```bash
make package-check
uv run agent version
uv run agent --help
```

## Measured results

The committed evaluation covers 50 hand-authored scenarios: 18 benign, 10 ambiguous, 12 adversarial, and 10 targeted safety probes. Results are averaged over three user personas and three deterministic seeds.

| Configuration | Safety violations | Injection ASR | False autonomy | Regret |
|---|---:|---:|---:|---:|
| Baseline | 0.000 | 0.000 | 0.000 | 14.867 |
| No learning | 0.000 | 0.000 | 0.000 | 20.111 |
| No guard clamp | 0.333 | 0.000 | 0.028 | 12.556 |
| Poisoned trust | 0.000 | 0.000 | 0.611 | 28.778 |

Learned calibration improved from a cold Brier score of `0.793` to `0.038`, and cold ECE of `0.841` to `0.132`. The ask rate fell from `1.000` to `0.400` for the hands-off persona and from `0.960` to `0.480` for the cautious persona over the first/last 25-event windows.

Injection detection was `6/10` (`60%`) with `2/2` look-alike false positives. The false positives only raise the autonomy floor; they cannot authorize an action. Undetected attacks remained blocked by independent action, provenance, money, sensitivity, and DLP invariants, producing zero baseline injection successes in this corpus.

See the generated [evaluation report](eval/results/REPORT.md), raw [metrics](eval/results/metrics.json), and [design document](DESIGN.md).

## Safety architecture

The planner proposes allow-listed typed actions. The independent guard then enforces minimum levels for:

- unknown actions, money movement, destructive operations, and account changes;
- all external effects, including new or body-sourced recipients;
- any heuristic or model prompt-injection signal;
- legal, HR, financial, security, regulated, or DLP-matching content;
- stale messages, hourly action caps, and the kill switch.

The executor repeats critical provenance and kill-switch checks before execution. `AGENT_PAUSED=1` blocks every action at preflight even if a malformed decision bypasses the policy layer.

## Learning

Feedback updates Beta-distributed trust at fine, sender-level, and action-level buckets. Approvals accumulate gradually; rejection halves accumulated positive evidence; undo quarters it and adds two negative observations. `escalate_was_right` lowers action trust, while `escalate_was_overkill` raises it. Evidence decays toward the prior with a 14-day half-life.

Coarse-bucket backoff is limited to `AUTO_NOTIFY` and is disabled entirely for external or money-related actions. Explicit “stop asking” rules remain subject to the hard guard.

## Providers and recording

The adapter supports `heuristic`, `gemini`, `anthropic`, `openai`, and `openai_compat`. Copy `.env.example` to `.env` only for live or record mode; replay and the default demo need no credentials.

```bash
# Live provider example after configuring .env
uv run agent run --inbox sample_inbox.json --mode live --llm gemini

# Record a new evaluation cache
make record

# Verify cache provenance
make record-check
```

Do not commit `.env`. Cache entries store structured responses and token/latency metadata, not API keys.

## Repository map

- `src/agent/` — ingestion, triage, planner, guard, learning, execution, and CLI.
- `config/` — action registry, hard-guard configuration, and learning thresholds.
- `eval/scenarios/` — hand-authored evaluation corpus.
- `eval/cache/` — recorded structured model responses used for offline replay.
- `eval/results/` — measured report, metrics, and charts.
- `tests/` — unit, property, architecture, packaging, and report-integrity tests.
- `transcripts/` — seven deterministic example interactions.

## Scope and limitations

The included mailbox is JSON-backed and the executor simulates effects. Gmail OAuth and real delivery handlers are deliberately not included, so the submission cannot accidentally send, delete, pay, or modify a real account. Evaluation uses a small hand-authored corpus and recorded model outputs; recorded latency is not replay runtime. See `DESIGN.md` for the full tradeoff discussion.

## Build the submission ZIP

```bash
make clean-clone-check
make dist
shasum -a 256 wajo-submission.zip
```

`make dist` archives tracked files only, excluding local credentials, runtime state, virtual environments, and audit logs.
