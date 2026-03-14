.PHONY: help install infra-up infra-down \
       run-kafka-health run-kafka-health-cli \
       run-devops run-devops-cli

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2}'

# ── Setup ──────────────────────────────────────────────

install: ## Install all workspace packages
	uv sync

infra-up: ## Start shared infrastructure (Kafka, Zookeeper, Kafka UI)
	docker compose up -d

infra-down: ## Stop shared infrastructure
	docker compose down

# ── kafka-health-agent ─────────────────────────────────

run-kafka-health: ## Launch kafka-health-agent in ADK Dev UI
	cd agents/kafka-health && uv run adk web

run-kafka-health-cli: ## Run kafka-health-agent in terminal
	cd agents/kafka-health && uv run adk run kafka_health_agent

# ── devops-assistant ───────────────────────────────────

run-devops: ## Launch devops-assistant in ADK Dev UI
	cd agents/devops-assistant && uv run adk web

run-devops-cli: ## Run devops-assistant in terminal
	cd agents/devops-assistant && uv run adk run devops_assistant
