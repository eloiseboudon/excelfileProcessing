.PHONY: db-create run-backend

db-create:
	psql -U postgres -d postgres -tc "SELECT 1 FROM pg_database WHERE datname='ajtpro'" | grep -q 1 || psql -U postgres -d postgres -c "CREATE DATABASE ajtpro"

run-backend:
	$(MAKE) -C backend run
