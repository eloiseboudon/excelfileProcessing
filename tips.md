# Connexion serveur 
ssh ubuntu@51.77.231.101
3k56b5iEhI0k
curl http://51.77.231.101:8000

http://51.77.231.101:81/nginx/proxy
tanacode

# 📘 Mémo Docker – Projet AJTPRO

## 🛠️ Build et démarrage des containers
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env up -d --build
```

## ⬇️ Stop & suppression des containers
```bash
docker compose down            # Arrête les containers
docker compose down -v        # Supprime aussi les volumes
```

## 🐳 Gestion des containers

### 📋 Liste des containers
```bash
docker ps                     # Containers en cours
docker ps -a                 # Tous les containers (y compris arrêtés)
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### 🚪 Accès à un container
```bash
docker exec -it <nom_container> sh
# Exemple :
docker exec -it ajt_backend sh
docker exec -it <nom_container> bash
```

### 📜 Logs
```bash
docker logs -f <nom_container> 
docker logs -f ajt_backend_prod
docker logs -f ajt_frontend_prod
docker logs -f postgres_prod
```

### 🔄 Redémarrer un container
```bash
docker restart <nom_container>
```

## 🧱 Réseau Docker

### 🔍 Voir les réseaux
```bash
docker network ls
```

### 🕸️ Tester la résolution DNS dans un réseau
```bash
docker run --rm --network <nom_reseau> busybox nslookup postgres
```

## 🗃️ PostgreSQL

### 🔐 Connexion au container Postgres
```bash
docker exec -it postgres bash
```

### 🛢️ Connexion à la base
```bash
psql -U <utilisateur> -d <base>
# Exemple :
psql -U ajt_user -d ajt_db
```

### 🔧 Création manuelle
```sql
CREATE ROLE ajt_user WITH LOGIN PASSWORD 'ajt_password';
ALTER ROLE ajt_user CREATEDB;
CREATE DATABASE ajt_db OWNER ajt_user;
```

### 🧪 Lancer un script (externe)
```bash
docker run -it --rm \
  --env-file .env \
  --network ajtpro_default \
  -v $(pwd)/backend:/app \
  -w /app \
  python:3.11-slim \
  sh -c "pip install -r requirements.txt && python implement_tables.py"
```

## ⚙️ Alembic

### ▶️ Lancer les migrations
```bash
docker compose exec backend alembic upgrade head
```

### 🧪 Mode temporaire (externe)
```bash
docker run -it --rm \
  --env-file .env \
  --network ajtpro_default \
  -v $(pwd)/backend:/app \
  -w /app \
  python:3.11-slim \
  sh -c "pip install -r requirements.txt && alembic upgrade head"
```

## 👌 Compilation manuelle

### En local : 
```bash
cd frontend
npm install
npm run build
```


### Depuis le dossier ajtpro/, exécute :

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```
Explication :

down : arrête et supprime les conteneurs existants.

build --no-cache : reconstruit sans réutiliser d’anciennes couches Docker.

up -d : relance tout en détaché.



