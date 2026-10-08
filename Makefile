.PHONY: help install lint format test run-api clean

VENV ?= .venv
PYTHON ?= $(shell which python3)
BIN = $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/,)

help:
	@echo "News Sentiment Analyzer - Available commands:"
	@echo "  make install   Install package and dev dependencies"
	@echo "  make lint      Run ruff check, ruff format check, and mypy"
	@echo "  make format    Format code with ruff"
	@echo "  make test      Run unit and integration tests with coverage"
	@echo "  make run-api   Start FastAPI development server with reload"
	@echo "  make clean     Remove cache files and build artifacts"

install:
	$(BIN)$(PYTHON) -m pip install --upgrade pip
	$(BIN)$(PYTHON) -m pip install -e ".[dev]"
	-$(BIN)pre-commit install

lint:
	$(BIN)ruff check src tests
	$(BIN)ruff format --check src tests
	$(BIN)mypy src

format:
	$(BIN)ruff check --fix src tests
	$(BIN)ruff format src tests

test:
	$(BIN)pytest

run-api:
	$(BIN)uvicorn news_sentiment.api.main:app --host 127.0.0.1 --port 8000 --reload

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov coverage.xml
	find . -type d -name "__pycache__" -exec rm -rf {} +
