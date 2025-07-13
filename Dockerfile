FROM python:3.13-slim

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    make \
    && rm -rf /var/lib/apt/lists/*

# Créer le répertoire de travail
WORKDIR /app

# Copier les requirements et installer les dépendances Python
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l'application
COPY backend/ /app/
# Exposer le port
EXPOSE 5001

# Commande par défaut
CMD ["python", "app.py"]
