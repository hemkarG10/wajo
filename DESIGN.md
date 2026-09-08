# Calibrated-Autonomy Email Agent - Design Decisions

This document captures the key architectural decisions and metrics for the Calibrated-Autonomy Email Agent.

## Core Philosophy

The agent is built around the principle of **calibrated autonomy**, governed by a **two-tier decision architecture**:
1. **Learned Policy (The Brain):** Suggests how much autonomy to take based on historical feedback and Bayesian confidence.
2. **Safety Floor (The Guard):** Enforces hard invariant rules that cannot be bypassed, even if the Learned Policy is perfectly confident.

## Architecture

The system pipeline is completely decoupled into functional stages:
1. **Ingest:** Parses raw JSON emails.
2. **Injection Scan (Heuristics + LLM Judge):** Flags malicious instructions or prompt injections.
3. **Triage:** Uses structured LLM generation to classify intent and urgency.
4. **Planner:** Proposes actions and extracts intent arguments. It securely marks the provenance of parameters (e.g. `UNTRUSTED` if it comes directly from the email body).
5. **Decide:** Computes the policy level (using Lower Confidence Bound from the Beta distribution) and the Guard floor, taking the `max()` (most restrictive) of the two.
6. **Execute:** Executes the action or refuses it based on `untrusted_destinations` or kill switches.

## Safety Floor Invariants

The Safety Floor implements the following constraints (see `src/agent/guard.py`):
- **I1:** Money transfers never happen autonomously (`ESCALATE`).
- **I2:** Irreversible, destructive actions always escalate (`ESCALATE`).
- **I3:** External emails are never sent silently (`AUTO_NOTIFY`).
- **I4:** New external recipients require human approval (`ASK`).
- **I5:** Untrusted provenance cannot steer external actions (`ESCALATE` enforced in Executor).
- **I6:** Suspected injection freezes outbound actions (`ESCALATE`).
- **I7:** Sensitive categories stay human (`ESCALATE` for regulated external actions, `ASK` otherwise).
- **I8:** DLP (Data Loss Prevention) on egress (`ESCALATE`).
- **I9:** Rate caps and staleness checks (`ASK`).
- **I11:** Global kill switch (`ASK`).

## Learning Mechanism

The agent uses a **Beta Distribution (Bayesian update)** to learn user preferences:
- Successes increment $\alpha$.
- Failures increment $\beta$.
- Decisions are made using the **Lower Confidence Bound (LCB)** to require high certainty for `AUTO` or `AUTO_NOTIFY`.
- A decay factor ($\lambda$) ensures older behavior decays, preferring recent feedback.

## Key Metrics & Results

The evaluation harness tests the agent against a corpus of benign, ambiguous, adversarial, and safety probe scenarios. 

The evaluation measures:
- **Safety Violations:** The rate at which the agent bypasses invariant rules.
- **False Autonomy Rate:** The rate at which the agent wrongly takes autonomous action for ambiguous requests.
- **Injection ASR:** The attack success rate of prompt injections against the agent's planner and triage components.

For the latest metrics across the baseline and ablation studies (e.g. poisoning the learner, removing the guard), please see [`REPORT.md`](REPORT.md).

---
*Developed for the take-home project.*
