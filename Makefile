.DEFAULT_GOAL := install

.PHONY: lock install fmt serve start-site stop-site publisher clean test studio-install studio-start studio-stop start-all stop-all

uv:
	pip install -Uq uv

lock: uv
	uv pip compile -o requirements.txt \
		--no-emit-index-url \
		--generate-hashes \
		--extra dev \
		--extra docs \
		pyproject.toml
	@echo "Please check in the generated <requirements.txt> to the repository"

lock-upgrade: uv
	uv pip compile -o requirements.txt \
		--upgrade \
		--no-emit-index-url \
		--generate-hashes \
		--extra dev \
		--extra docs \		
		pyproject.toml

install: uv
	uv pip install \
		--no-compile \
		--no-deps \
		-r requirements.txt
	uv pip install \
		--no-deps \
		--editable .
	uv pip check

fmt:
	ruff format .
# 	ruff format --check .
	ruff check --fix .
	ruff check .
# 	mypy producer/fable_flow/

start-site:
	@echo "📚 Starting MkDocs website on http://localhost:8080..."
	@mkdocs serve --livereload -a localhost:8080 &
	@sleep 2
	@echo "✅ Website started at http://localhost:8080"

stop-site:
	@echo "🛑 Stopping MkDocs website..."
	@-pkill -f "mkdocs serve" 2>/dev/null
	@sleep 1
	@-pkill -9 -f "mkdocs serve" 2>/dev/null
	@echo "✅ Website stopped"

serve: start-site

publisher:
	# source .env
	fable-flow publisher process

test:
	python -m pytest --cov=fable_flow --cov-report=term-missing

clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
	find . -name "htmlcov" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name ".mypy_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name ".ruff_cache" -type d -exec rm -rf {} + 2>/dev/null || true 

# Studio targets
studio-install:
	@echo "📦 Installing FableFlow Studio dependencies..."
	@echo "Installing Python backend dependencies..."
	pip install fastapi uvicorn[standard] websockets aiofiles
	@echo "Installing React frontend dependencies..."
	cd studio/web-ui && npm install
	@echo "✅ Studio dependencies installed"

studio-start:
	@echo "🚀 Starting FableFlow Studio..."
	@echo "📝 Loading environment variables from .env..."
	@if [ -f .env ]; then \
		echo "✓ Found .env file"; \
	else \
		echo "⚠️  Warning: .env file not found. Create one with GOOGLE_API_KEY for AI features."; \
		echo "   Get API key from: https://ai.google.dev/gemini-api/docs/api-key"; \
	fi
	@echo "🔧 Starting backend on http://localhost:8000..."
	@bash -c 'source .env 2>/dev/null || true; python3 studio/api.py' &
	@sleep 3
	@echo "🎨 Starting frontend on http://localhost:3000..."
	@cd studio/web-ui && npm run dev &
	@sleep 2
	@echo ""
	@echo "✅ FableFlow Studio started!"
	@echo "📍 Studio: http://localhost:3000"
	@echo "📍 Backend API: http://localhost:8000"
	@echo "📍 API Docs: http://localhost:8000/docs"
	@echo ""
	@echo "To stop: make studio-stop"

studio-stop:
	@echo "🛑 Stopping FableFlow Studio..."
	@-pkill -f "python -m uvicorn.*api:app" 2>/dev/null
	@-pkill -f "python3 studio/api.py" 2>/dev/null	
	@-pkill -f "node.*vite" 2>/dev/null	
	@sleep 2
	@-pkill -9 -f "python -m uvicorn.*api:app" 2>/dev/null
	@-pkill -9 -f "python3 studio/api.py" 2>/dev/null	
	@-pkill -9 -f "node.*vite" 2>/dev/null
	@echo "✅ Studio stopped"

start-all:
	@echo "🚀 Starting FableFlow Development Environment..."
	@$(MAKE) studio-start
	@$(MAKE) start-site
	@echo ""
	@echo "✅ FableFlow Development Environment started!"
	@echo "📍 Studio: http://localhost:3000"
	@echo "📍 Backend API: http://localhost:8000"
	@echo "📍 API Docs: http://localhost:8000/docs"
	@echo "📍 Website: http://localhost:8080"
	@echo ""
	@echo "To stop: make stop-all"

stop-all:
	@echo "🛑 Stopping FableFlow Development Environment..."
	@$(MAKE) studio-stop
	@$(MAKE) stop-site
	@echo "✅ All services stopped"
