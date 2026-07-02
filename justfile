# ReOrchestra - Command Runner

# Install dependencies
install:
    uv venv
    uv pip install -e .

# Start server
run:
    uvicorn app.main:app --host 0.0.0.0 --port 8000

# Start with auto-reload
dev:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Start with debug logging
debug:
    LOG_LEVEL=DEBUG uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Tail logs
logs:
    tail -f data/logs/app_*.log | cut -d'|' -f3-

# Clear logs
logs-clear:
    rm -f data/logs/*.log

# Clean cache
clean:
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
    find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null; true
    find . -type f -name "*.pyc" -delete

# Run tests
test:
    pytest

# Lint code
lint:
    ruff check .
