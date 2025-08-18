#!/usr/bin/env python3
"""
Script pour implémenter les tables avec les données initiales
"""

import os
import sys

import psycopg2
from dotenv import load_dotenv


def main():
    print("🚀 Début de l'implémentation des tables...")

    # Charger les variables d'environnement
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)

    # Obtenir l'URL de la base de données
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ ERROR: DATABASE_URL environment variable is not set")
        sys.exit(1)

    print("📡 Connexion à la base de données...")

    try:
        # Connexion à la base de données
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        print("🗑️  Avant update")

        cur.execute("SELECT * FROM users")
        users = cur.fetchall()
        print(users)

        cur.execute("UPDATE users SET email = 'admin@admin' WHERE username = 'admin'")
        conn.commit()

        cur.execute(
            "UPDATE users SET email = 'client@client' WHERE username = 'client'"
        )
        conn.commit()

        print("🗑️  Après update")
        cur.execute("SELECT * FROM users")
        users = cur.fetchall()
        print(users)

        print("\n🎉 Modification user ok !")

    except psycopg2.Error as e:
        print(f"❌ Erreur de base de données: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        sys.exit(1)
    finally:
        # Fermer les connexions
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()
