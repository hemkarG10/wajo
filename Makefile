.PHONY: setup test lint eval eval-live transcripts

setup:
	uv sync

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check .

eval:
	uv run python -m eval.harness --mode replay

eval-live:
	uv run python -m eval.harness --mode live

transcripts:
	uv run python -m agent.cli transcripts
