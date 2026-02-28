.PHONY: help install lint format type-check test test-cov ci clean

help:
	@echo "gnss-remote-sensing Makefile targets:"
	@echo "  install        - Install development dependencies"
	@echo "  lint           - Run ruff linter (GitHub format)"
	@echo "  format         - Check code formatting with ruff"
	@echo "  format-fix     - Fix code formatting with ruff"
	@echo "  type-check     - Run mypy type checking"
	@echo "  test           - Run pytest test suite"
	@echo "  test-cov       - Run pytest with coverage report"
	@echo "  ci             - Run all CI checks (lint, format, type-check, test-cov)"
	@echo "  clean          - Remove build artifacts and cache files"

install:
	pip install -e ".[dev]" || uv pip install -e .

lint:
	uv run ruff check . --output-format=github

format:
	uv run ruff format --check .

format-fix:
	rv run ruff format .

type-check:
	uv run mypy --explicit-package-bases --exclude '(^|/)misc/' ./app --pretty

test:
	uv run pytest tests/ -v

test-cov:
	uv run pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=xml

ci: lint format type-check test-cov
	@echo "✅ All CI checks passed!"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete
	find . -type f -name "coverage.xml" -delete
	@echo "✅ Cleaned up build artifacts and cache files"
