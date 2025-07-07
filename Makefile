.PHONY: db-up db-down db-create run-backend

db-up:
	docker compose up -d db

db-down:
	docker compose down

db-create:
	docker compose exec db psql -U postgres -c "CREATE DATABASE ajtpro;" || true

run-backend:
	$(MAKE) -C backend run
