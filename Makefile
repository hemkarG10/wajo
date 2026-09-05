.PHONY: setup test lint eval eval-live transcripts

setup:
	uv sync

test:
	uv run pytest tests/ -v

eval:
	PYTHONPATH=. uv run python eval/runner.py

lint:
	uv run ruff check .

transcripts:
	uv run python src/agent/cli.py run --inbox sample_inbox.json --mode record
