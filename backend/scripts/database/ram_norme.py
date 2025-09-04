#!/usr/bin/env python3
"""
Script pour initialiser les tables RAMOption et Norme
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

        cur.execute("SELECT * FROM ram_options")
        ram_options = cur.fetchall()
        print("RAM options actuelles:", ram_options)

        cur.execute("SELECT * FROM norme_options")
        norme_options = cur.fetchall()
        print("Norme options actuelles:", norme_options)

        # Insérer les options RAM (méthode 1 : une requête par valeur)
        ram_values = ['4 Go', '8 Go', '16 Go', '32 Go']
        for ram in ram_values:
            try:
                cur.execute("INSERT INTO ram_options (ram) VALUES (%s)", (ram,))
                print(f"✅ Ajouté RAM: {ram}")
            except psycopg2.IntegrityError:
                print(f"⚠️  RAM {ram} existe déjà")
                conn.rollback()  # Rollback pour cette insertion seulement

        # Insérer les options de norme (méthode 1 : une requête par valeur)
        norme_values = ['3G', '4G', '5G']
        for norme in norme_values:
            try:
                cur.execute("INSERT INTO norme_options (norme) VALUES (%s)", (norme,))
                print(f"✅ Ajouté Norme: {norme}")
            except psycopg2.IntegrityError:
                print(f"⚠️  Norme {norme} existe déjà")
                conn.rollback()  # Rollback pour cette insertion seulement

        conn.commit()

        print("🗑️  Après update")
        cur.execute("SELECT * FROM ram_options")
        ram_options = cur.fetchall()
        print("RAM options finales:", ram_options)

        cur.execute("SELECT * FROM norme_options")
        norme_options = cur.fetchall()
        print("Norme options finales:", norme_options)

        print("\n🎉 Modification norme_options et ram_options ok !")

    except psycopg2.Error as e:
        print(f"❌ Erreur de base de données: {e}")
        if 'conn' in locals():
            conn.rollback()
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
