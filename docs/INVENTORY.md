# Project Inventory (Phase 0)

| existing path | planned path (Section 13) | action | note |
|---|---|---|---|
| `README.md` | `README.md` | adapt | Update for v2 quickstart/instructions |
| `DESIGN.md` | `DESIGN.md` | adapt | Will need updates for v2 new concepts (Clock, heuristic provider) |
| `IMPLEMENTATION_PLAN.md` | `IMPLEMENTATION_PLAN.md` | keep | This is the new v2 plan |
| `Makefile` | `Makefile` | adapt | Needs new eval targets (`eval-smoke`, `eval-live`, `clean-clone-check`) |
| `.github/workflows/ci.yml` | `.github/workflows/ci.yml` | adapt | Will need to run `eval-smoke` and `eval (replay)` |
| `pyproject.toml` | `pyproject.toml` | keep | Uses `hatchling` backend |
| `config/actions.yaml` | `config/actions.yaml` | keep | Verify it meets v2 requirements |
| `config/guard.yaml` | `config/guard.yaml` | keep | Verify it meets v2 requirements |
| `eval/harness.py` | `eval/harness.py` | adapt | Update to support new ablations and heuristic provider |
| `eval/personas.py` | `eval/personas.py` | adapt | Verify persona logic vs v2 requirements |
| `eval/report.py` | `eval/report.py` | adapt | Update for new metrics/ablations |
| `eval/simulate.py` | `eval/simulate.py` | adapt | Update for `SimClock` and new feedback model |
| `src/agent/cli.py` | `src/agent/cli.py` | adapt | Add heuristic/mock flags |
| `src/agent/decide.py` | `src/agent/decide.py` | adapt | Update for `Clock`, new LCB buckets |
| `src/agent/execute.py` | `src/agent/execute.py` | adapt | Update for `ExecutionOutcome`, `blocked_reason`, `Clock` |
| `src/agent/guard.py` | `src/agent/guard.py` | adapt | Ensure pure and handles new invariants |
| `src/agent/ingest.py` | `src/agent/ingest.py` | adapt | Add `GmailProvider` stub with docstring |
| `src/agent/injection.py` | `src/agent/injection.py` | adapt | Update heuristic checks, add `llm_judgement` skipping |
| `src/agent/learn/learner.py` | `src/agent/learn/trust.py` / `src/agent/learn/rules.py` / `src/agent/learn/feedback.py` | move / adapt | Refactor into `trust.py`, `rules.py`, `feedback.py` |
| `src/agent/llm.py` | `src/agent/llm.py` | adapt | Add `mock` and `heuristic` modes, enforce `CacheMiss` |
| `src/agent/models.py` | `src/agent/models.py` | adapt | Update with new models (`Clock`, `ExecutionOutcome`, `Feedback`) |
| `src/agent/planner.py` | `src/agent/planner.py` | adapt | Ensure provenance marking matches v2 |
| `src/agent/triage.py` | `src/agent/triage.py` | adapt | Remove persona from context (cache determinism) |
| `tests/` | `tests/` | adapt | Refactor for new module names and new v2 tests |

## Project Details
- **Package manager:** `uv` (implicitly through Makefile / `pyproject.toml` deps)
- **Python version:** `>=3.12`
- **Package name:** `agent`
- **Test runner:** `pytest`
- **Lint/format config:** `ruff`
- **LLM client exists:** Yes (`src/agent/llm.py` wraps Anthropic)
- **Mailbox reader exists:** Yes (`src/agent/ingest.py` contains `FakeMailbox`)
