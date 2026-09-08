.PHONY: setup test lint eval eval-smoke record run transcripts clean-clone-check

setup:
	uv sync

-include .env
export

test:
	PYTHONPATH=. uv run pytest tests/ -v

lint:
	uv run ruff check .

run:
	PYTHONPATH=. uv run python src/agent/cli.py run --inbox sample_inbox.json --mode replay

record:
	PYTHONPATH=. uv run python eval/record.py --rpm 0

record-check:
	PYTHONPATH=. uv run python eval/record.py --check

eval-smoke:
	AGENT_LLM_PROVIDER=heuristic PYTHONPATH=. uv run python eval/harness.py
	PYTHONPATH=. uv run python eval/report.py

eval:
	PYTHONPATH=. uv run python eval/harness.py
	PYTHONPATH=. uv run python eval/report.py

transcripts:
	PYTHONPATH=. uv run python eval/gen_transcripts.py

clean-clone-check:
	cd /tmp && rm -rf wajo_clean && git clone $(PWD) wajo_clean && cd wajo_clean && env -i PATH=$(PATH) HOME=$(HOME) make setup && make test && make eval
