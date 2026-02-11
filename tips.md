# Memo Docker - Projet AJTPRO

## Build et demarrage des containers
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env up -d --build
```

## Stop & suppression des containers
```bash
docker compose down            # Arrete les containers
docker compose down -v        # Supprime aussi les volumes
```

## Gestion des containers

### Liste des containers
```bash
docker ps                     # Containers en cours
docker ps -a                 # Tous les containers (y compris arretes)
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### Acces a un container
```bash
docker exec -it <nom_container> sh
# Exemple :
docker exec -it ajt_backend sh
docker exec -it <nom_container> bash
```

### Logs
```bash
docker logs -f <nom_container>
docker logs -f ajt_backend_prod
docker logs -f ajt_frontend_prod
docker logs -f postgres_prod
```

### Redemarrer un container
```bash
docker restart <nom_container>
```

## Reseau Docker

### Voir les reseaux
```bash
docker network ls
```

### Tester la resolution DNS dans un reseau
```bash
docker run --rm --network <nom_reseau> busybox nslookup postgres
```

## PostgreSQL

### Connexion au container Postgres
```bash
docker exec -it postgres bash
```

### Connexion a la base
```bash
psql -U <utilisateur> -d <base>
docker exec -it postgres_prod psql -U <utilisateur> -d <base>
```

### Ajout des donnees initiales
```bash
docker exec -it ajt_backend_prod python scripts/database/users.py
```

#### Import produits a partir d'un fichier
```bash
docker exec -it ajt_backend_prod python scripts/database/import_reference_products.py scripts/files/Produits_final_unique_20250923.csv --delimiter ";" --default-tcp 0
```

### Creation manuelle de la base
```sql
CREATE ROLE <utilisateur> WITH LOGIN PASSWORD '<mot_de_passe>';
ALTER ROLE <utilisateur> CREATEDB;
CREATE DATABASE <base> OWNER <utilisateur>;
```

### Lancer un script (externe)
```bash
docker run -it --rm \
  --env-file .env \
  --network ajtpro_default \
  -v $(pwd)/backend:/app \
  -w /app \
  python:3.11-slim \
  sh -c "pip install -r requirements.txt && python implement_tables.py"
```

## Alembic

### Lancer les migrations
```bash
docker compose exec backend alembic upgrade head
```

### Mode temporaire (externe)
```bash
docker run -it --rm \
  --env-file .env \
  --network ajtpro_default \
  -v $(pwd)/backend:/app \
  -w /app \
  python:3.11-slim \
  sh -c "pip install -r requirements.txt && alembic upgrade head"
```

## Compilation manuelle

### En local
```bash
cd frontend
npm install
npm run build
```

### Depuis le dossier ajtpro/
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

## Deploiement
```bash
chmod +x deploy.sh
./deploy.sh
```
