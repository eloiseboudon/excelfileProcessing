"""
- brands: Essential, Hotwav, Nothing, Redmi
- colors: Alpine Loop L Indigo, Black, Black Titanium, Blue, Blue Titanium, Bronze, Brown, Chalk, Copper, Cream, Desert, Desert Titanium, Gold, Graphite, Gray, Green, Grey, Ice Blue, Indigo, Lavender, Lavender Purple, Midnight, Mint, Natural Titanium, Navy, Ocean, Olive, Phantom Black, Pink, Porcelain, Porcelaine, Purple, Red, Rose Gold, Silver, Space Gray, Space Grey, Starlight, Teal, Titanium, Trail Loop M/L Green/Grey, Trail Loop S/M Green/Grey, Ultramarine, White, White Titanium, Yellow
- memory_options: 100GB, 10GB, 1GB, 1TB, 20GB, 320GB, 50GB
- ram_options: 12, 16, 2, 3, 4, 6, 8
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

        cur.execute("SELECT * FROM memory_options")
        memory_options = cur.fetchall()
        print("Memory options actuelles:", memory_options)

        cur.execute("SELECT * FROM brands")
        brands = cur.fetchall()
        print("Brands actuelles:", brands)

        cur.execute("SELECT * FROM colors")
        colors = cur.fetchall()
        print("Colors actuelles:", colors)

        color_lookup = {
            color.lower(): color_id for color_id, color in colors if isinstance(color, str)
        }

        cur.execute("SELECT * FROM ram_options")
        ram_options = cur.fetchall()
        print("RAM options actuelles:", ram_options)

        # Insérer les options RAM (méthode 1 : une requête par valeur)
        memory_values = ["100GB", "10GB", "1GB", "1TB", "20GB", "320GB", "50GB"]
        for memory in memory_values:
            try:
                cur.execute(
                    "INSERT INTO memory_options (memory, tcp_value) VALUES (%s, %s)",
                    (memory, 0),
                )
                print(f"✅ Ajouté Memory: {memory} (tcp_value=0)")
            except psycopg2.IntegrityError:
                print(f"⚠️  Memory {memory} existe déjà")
                conn.rollback()  # Rollback pour cette insertion seulement

        # Insérer les options de norme (méthode 1 : une requête par valeur)
        ram_values = ["12", "16", "2", "3", "4", "6", "8"]
        for ram in ram_values:
            try:
                cur.execute("INSERT INTO ram_options (ram) VALUES (%s)", (ram,))
                print(f"✅ Ajouté RAM: {ram}")
            except psycopg2.IntegrityError:
                print(f"⚠️  RAM {ram} existe déjà")
                conn.rollback()  # Rollback pour cette insertion seulement

        brand_values = ['Essential', 'Hotwav', 'Nothing', 'Redmi']
        for brand in brand_values:
            try:
                cur.execute("INSERT INTO brands (brand) VALUES (%s)", (brand,))
                print(f"✅ Ajouté Brand: {brand}")
            except psycopg2.IntegrityError:
                print(f"⚠️  Brand {brand} existe déjà")
                conn.rollback()  # Rollback pour cette insertion seulement

        # colors_values = ['Alpine Loop L Indigo', 'Black', 'Black Titanium', 'Blue', 'Blue Titanium', 'Bronze', 'Brown', 'Chalk', 'Copper', 'Cream', 'Desert', 'Desert Titanium', 'Gold', 'Graphite', 'Gray', 'Green', 'Grey', 'Ice Blue', 'Indigo', 'Lavender', 'Lavender Purple', 'Midnight', 'Mint', 'Natural Titanium', 'Navy', 'Ocean', 'Olive', 'Phantom Black', 'Pink', 'Porcelain', 'Porcelaine', 'Purple', 'Red', 'Rose Gold', 'Silver', 'Space Gray', 'Space Grey', 'Starlight', 'Teal', 'Titanium', 'Trail Loop M/L Green/Grey', 'Trail Loop S/M Green/Grey', 'Ultramarine', 'White', 'White Titanium', 'Yellow']

        color_translations = {
            "alpine loop l indigo": "Bleu",
            "black": "Noir",
            "black titanium": "Noir",
            "blue": "Bleu",
            "blue titanium": "Bleu",
            "bronze": "Orange",
            "brown": "Orange",
            "chalk": "Blanc",
            "copper": "Orange",
            "cream": "Blanc",
            "desert": "Blanc",
            "desert titanium": "Blanc",
            "gold": "Blanc",
            "graphite": "Noir",
            "gray": "Noir",
            "green": "Vert",
            "grey": "Noir",
            "ice blue": "Bleu",
            "indigo": "Bleu",
            "lavender": "Violet",
            "lavender purple": "Violet",
            "midnight": "Bleu",
            "mint": "Vert",
            "natural titanium": "Blanc",
            "navy": "Bleu",
            "ocean": "Bleu",
            "olive": "Vert",
            "phantom black": "Noir",
            "pink": "Rose",
            "porcelain": "Blanc",
            "porcelaine": "Blanc",
            "purple": "Violet",
            "red": "Rouge",
            "rose gold": "Rose",
            "silver": "Blanc",
            "space gray": "Noir",
            "space grey": "Noir",
            "starlight": "Blanc",
            "teal": "Bleu",
            "titanium": "Blanc",
            "trail loop m/l green/grey": "Vert",
            "trail loop s/m green/grey": "Vert",
            "ultramarine": "Bleu",
            "white": "Blanc",
            "white titanium": "Blanc",
            "yellow": "Jaune",
        }

        for source, target in color_translations.items():
            color_source = source.lower()
            target_id = color_lookup.get(target.lower())
            if target_id is None:
                print(
                    f"⚠️  Impossible d'associer la couleur cible '{target}' pour '{color_source}'"
                )
                continue

            try:
                cur.execute(
                    """
                    INSERT INTO color_translations (color_source, color_target, color_target_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (color_source) DO UPDATE
                    SET color_target = EXCLUDED.color_target,
                        color_target_id = EXCLUDED.color_target_id
                    """,
                    (color_source, target, target_id),
                )
                print(
                    f"✅ Traduction couleur: {color_source} -> {target} (ID cible: {target_id})"
                )
            except psycopg2.Error as error:
                print(
                    f"❌ Erreur lors de l'insertion de la couleur {color_source}: {error}"
                )
                conn.rollback()

        conn.commit()

        print("🗑️  Après update")
        cur.execute("SELECT * FROM memory_options")
        memory_options = cur.fetchall()
        print("Memory options finales:", memory_options)

        cur.execute("SELECT * FROM ram_options")
        ram_options = cur.fetchall()
        print("RAM options finales:", ram_options)

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
