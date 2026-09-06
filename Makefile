.PHONY: setup test lint eval eval-smoke eval-live run transcripts clean-clone-check

setup:
	uv sync

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check .

run:
	PYTHONPATH=. uv run python src/agent/cli.py run --inbox sample_inbox.json --mode replay

eval:
	EVAL_MODE=replay PYTHONPATH=. uv run python eval/harness.py
	PYTHONPATH=. uv run python eval/report.py

eval-smoke:
	EVAL_MODE=mock PYTHONPATH=. uv run python eval/harness.py --llm heuristic
	PYTHONPATH=. uv run python eval/report.py

eval-live:
	EVAL_MODE=record PYTHONPATH=. uv run python eval/harness.py
	PYTHONPATH=. uv run python eval/report.py

transcripts:
	PYTHONPATH=. uv run python src/agent/cli.py run --inbox sample_inbox.json --mode replay

clean-clone-check:
	cd /tmp && rm -rf wajo_clean && git clone $(PWD) wajo_clean && cd wajo_clean && env -i PATH=$(PATH) HOME=$(HOME) make setup && make test && make eval
