#!/bin/bash
# backend/dev-start.sh

echo "🚀 Démarrage du backend en mode développement..."
echo "📁 Répertoire de travail: $(pwd)"
echo "🔍 Fichiers Python détectés: $(ls -la *.py 2>/dev/null || echo 'Aucun')"

# Installer les dépendances si requirements.txt a changé
if [ requirements.txt -nt .requirements-installed ]; then
    echo "📦 Installation des dépendances..."
    pip install -r requirements.txt
    touch .requirements-installed
fi

# Vérifier la connexion à la base de données
echo "🔌 Test de connexion à la base de données..."
python -c "
import psycopg2
import os
import sys
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    print('✅ Connexion à la base de données OK')
    conn.close()
except Exception as e:
    print(f'❌ Erreur de connexion DB: {e}')
    sys.exit(1)
"

echo "🔥 Démarrage de Flask avec hot-reload..."
echo "💡 Modifications détectées automatiquement dans:"
echo "   - $(pwd)/*.py"
echo "   - Sous-dossiers inclus"
echo ""

# Démarrer Flask avec hot-reload
export FLASK_ENV=development
export FLASK_DEBUG=1
python -m flask run --host=0.0.0.0 --port=5001 --reload