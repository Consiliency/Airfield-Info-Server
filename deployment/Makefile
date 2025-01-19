# Detect the current Git branch
BRANCH := $(shell git rev-parse --abbrev-ref HEAD)

# Paths to deployment files based on branch
ifeq ($(BRANCH), main)
  COMPOSE_FILE := ../deployment/docker-compose.yml
else ifeq ($(BRANCH), develop)
  COMPOSE_FILE := ../deployment/docker-compose.dev.yml
else
  $(error Unsupported branch "$(BRANCH)". Only "main" and "develop" are supported.)
endif

# Path to environment file
ENV_FILE := .env

# Docker Compose Commands
up:
	@echo "Starting services with $(ENV_FILE) on branch $(BRANCH)..."
	docker compose -f $(COMPOSE_FILE) up -d

upb:
	@echo "Starting services with $(ENV_FILE) on branch $(BRANCH) and rebuilding images..."
	docker compose -f $(COMPOSE_FILE) up -d --build

down:
	@echo "Stopping services on branch $(BRANCH)..."
	docker compose -f $(COMPOSE_FILE) down

downrmi:
	@echo "Stopping services and removing containers and images on branch $(BRANCH)..."
	docker compose -f $(COMPOSE_FILE) down --rmi all

log:
	@echo "Fetching logs on branch $(BRANCH)..."
	docker compose -f $(COMPOSE_FILE) logs -f

ps:
	@echo "Listing running services on branch $(BRANCH)..."
	docker compose -f $(COMPOSE_FILE) ps

restart:
	@echo "Restarting services on branch $(BRANCH)..."
	docker compose -f $(COMPOSE_FILE) down
	docker compose -f $(COMPOSE_FILE) up -d

remove:
	@echo "Removing services, volumes, and orphan containers on branch $(BRANCH)..."
	docker compose -f $(COMPOSE_FILE) down --volumes --remove-orphans

clean:
	@echo "Cleaning up Docker resources..."
	docker system prune -f
	docker volume prune -f

help:
	@echo "Makefile commands:"
	@echo "  up       - Start services in detached mode."
	@echo "  down     - Stop services and remove containers."
	@echo "  log      - View logs from all services."
	@echo "  ps       - List running services."
	@echo "  restart  - Restart services."
	@echo "  remove   - Stop services and remove all volumes."
	@echo "  clean    - Clean up unused Docker resources."