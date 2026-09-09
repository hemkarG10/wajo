.PHONY: setup test lint package-check eval eval-smoke record record-check run transcripts clean-clone-check dist

setup:
	uv sync

-include .env
export

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check .

package-check:
	uv build
	uv run agent version
	uv run agent --help > /dev/null

run:
	uv run agent run --inbox sample_inbox.json --mode live --llm heuristic

record:
	AGENT_LLM_MODE=record uv run python -u -m eval.record --rpm 0

record-check:
	uv run python -m eval.record --check

eval-smoke:
	AGENT_LLM_PROVIDER=heuristic AGENT_LLM_MODE=replay uv run python -m eval.harness
	uv run python -m eval.report

eval:
	AGENT_LLM_PROVIDER=gemini AGENT_LLM_MODE=replay AGENT_MODEL_SMALL=gemini-flash-lite-latest AGENT_MODEL_MAIN=gemini-flash-lite-latest uv run python -m eval.harness
	uv run python -m eval.report

transcripts:
	AGENT_LLM_PROVIDER=gemini AGENT_LLM_MODE=replay AGENT_MODEL_SMALL=gemini-flash-lite-latest AGENT_MODEL_MAIN=gemini-flash-lite-latest uv run python -m eval.gen_transcripts

clean-clone-check:
	audit_dir=$$(mktemp -d /tmp/wajo-clean.XXXXXX) && git archive HEAD | tar -x -C $$audit_dir && cd $$audit_dir && env -i PATH=$(PATH) HOME=$(HOME) make setup && make lint && make package-check && make test && make run && make eval

dist:
	git archive --format=zip -o wajo-submission.zip HEAD
