.PHONY: help dev-up dev-down migrate seed api-shell test lint format backup
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

dev-up: ## Start development environment
	docker-compose -f backend/compose/docker-compose.yml -f backend/compose/docker-compose.override.yml up -d

dev-down: ## Stop development environment
	docker-compose -f backend/compose/docker-compose.yml -f backend/compose/docker-compose.override.yml down

migrate: ## Run database migrations
	cd backend && python manage.py migrate

seed: ## Load demo data
	cd backend && python manage.py seed_demo

api-shell: ## Open Django shell
	cd backend && python manage.py shell

test: ## Run tests with coverage
	cd backend && pytest

lint: ## Run linting (pre-commit)
	pre-commit run --all-files

format: ## Format code
	cd backend && black apps/
	cd backend && isort apps/
	cd backend && ruff --fix apps/

backup: ## Run database backup
	cd backend && ./scripts/backup_db.sh

clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .coverage

install: ## Install dependencies (development)
	pip install --upgrade pip
	pip install -r backend/requirements/dev.txt
	cd backend && pip install -e .
	pre-commit install

install-prod: ## Install production dependencies
	pip install --upgrade pip
	pip install -r backend/requirements.txt

install-test: ## Install testing dependencies
	pip install --upgrade pip
	pip install -r backend/requirements/test.txt

build: ## Build Docker image
	cd backend && docker build -t django-saas-boilerplate .

logs: ## Show container logs
	docker-compose -f backend/compose/docker-compose.yml logs -f

restart: ## Restart development environment
	make dev-down
	make dev-up

check: ## Run all checks (lint, test, type check)
	make lint
	make test
	cd backend && mypy apps/
