.RECIPEPREFIX := >
DC := docker compose
SERVICE ?=
MSG ?= "Auto migration"

.PHONY: help docker-build docker-up docker-down docker-logs         alembic-init alembic-migrate alembic-upgrade alembic-downgrade         alembic-current alembic-history clean-branches shell-postgres

help:
> @echo "Available commands:"
> @echo "  docker-build           Build backend and frontend images"
> @echo "  docker-up              Start postgres, backend and frontend-dev"
> @echo "  docker-down            Stop all services"
> @echo "  docker-logs SERVICE=s  Tail logs of a service"
> @echo "  shell-postgres         Open a shell in the postgres container"
> @echo "  alembic-init           Initialise Alembic configuration"
> @echo "  alembic-migrate        Create a new Alembic migration"
> @echo "  alembic-upgrade        Apply Alembic migrations"
> @echo "  alembic-downgrade      Revert last Alembic migration"
> @echo "  alembic-current        Show current Alembic revision"
> @echo "  alembic-history        Show Alembic history"
> @echo "  clean-branches         Remove local Git branches except main/dev"

docker-build:
> $(DC) build backend
> $(DC) --profile dev build frontend-dev

docker-up:
> $(DC) up -d postgres backend
> $(DC) --profile dev up -d frontend-dev

docker-down:
> $(DC) down

docker-logs:
> $(DC) logs -f $(SERVICE)

shell-postgres:
> $(DC) exec postgres bash

alembic-init:
> $(DC) run --rm backend alembic init alembic

alembic-migrate:
> $(DC) run --rm backend alembic revision --autogenerate -m $(MSG)

alembic-upgrade:
> $(DC) exec backend alembic upgrade head

alembic-downgrade:
> $(DC) exec backend alembic downgrade -1

alembic-current:
> $(DC) exec backend alembic current

alembic-history:
> $(DC) exec backend alembic history --verbose

clean-branches:
> git branch | grep -v -E "(main|dev|\*)" | xargs git branch -D
