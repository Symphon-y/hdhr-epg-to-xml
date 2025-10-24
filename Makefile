# Makefile for HD HomeRun XMLTV Converter

.PHONY: help build run run-once health test clean docker-build docker-run docker-clean

# Default target
help: ## Show this help message
	@echo "HD HomeRun XMLTV Converter"
	@echo "=========================="
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Development targets
install: ## Install Python dependencies
	pip install -r requirements.txt

test: ## Run tests (when implemented)
	python -m pytest tests/ -v

run: ## Run application in scheduled mode
	PYTHONPATH=src python -m hdhr_xmltv.main scheduled

run-once: ## Run application once and exit
	PYTHONPATH=src python -m hdhr_xmltv.main once

health: ## Run health check
	PYTHONPATH=src python -m hdhr_xmltv.main health

# Docker targets
docker-build: ## Build Docker image
	docker build -f docker/Dockerfile -t hdhr-xmltv-converter .

docker-run: ## Run Docker container
	cd docker && docker-compose up -d

docker-stop: ## Stop Docker container
	cd docker && docker-compose down

docker-logs: ## Show Docker container logs
	cd docker && docker-compose logs -f

docker-clean: ## Clean Docker resources
	cd docker && docker-compose down -v
	docker rmi hdhr-xmltv-converter 2>/dev/null || true

# Development helpers
format: ## Format code (if black is installed)
	black src/ tests/ 2>/dev/null || echo "Install black for code formatting"

lint: ## Lint code (if flake8 is installed)
	flake8 src/ tests/ 2>/dev/null || echo "Install flake8 for linting"

clean: ## Clean temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Quick start
quickstart: docker-build docker-run ## Build and run with Docker
	@echo "Container started! Check docker-logs for output"