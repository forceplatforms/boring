# ComplianceGuard Development Automation
.PHONY: help install dev test lint format clean docker-up docker-down migrate

# Variables
PYTHON := python3.11
UV := uv
PROJECT_NAME := complianceguard
DOCKER_COMPOSE := docker compose -f docker/docker-compose.yml

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)ComplianceGuard Development Commands:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# Development Setup Commands
install: ## Install UV and project dependencies
	@echo "$(BLUE)Installing UV package manager...$(NC)"
	@curl -LsSf https://astral.sh/uv/install.sh | sh
	@echo "$(BLUE)Installing project dependencies...$(NC)"
	@$(UV) sync
	@echo "$(GREEN)✓ Dependencies installed successfully$(NC)"

install-dev: ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	@$(UV) pip install -e ".[dev]"
	@$(UV) pip install -e ".[monitoring]"
	@pre-commit install
	@echo "$(GREEN)✓ Development environment ready$(NC)"

create-env: ## Create .env file from example
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)✓ Created .env file from .env.example$(NC)"; \
		echo "$(RED)⚠ Please update .env with your API keys$(NC)"; \
	else \
		echo "$(BLUE).env file already exists$(NC)"; \
	fi

# Docker Commands
docker-build: ## Build Docker containers
	@echo "$(BLUE)Building Docker containers...$(NC)"
	@$(DOCKER_COMPOSE) build
	@echo "$(GREEN)✓ Containers built successfully$(NC)"

docker-up: ## Start all services with Docker Compose
	@echo "$(BLUE)Starting Docker services...$(NC)"
	@$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✓ Services started successfully$(NC)"
	@echo "$(BLUE)Services available at:$(NC)"
	@echo "  • API: http://localhost:8000"
	@echo "  • API Docs: http://localhost:8000/docs"
	@echo "  • MinIO Console: http://localhost:9001"
	@echo "  • Flower (Celery): http://localhost:5555"

docker-down: ## Stop all Docker services
	@echo "$(BLUE)Stopping Docker services...$(NC)"
	@$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✓ Services stopped$(NC)"

docker-logs: ## View Docker logs
	@$(DOCKER_COMPOSE) logs -f

docker-clean: ## Stop services and remove volumes
	@echo "$(RED)⚠ This will delete all data! Continue? [y/N]$(NC)"
	@read -r response; \
	if [ "$$response" = "y" ]; then \
		$(DOCKER_COMPOSE) down -v; \
		echo "$(GREEN)✓ Services stopped and volumes removed$(NC)"; \
	else \
		echo "$(BLUE)Operation cancelled$(NC)"; \
	fi

# Database Commands
db-create: ## Create database
	@echo "$(BLUE)Creating database...$(NC)"
	@$(DOCKER_COMPOSE) exec postgres createdb -U complianceguard complianceguard || true
	@echo "$(GREEN)✓ Database created$(NC)"

db-migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	@$(DOCKER_COMPOSE) exec api alembic upgrade head
	@echo "$(GREEN)✓ Migrations completed$(NC)"

db-migration-create: ## Create a new migration (usage: make db-migration-create name="add_user_table")
	@echo "$(BLUE)Creating new migration: $(name)$(NC)"
	@$(DOCKER_COMPOSE) exec api alembic revision --autogenerate -m "$(name)"
	@echo "$(GREEN)✓ Migration created$(NC)"

db-reset: ## Reset database (drop and recreate)
	@echo "$(RED)⚠ This will delete all data! Continue? [y/N]$(NC)"
	@read -r response; \
	if [ "$$response" = "y" ]; then \
		$(DOCKER_COMPOSE) exec postgres dropdb -U complianceguard complianceguard --if-exists; \
		$(DOCKER_COMPOSE) exec postgres createdb -U complianceguard complianceguard; \
		$(MAKE) db-migrate; \
		echo "$(GREEN)✓ Database reset completed$(NC)"; \
	else \
		echo "$(BLUE)Operation cancelled$(NC)"; \
	fi

db-seed: ## Seed database with test data
	@echo "$(BLUE)Seeding database...$(NC)"
	@$(DOCKER_COMPOSE) exec api python scripts/seed_data.py
	@echo "$(GREEN)✓ Database seeded$(NC)"

# Development Commands
dev: ## Start development server locally (without Docker)
	@echo "$(BLUE)Starting development server...$(NC)"
	@$(UV) run uvicorn complianceguard.main:app --reload --host 0.0.0.0 --port 8000

dev-celery: ## Start Celery worker locally
	@echo "$(BLUE)Starting Celery worker...$(NC)"
	@$(UV) run celery -A complianceguard.tasks.celery_app worker --loglevel=info

dev-flower: ## Start Flower (Celery monitoring)
	@echo "$(BLUE)Starting Flower...$(NC)"
	@$(UV) run celery -A complianceguard.tasks.celery_app flower

shell: ## Open Python shell with project context
	@$(UV) run ipython

