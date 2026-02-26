# Étape 1 : image de base optimisée
FROM python:3.13-slim

# Étape 2 : définition du dossier de travail dans le conteneur
WORKDIR /app

# Étape 3 : installation des dépendances système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    libpq-dev \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Étape 4 : copie des dépendances et installation Python
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Étape 5 : création d'un utilisateur non-root
RUN useradd --create-home --shell /bin/bash appuser

# Étape 6 : copie du code de l'application
COPY . .

RUN mkdir -p /app/logs && chown -R appuser:appuser /app

# Étape 7 : entrypoint qui fixe les permissions du volume logs au démarrage
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]

# Étape 8 : lancement via Gunicorn (expose l'objet app)
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5001"]
