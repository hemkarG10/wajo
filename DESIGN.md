# System Design & Architecture

## Core Invariants & Safety Bounds
The agent enforces a pure, static safety floor (`src/agent/guard.py`) that strictly overrides the LLM planner. Key invariants include:
1. **Money & Exfiltration:** All actions involving money transfer (`pay`, `purchase`, `wire`) or severe exfiltration risk require absolute human approval (`ESCALATE`), regardless of the LLM's confidence.
2. **Untrusted Provenance:** External actions with parameters derived from untrusted inputs (e.g., an email body) are halted at execution unless strictly isolated. Taint-tracking explicitly prevents this.
3. **Injection Defence:** The agent features a dual-layer injection scanner (heuristics + LLM-as-a-judge). A positive identification forces an `ESCALATE` or `ASK` floor, depending on external interactions.

## Trade-offs
1. **Deterministic Guard vs Flexibility:** The guard is hard-coded via `config/guard.yaml` and purely functional Python. This sacrifices runtime flexibility (the LLM cannot invent new capabilities or override safety rules) in exchange for absolute determinism.
2. **Stateless Pipelines vs Multi-agent graph:** The pipeline (`Triage -> Planner -> Decide -> Execute`) is stateless and linear, without cyclic reasoning. While LangGraph/CrewAI could provide iterative refinement, they obscure provenance. The linear pipeline enforces clean boundaries for taint tracking and evaluation.
3. **Pessimistic Caching for Eval:** The offline evaluation harness (`eval/runner.py`) uses strict SHA256 caching of prompt combinations. This prevents hallucinated variations during CI/CD, trading prompt flexibility for reliable, non-flaky test runs.

## Future Improvements
1. **Human-in-the-Loop Feedback UI:** Extend the policy learner with a graphical interface where users can right-swipe/left-swipe actions, creating a real-time `train_policy()` feed.
2. **Granular Taint-Tracking:** Expand the provenance schema to track taint down to the AST level rather than just the string level for safer JSON parameter generation.
3. **Local Models:** Replace the Anthropic adapter with local weights (e.g., Llama 3) for the injection judge and triage layers, reducing latency and cost for high-volume pipelines.