# Testing Commands
test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	@$(UV) run pytest tests/ -v --cov=complianceguard --cov-report=term-missing

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	@$(UV) run pytest tests/unit -v -m unit

test-integration: ## Run integration tests
	@echo "$(BLUE)Running integration tests...$(NC)"
	@$(UV) run pytest tests/integration -v -m integration

test-e2e: ## Run end-to-end tests
	@echo "$(BLUE)Running E2E tests...$(NC)"
	@$(UV) run pytest tests/e2e -v -m e2e

test-watch: ## Run tests in watch mode
	@echo "$(BLUE)Starting test watcher...$(NC)"
	@$(UV) run pytest-watch tests/ --clear --nobeep

test-coverage: ## Generate test coverage report
	@echo "$(BLUE)Generating coverage report...$(NC)"
	@$(UV) run pytest tests/ --cov=complianceguard --cov-report=html
	@echo "$(GREEN)✓ Coverage report generated in htmlcov/index.html$(NC)"

# Code Quality Commands
lint: ## Run code linters
	@echo "$(BLUE)Running linters...$(NC)"
	@$(UV) run ruff check src/ tests/
	@$(UV) run mypy src/
	@echo "$(GREEN)✓ Linting completed$(NC)"

format: ## Format code with Black and isort
	@echo "$(BLUE)Formatting code...$(NC)"
	@$(UV) run ruff format src/ tests/
	@$(UV) run ruff check --fix src/ tests/
	@echo "$(GREEN)✓ Code formatted$(NC)"

type-check: ## Run type checking with mypy
	@echo "$(BLUE)Running type checks...$(NC)"
	@$(UV) run mypy src/ --show-error-codes
	@echo "$(GREEN)✓ Type checking completed$(NC)"

pre-commit: ## Run pre-commit hooks
	@echo "$(BLUE)Running pre-commit hooks...$(NC)"
	@pre-commit run --all-files
	@echo "$(GREEN)✓ Pre-commit checks passed$(NC)"

# Documentation Commands
docs-serve: ## Serve documentation locally
	@echo "$(BLUE)Starting documentation server...$(NC)"
	@$(UV) run mkdocs serve

docs-build: ## Build documentation
	@echo "$(BLUE)Building documentation...$(NC)"
	@$(UV) run mkdocs build
	@echo "$(GREEN)✓ Documentation built in site/$(NC)"

# Utility Commands
clean: ## Clean up generated files and caches
	@echo "$(BLUE)Cleaning up...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type f -name ".coverage" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✓ Cleanup completed$(NC)"

check-env: ## Verify environment setup
	@echo "$(BLUE)Checking environment...$(NC)"
	@echo -n "Python: "; python --version
	@echo -n "UV: "; $(UV) --version || echo "Not installed"
	@echo -n "Docker: "; docker --version || echo "Not installed"
	@echo -n "Docker Compose: "; docker compose version || echo "Not installed"
	@echo ""
	@if [ -f .env ]; then \
		echo "$(GREEN)✓ .env file exists$(NC)"; \
	else \
		echo "$(RED)✗ .env file missing (run: make create-env)$(NC)"; \
	fi
	@echo "$(GREEN)✓ Environment check completed$(NC)"

# API Testing Commands
api-test-upload: ## Test document upload endpoint
	@echo "$(BLUE)Testing document upload...$(NC)"
	@curl -X POST "http://localhost:8000/api/v1/documents/upload" \
		-F "file=@tests/fixtures/sample.pdf" \
		-F "doc_type=ciso_report"

api-test-scan: ## Test scan trigger endpoint
	@echo "$(BLUE)Triggering compliance scan...$(NC)"
	@curl -X POST "http://localhost:8000/api/v1/scans/trigger" \
		-H "Content-Type: application/json" \
		-d '{"framework": "SEC_CYBER", "scan_type": "initial"}'

api-test-violations: ## Get violations list
	@echo "$(BLUE)Fetching violations...$(NC)"
	@curl -X GET "http://localhost:8000/api/v1/violations" | python -m json.tool

# Performance Commands
profile: ## Profile the application
	@echo "$(BLUE)Starting profiler...$(NC)"
	@$(UV) run python -m cProfile -o profile.stats src/complianceguard/main.py

benchmark: ## Run performance benchmarks
	@echo "$(BLUE)Running benchmarks...$(NC)"
	@$(UV) run python scripts/benchmark.py

# Quick Start Commands
quickstart: install create-env docker-build docker-up db-migrate ## Complete setup for new developers
	@echo "$(GREEN)✨ ComplianceGuard is ready!$(NC)"
	@echo ""
	@echo "$(BLUE)Next steps:$(NC)"
	@echo "1. Update .env with your API keys"
	@echo "2. Run: make api-test-upload (to test document upload)"
	@echo "3. Visit http://localhost:8000/docs for API documentation"

# Default target
.DEFAULT_GOAL := help