.DEFAULT_GOAL := install

.PHONY: help install sync lock lock-upgrade fmt lint check test cov clean run validate vllm-serve docs-serve docs-stop

UV ?= uv
PYTHON ?= 3.13
INPUT ?= examples/cassie_beach_adventure_input.json
OUTPUT ?=
MODEL ?=
VLLM_MODEL ?= google/gemma-4-31B-it
VLLM_PORT ?= 8000

help:
	@echo "FableFlow Makefile"
	@echo ""
	@echo "Environment:"
	@echo "  install        - Sync the venv from uv.lock (default target)"
	@echo "  sync           - Same as install"
	@echo "  lock           - Resolve dependencies into uv.lock"
	@echo "  lock-upgrade   - Resolve uv.lock with --upgrade"
	@echo "  clean          - Remove caches and build artifacts"
	@echo ""
	@echo "Development:"
	@echo "  fmt            - Format code with ruff"
	@echo "  lint           - Lint with ruff (check only)"
	@echo "  check          - Lint + type check (mypy)"
	@echo "  test           - Run all tests"
	@echo "  cov            - Run tests with coverage"
	@echo ""
	@echo "Pipeline:"
	@echo "  validate       - Validate an input file (override with INPUT=)"
	@echo "  run            - Run the full pipeline (override INPUT=, OUTPUT=, MODEL=, RESUME=0 to disable resume)"
	@echo ""
	@echo "Local LLM serving (vLLM):"
	@echo "  vllm-serve     - Serve VLLM_MODEL (default: $(VLLM_MODEL)) on port $(VLLM_PORT)"
	@echo ""
	@echo "Docs:"
	@echo "  docs-serve     - Run mkdocs livereload on :8080"
	@echo "  docs-stop      - Stop mkdocs livereload"

install: sync

sync:
	$(UV) sync

lock:
	$(UV) lock

lock-upgrade:
	$(UV) lock --upgrade

fmt:
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

lint:
	$(UV) run ruff format --check .
	$(UV) run ruff check .

check: lint
	$(UV) run mypy producer/fable_flow/

test:
	$(UV) run pytest --no-cov

cov:
	$(UV) run pytest

validate:
	$(UV) run fable-flow validate $(INPUT)

RESUME ?= 1

run:
	$(UV) run fable-flow generate $(INPUT) \
		$(if $(OUTPUT),--output $(OUTPUT),) \
		$(if $(MODEL),--model $(MODEL),) \
		$(if $(filter 1 true yes,$(RESUME)),--resume,)

vllm-serve:
	@echo "Serving $(VLLM_MODEL) on http://localhost:$(VLLM_PORT)/v1"
	$(UV) run vllm serve $(VLLM_MODEL) --port $(VLLM_PORT)
	# uv run vllm serve google/gemma-4-31B-it \
	#   --tensor-parallel-size 2 \
	#   --enable-auto-tool-choice \
	#   --tool-call-parser gemma4 \
	#   --reasoning-parser gemma4 \
	#   --gpu-memory-utilization 0.90


docs-serve:
	@echo "Starting MkDocs on http://localhost:8080"
	@$(UV) run --group docs mkdocs serve --livereload -a localhost:8080 &
	@sleep 2
	@echo "Docs at http://localhost:8080"

docs-stop:
	@echo "Stopping mkdocs..."
	@-pkill -f "mkdocs serve" 2>/dev/null
	@sleep 1
	@-pkill -9 -f "mkdocs serve" 2>/dev/null
	@echo "Stopped"

clean:
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage build dist site 2>/dev/null || true
