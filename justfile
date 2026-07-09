# ReOrchestra - Command Runner

# Show available commands
default:
    @echo "Available commands:"
    @echo "  just install   - Install dependencies"
    @echo "  just dev       - Start dev server with auto-reload"
    @echo "  just run       - Start production server"
    @echo "  just debug     - Start with debug logging"
    @echo "  just test      - Run tests"
    @echo "  just lint      - Lint code"
    @echo "  just fmt       - Format code"
    @echo "  just logs      - Tail logs"
    @echo "  just clean     - Clean cache"
    @echo "  just cleanup   - Full cleanup"

# Install dependencies
install:
    uv sync

# Start server
run:
    uv run -- python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Start with auto-reload
dev:
    uv run -- python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Start with debug logging
debug:
    LOG_LEVEL=DEBUG uv run -- python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Tail logs
logs:
    tail -f data/logs/app_*.log | cut -d'|' -f3-

# Clear logs
logs-clear:
    rm -f data/logs/*.log

# Clean cache only (keep venv and data)
clean:
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
    find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null; true
    find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null; true
    find . -type f -name "*.pyc" -delete

# Full cleanup (remove venv, cache, data)
cleanup: clean
    rm -rf .venv
    rm -rf data/sessions/*
    rm -rf data/logs/*
    rm -f data/reddit.db

# Run tests
test:
    uv run pytest tests/

# Lint code
lint:
    uv run ruff check app/ tests/

# Format code
fmt:
    uv run ruff format app/ tests/
