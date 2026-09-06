.PHONY: setup test lint eval run transcripts

setup:
	uv sync

test:
	uv run pytest tests/ -v

eval:
	PYTHONPATH=. uv run python eval/harness.py
	PYTHONPATH=. uv run python eval/report.py

lint:
	uv run ruff check .

run:
	PYTHONPATH=. uv run python src/agent/cli.py run --inbox sample_inbox.json --mode replay

transcripts:
	PYTHONPATH=. uv run python src/agent/cli.py run --inbox sample_inbox.json --mode replay
