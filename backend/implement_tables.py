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

        print("🗑️  Nettoyage des tables existantes...")
        # Nettoyer les tables existantes
        cur.execute(
            """
            TRUNCATE TABLE suppliers, brands, colors, memory_options, device_types, exclusions, color_translations,graph_settings RESTART IDENTITY CASCADE;
        """
        )
        conn.commit()

        print("👥 Insertion des fournisseurs...")
        # Insérer les fournisseurs
        cur.execute(
            """
            INSERT INTO suppliers (name) VALUES
            ('Yuka'),('supplier2');
        """
        )

        print("📄 Insertion des formats d'import...")
        # Insérer les formats d'import
        cur.execute(
            """
            INSERT INTO format_imports (supplier_id, column_name, column_order) VALUES
            (1, 'description', 2),
            (1, 'model', 2),
            (1, 'quantity', 3),
            (1, 'selling_price', 4),
            (1, 'ean', 7);
        """
        )

        print("🏷️  Insertion des marques...")
        # Insérer les marques
        cur.execute(
            """
            INSERT INTO brands(brand) VALUES 
            ('Samsung'), ('Apple'), ('Huawei'), ('Xiaomi'), ('Oppo'),
            ('Dyson'), ('Sony'), ('LG'), ('Google'), ('Microsoft'), ('Lenovo'), ('Asus'),
            ('Dell'), ('HP'), ('Acer'), ('OnePlus'), ('Realme'),('Fairphone'),('JBL'), ('Bose'),
            ('Motorola'), ('Nokia'), ('Vivo'), ('ZTE'), ('Honor'),('GoPro'), ('Canon'), ('Nikon'),
            ('TCL'), ('Alcatel'), ('BlackBerry'), ('Panasonic'), ('Fujitsu'), ('Sharp'), ('Razer'), ('Logitech'),
            ('Corsair');
        """
        )

        print("💾 Insertion des options de mémoire...")
        # Insérer les options de mémoire
        cur.execute(
            """
            INSERT INTO memory_options (memory, tcp_value) VALUES 
            ('32GB', 10),('64GB', 12), ('128GB', 14), ('256GB', 14), ('512GB', 14);
        """
        )

        print("🎨 Insertion des couleurs...")
        # Insérer les couleurs
        cur.execute(
            """
            INSERT INTO colors (color) VALUES 
            ('Blanc'), ('Noir'), ('Bleu'), ('Rouge'), ('Vert'),('Orange'),('Violet'),('Jaune'),('Rose');
        """
        )

        print("🔄 Insertion des traductions de couleurs...")
        # Insérer les traductions de couleurs
        cur.execute(
            """
            INSERT INTO color_translations (color_source, color_target, color_target_id) VALUES
            ('black', 'Noir', 2),
            ('dark grey', 'Noir', 2),
            ('dark gray', 'Noir', 2),
            ('white', 'Blanc', 1),
            ('starlight', 'Blanc', 1),
            ('blue', 'Bleu', 3),
            ('blau', 'Bleu', 3),
            ('midnight', 'Bleu', 3),
            ('ultramarine', 'Bleu', 3),
            ('red', 'Rouge', 4),
            ('pink', 'Rose', 9),
            ('green', 'Vert', 5),
            ('orange', 'Orange', 6),
            ('purple', 'Violet', 7),
            ('gold', 'Blanc', 1),
            ('silver', 'Blanc', 1),
            ('grey', 'Noir', 2),
            ('gray', 'Noir', 2),
            ('champagne', 'Blanc', 1),
            ('rose', 'Rose', 9),
            ('yellow', 'Jaune', 8);
        """
        )

        print("📱 Insertion des types d'appareils...")
        # Insérer les types d'appareils
        cur.execute(
            """
            INSERT INTO device_types (type) VALUES 
            ('Téléphone'), ('Tablette'), ('Montre'), ('Ordinateur'), ('Accessoire'),('Ecouteur'),('Chargeur'),('Câble'),('A définir');
        """
        )

        print("🚫 Insertion des exclusions...")
        # Insérer les exclusions
        cur.execute(
            """
            INSERT INTO exclusions (term) VALUES 
            ('Mac'), ('Backbone'), ('Bulk'), ('OH25B'), ('Soundbar');
        """
        )

        print("📊 Insertion des paramètres de graphique...")
        # Insérer les paramètres de graphique
        cur.execute(
            """
            INSERT INTO graph_settings (name, visible) VALUES 
            ('global', True),('product', False),('relative', False),('distribution', False),
            ('stdev', False),('range', False),('index', False),('correlation', False),('anomalies', False);
        """
        )

        print("📱Ajout produits")
        cur.execute(
            """
            INSERT INTO products (model,description, brand_id, color_id, memory_id, type_id) VALUES
            ('Apple 20W USB-C Adapter - White', 'Apple 20W USB-C Adapter - White', 2, 1, null,null);
        """
        )

        # Valider toutes les transactions
        conn.commit()

        # Afficher un résumé
        print("\n📈 Résumé des données insérées:")
        tables = [
            ('suppliers', 'Fournisseurs'),
            ('brands', 'Marques'),
            ('colors', 'Couleurs'),
            ('memory_options', 'Options mémoire'),
            ('device_types', 'Types d\'appareils'),
            ('exclusions', 'Exclusions'),
            ('color_translations', 'Traductions couleurs'),
            ('graph_settings', 'Paramètres graphiques'),
            ('products', 'Produits'),
        ]

        for table, description in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"  ✅ {description}: {count} entrées")

        print("\n🎉 Implémentation des tables terminée avec succès!")

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
