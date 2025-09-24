.RECIPEPREFIX := >
DC := docker compose
SERVICE ?=
MSG ?= "Auto migration"
CSV ?=
DELIMITER ?= ;
DEFAULT_TCP ?= 0

.PHONY: help docker-build docker-up docker-down docker-logs \
        alembic-init alembic-migrate alembic-upgrade alembic-downgrade \
        alembic-current alembic-history clean-branches shell-postgres \
        import-reference-products

help:
	@echo "Available commands:"
	@echo "  docker-build           Build backend and frontend images"
	@echo "  docker-up              Start postgres, backend and frontend"
	@echo "  docker-down            Stop all services"
	@echo "  docker-logs SERVICE=s  Tail logs of a service"
	@echo "  import-reference-products CSV=path/to/file.csv [DELIMITER=';'] [DEFAULT_TCP=0]"
	@echo "  shell-postgres         Open a shell in the postgres container"
	@echo "  alembic-init           Initialise Alembic configuration"
	@echo "  alembic-migrate        Create a new Alembic migration"
	@echo "  alembic-upgrade        Apply Alembic migrations"
	@echo "  alembic-downgrade      Revert last Alembic migration"
	@echo "  alembic-current        Show current Alembic revision"
	@echo "  alembic-history        Show Alembic history"
	@echo "  clean-branches         Remove local Git branches except main/dev"

docker-build:
	$(DC) build backend frontend

docker-up:
	$(DC) up -d

docker-down:
	$(DC) down

docker-logs:
	$(DC) logs -f $(SERVICE)

shell-postgres:
	docker compose exec postgres psql -U postgres -d ajtpro

alembic-init:
	$(DC) run --rm backend alembic init alembic

alembic-migrate:
	$(DC) run --rm backend alembic revision --autogenerate -m $(MSG)

alembic-upgrade:
	$(DC) exec backend alembic upgrade head

alembic-downgrade:
	$(DC) exec backend alembic downgrade -1

alembic-current:
	$(DC) exec backend alembic current

alembic-history:
	$(DC) exec backend alembic history --verbose

clean-branches:
	git branch | grep -v -E "(main|dev|\*)" | xargs git branch -D

import-reference-products:
	if [ -z "$(CSV)" ]; then \
		echo "Usage: make import-reference-products CSV=scripts/files/Produits_final_unique_20250923.csv [DELIMITER=';'] [DEFAULT_TCP=0]"; \
		exit 1; \
	fi
	CSV_IN_CONTAINER="$(CSV)"; \
	case "$$CSV_IN_CONTAINER" in \
		backend/*) CSV_IN_CONTAINER="$${CSV_IN_CONTAINER#backend/}" ;; \
	esac; \
	docker compose exec backend python scripts/database/import_reference_products.py \
		"$$CSV_IN_CONTAINER" --delimiter "$(DELIMITER)" --default-tcp "$(DEFAULT_TCP)"

add_references_import_2025_0923:
	docker compose exec backend python scripts/database/add_references_import_2025_0923.py