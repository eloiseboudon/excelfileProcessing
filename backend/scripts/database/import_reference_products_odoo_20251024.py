#!/usr/bin/env python3
"""
Script d'import simplifié pour lier les produits Odoo avec les produits de la base.

Utilisation:
    python import_odoo_products_simple.py products_odoo_20251023.csv

Le fichier CSV doit avoir:
    - Ligne 1: en-tête (ignoré)
    - Colonne 1: odoo_id
    - Colonne 2: nom du modèle à chercher dans la table products
"""

import csv
import os
import sys
from datetime import datetime
from typing import Optional, Tuple
from urllib.parse import urlparse

import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import connection
from psycopg2.extras import DictCursor


class ImportLogger:
    """Logger pour suivre les opérations d'import."""

    def __init__(self, verbose: bool = False):
        self.log_file = f"import_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        self.verbose = verbose
        self.stats = {
            'total': 0,
            'found_and_linked': 0,
            'created_and_linked': 0,
            'already_linked': 0,
            'errors': 0,
        }

    def log(self, message: str, level: str = "INFO"):
        """Écrire un message dans le fichier de log et l'afficher."""
        # Ne pas afficher les messages DEBUG à l'écran si verbose=False
        if level == "DEBUG" and not self.verbose:
            # Mais toujours les écrire dans le fichier
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_message = f"[{timestamp}] [{level}] {message}"
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_message + '\n')
            return

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] [{level}] {message}"
        print(log_message)

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_message + '\n')

    def log_summary(self):
        """Afficher le résumé des opérations."""
        self.log("\n" + "=" * 80)
        self.log("📊 RÉSUMÉ DE L'IMPORT")
        self.log("=" * 80)
        self.log(f"📝 Total de lignes traitées: {self.stats['total']}")
        self.log(f"✅ Produits trouvés et liés: {self.stats['found_and_linked']}")
        self.log(f"➕ Produits créés et liés: {self.stats['created_and_linked']}")
        self.log(f"🔗 Liens déjà existants: {self.stats['already_linked']}")
        self.log(f"❌ Erreurs: {self.stats['errors']}")
        self.log("=" * 80)
        self.log(f"📄 Log complet disponible dans: {self.log_file}")


def get_database_connection() -> connection:
    """Établir la connexion à la base de données."""
    load_dotenv()

    database_url = os.getenv('DATABASE_URL')

    if database_url:
        # Parser l'URL de connexion
        parsed = urlparse(database_url)
        # Remplacer postgresql+psycopg2 par postgresql si nécessaire
        if parsed.scheme in ('postgresql+psycopg2', 'postgres'):
            database_url = database_url.replace(parsed.scheme, 'postgresql', 1)

        conn = psycopg2.connect(database_url, cursor_factory=DictCursor)
    else:
        # Connexion à partir des variables individuelles
        conn = psycopg2.connect(
            dbname=os.getenv('POSTGRES_DB', 'tpvs_db'),
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD', ''),
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=os.getenv('POSTGRES_PORT', '5432'),
            cursor_factory=DictCursor,
        )

    return conn


def ensure_internal_products_table(conn: connection, logger: ImportLogger) -> bool:
    """Créer la table internal_products si elle n'existe pas."""
    try:
        with conn.cursor() as cursor:
            # Vérifier si la table existe
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'internal_products'
                )
            """
            )
            exists = cursor.fetchone()[0]

            if not exists:
                logger.log("Création de la table internal_products...")
                cursor.execute(
                    """
                    CREATE TABLE internal_products (
                        id SERIAL PRIMARY KEY,
                        product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                        odoo_id VARCHAR(200) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Ajouter les index uniques
                cursor.execute(
                    """
                    CREATE UNIQUE INDEX idx_internal_products_odoo_id_unique
                        ON internal_products (odoo_id)
                """
                )
                cursor.execute(
                    """
                    CREATE UNIQUE INDEX idx_internal_products_product_id_unique
                        ON internal_products (product_id)
                """
                )

                conn.commit()
                logger.log("✅ Table internal_products créée avec succès", "SUCCESS")
            else:
                logger.log("✓ Table internal_products existe déjà")

            return True
    except Exception as e:
        conn.rollback()
        logger.log(f"❌ Erreur lors de la création de la table: {e}", "ERROR")
        return False


def find_product_by_model(cursor, product_model: str) -> Optional[int]:
    """
    Chercher un produit par son nom (ou modèle).
    Retourne l'ID du produit si trouvé, None sinon.
    """
    # Recherche exacte sur le nom
    cursor.execute(
        """
        SELECT id FROM products 
        WHERE LOWER(TRIM(model)) = LOWER(TRIM(%s))
        LIMIT 1
    """,
        (product_model,),
    )

    result = cursor.fetchone()
    if result:
        return result['id']

    # Recherche exacte sur le modèle si pas trouvé par nom
    cursor.execute(
        """
        SELECT id FROM products 
        WHERE LOWER(TRIM(model)) = LOWER(TRIM(%s))
        LIMIT 1
    """,
        (product_model,),
    )

    result = cursor.fetchone()
    if result:
        return result['id']

    return None


def create_product(
    conn, cursor, product_model: str, logger: ImportLogger
) -> Optional[int]:
    """
    Créer un nouveau produit avec le nom fourni.
    Retourne l'ID du produit créé.
    """
    try:
        cursor.execute(
            """
            INSERT INTO products (model, description)
            VALUES ( %s, %s)
            RETURNING id
        """,
            (product_model, product_model),
        )

        result = cursor.fetchone()
        product_id = result['id'] if result else None

        if product_id:
            conn.commit()  # COMMIT IMMEDIAT
            logger.log(
                f"    [DEBUG] Product INSERT committed: id={product_id}", "DEBUG"
            )

        return product_id
    except Exception as e:
        conn.rollback()
        raise Exception(f"Erreur lors de la création du produit: {e}")


def check_link_exists(cursor, odoo_id: str = None, product_id: int = None) -> bool:
    """Vérifier si un lien existe déjà dans internal_products."""
    if odoo_id:
        cursor.execute(
            """
            SELECT id FROM internal_products WHERE odoo_id = %s
        """,
            (odoo_id,),
        )
        if cursor.fetchone():
            return True

    if product_id:
        cursor.execute(
            """
            SELECT id FROM internal_products WHERE product_id = %s
        """,
            (product_id,),
        )
        if cursor.fetchone():
            return True

    return False


def create_or_update_link(
    conn, cursor, odoo_id: str, product_id: int, logger: ImportLogger
) -> Tuple[bool, str]:
    """
    Créer ou mettre à jour le lien dans internal_products.
    Retourne (succès, action) où action peut être 'created', 'updated', ou 'exists'.
    """
    try:
        # Vérifier si le lien existe déjà par odoo_id
        cursor.execute(
            """
            SELECT id, product_id FROM internal_products WHERE odoo_id = %s
        """,
            (odoo_id,),
        )
        existing_by_odoo = cursor.fetchone()

        if existing_by_odoo:
            if existing_by_odoo['product_id'] == product_id:
                return True, 'exists'
            else:
                # Mettre à jour le product_id
                cursor.execute(
                    """
                    UPDATE internal_products 
                    SET product_id = %s
                    WHERE odoo_id = %s
                """,
                    (product_id, odoo_id),
                )
                conn.commit()  # COMMIT IMMEDIAT
                logger.log(f"    [DEBUG] UPDATE committed: odoo_id={odoo_id}", "DEBUG")
                return True, 'updated'

        # Vérifier si le product_id est déjà lié à un autre odoo_id
        cursor.execute(
            """
            SELECT id, odoo_id FROM internal_products WHERE product_id = %s
        """,
            (product_id,),
        )
        existing_by_product = cursor.fetchone()

        if existing_by_product:
            # Mettre à jour l'odoo_id
            cursor.execute(
                """
                UPDATE internal_products 
                SET odoo_id = %s
                WHERE product_id = %s
            """,
                (odoo_id, product_id),
            )
            conn.commit()  # COMMIT IMMEDIAT
            logger.log(
                f"    [DEBUG] UPDATE committed: product_id={product_id}", "DEBUG"
            )
            return True, 'updated'

        # Créer le nouveau lien
        cursor.execute(
            """
            INSERT INTO internal_products (odoo_id, product_id)
            VALUES (%s, %s)
        """,
            (odoo_id, product_id),
        )
        conn.commit()  # COMMIT IMMEDIAT
        logger.log(
            f"    [DEBUG] INSERT committed: odoo_id={odoo_id} → product_id={product_id}",
            "DEBUG",
        )

        # Vérifier que l'insertion a bien été faite
        cursor.execute(
            "SELECT COUNT(*) FROM internal_products WHERE odoo_id = %s", (odoo_id,)
        )
        count = cursor.fetchone()[0]
        logger.log(
            f"    [DEBUG] Vérification: {count} ligne(s) avec odoo_id={odoo_id}",
            "DEBUG",
        )

        return True, 'created'
    except Exception as e:
        conn.rollback()
        logger.log(f"    [DEBUG] ERREUR lors de create_or_update_link: {e}", "ERROR")
        raise


def verify_internal_products(conn: connection, logger: ImportLogger):
    """Vérifier le contenu de la table internal_products après l'import."""
    try:
        with conn.cursor() as cursor:
            # Compter le total de lignes
            cursor.execute("SELECT COUNT(*) FROM internal_products")
            total = cursor.fetchone()[0]

            logger.log("\n🔍 Vérification de la table internal_products:")
            logger.log(f"   Total de lignes dans internal_products: {total}")

            if total > 0:
                # Afficher quelques exemples
                cursor.execute(
                    """
                    SELECT ip.id, ip.odoo_id, ip.product_id, p.model 
                    FROM internal_products ip
                    LEFT JOIN products p ON ip.product_id = p.id
                    ORDER BY ip.id DESC
                    LIMIT 5
                """
                )
                rows = cursor.fetchall()

                logger.log("   Dernières entrées:")
                for row in rows:
                    logger.log(
                        f"     - ID={row['id']}, odoo_id={row['odoo_id']}, "
                        f"product_id={row['product_id']}, model='{row['model']}'"
                    )
            else:
                logger.log("   ⚠️  La table internal_products est VIDE !", "WARNING")
                logger.log(
                    "   ⚠️  Vérifiez les droits d'écriture et les contraintes de la table",
                    "WARNING",
                )

            return total
    except Exception as e:
        logger.log(f"❌ Erreur lors de la vérification: {e}", "ERROR")
        return -1


def process_csv(csv_path: str, conn: connection, logger: ImportLogger):
    """Traiter le fichier CSV ligne par ligne."""

    logger.log(f"📖 Ouverture du fichier: {csv_path}")

    try:
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            # Détecter automatiquement le délimiteur
            sample = csvfile.read(1024)
            csvfile.seek(0)

            delimiter = ';' if sample.count(';') > sample.count(',') else ','
            logger.log(f"Délimiteur détecté: '{delimiter}'")

            reader = csv.reader(csvfile, delimiter=delimiter)

            # Ignorer l'en-tête
            next(reader, None)

            line_number = 1
            for row in reader:
                line_number += 1
                logger.stats['total'] += 1

                # Vérifier qu'on a au moins 2 colonnes
                if len(row) < 2:
                    logger.log(
                        f"⚠️  Ligne {line_number}: pas assez de colonnes, ignorée",
                        "WARNING",
                    )
                    logger.stats['errors'] += 1
                    continue

                odoo_id = row[0].strip()
                product_model = row[1].strip()

                if not odoo_id or not product_model:
                    logger.log(
                        f"⚠️  Ligne {line_number}: odoo_id ou nom vide, ignorée",
                        "WARNING",
                    )
                    logger.stats['errors'] += 1
                    continue

                try:
                    with conn.cursor() as cursor:
                        # Étape 1: Chercher le produit
                        product_id = find_product_by_model(cursor, product_model)

                        if product_id:
                            # Produit trouvé
                            logger.log(
                                f"✓ Ligne {line_number} - Produit trouvé: '{product_model}' (ID: {product_id})"
                            )

                            # Créer le lien
                            success, action = create_or_update_link(
                                conn, cursor, odoo_id, product_id, logger
                            )

                            if action == 'created':
                                logger.log(
                                    f"  ➜ Lien créé: odoo_id={odoo_id} → product_id={product_id}",
                                    "SUCCESS",
                                )
                                logger.stats['found_and_linked'] += 1
                            elif action == 'updated':
                                logger.log(
                                    f"  ➜ Lien mis à jour: odoo_id={odoo_id} → product_id={product_id}",
                                    "SUCCESS",
                                )
                                logger.stats['found_and_linked'] += 1
                            else:
                                logger.log(
                                    f"  ➜ Lien déjà existant: odoo_id={odoo_id} → product_id={product_id}"
                                )
                                logger.stats['already_linked'] += 1

                        else:
                            # Produit non trouvé, le créer
                            logger.log(
                                f"➕ Ligne {line_number} - Produit non trouvé, création: '{product_model}'"
                            )

                            product_id = create_product(
                                conn, cursor, product_model, logger
                            )

                            if product_id:
                                logger.log(
                                    f"  ✓ Produit créé avec ID: {product_id}", "SUCCESS"
                                )

                                # Créer le lien
                                success, action = create_or_update_link(
                                    conn, cursor, odoo_id, product_id, logger
                                )

                                logger.log(
                                    f"  ➜ Lien créé: odoo_id={odoo_id} → product_id={product_id}",
                                    "SUCCESS",
                                )
                                logger.stats['created_and_linked'] += 1
                            else:
                                logger.log(
                                    "  ❌ Échec de la création du produit", "ERROR"
                                )
                                logger.stats['errors'] += 1

                        # Commit après chaque ligne pour éviter de perdre tout en cas d'erreur
                        conn.commit()

                except Exception as e:
                    conn.rollback()
                    logger.log(f"❌ Ligne {line_number} - Erreur: {str(e)}", "ERROR")
                    logger.stats['errors'] += 1

        logger.log("\n✅ Traitement du fichier terminé")

    except FileNotFoundError:
        logger.log(f"❌ Fichier non trouvé: {csv_path}", "ERROR")
        sys.exit(1)
    except Exception as e:
        logger.log(f"❌ Erreur lors de la lecture du fichier: {e}", "ERROR")
        sys.exit(1)


def main():
    """Point d'entrée principal du script."""

    # Vérifier les arguments
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    if verbose:
        sys.argv.remove('--verbose' if '--verbose' in sys.argv else '-v')

    logger = ImportLogger(verbose=verbose)
    logger.log("=" * 80)
    logger.log("🚀 DÉMARRAGE DE L'IMPORT ODOO → PRODUCTS")
    logger.log("=" * 80)
    if verbose:
        logger.log("Mode verbose activé - affichage des logs DEBUG", "INFO")

    # Vérifier les arguments
    if len(sys.argv) < 2:
        logger.log(
            "❌ Usage: python import_odoo_products_simple.py <chemin_csv> [--verbose]",
            "ERROR",
        )
        sys.exit(1)

    csv_path = sys.argv[1]

    if not os.path.exists(csv_path):
        logger.log(f"❌ Le fichier n'existe pas: {csv_path}", "ERROR")
        sys.exit(1)

    # Connexion à la base
    logger.log("🔌 Connexion à la base de données...")
    try:
        conn = get_database_connection()
        logger.log("✅ Connexion établie", "SUCCESS")
    except Exception as e:
        logger.log(f"❌ Erreur de connexion: {e}", "ERROR")
        sys.exit(1)

    try:
        # Créer la table internal_products si nécessaire
        if not ensure_internal_products_table(conn, logger):
            logger.log("❌ Impossible de créer la table internal_products", "ERROR")
            sys.exit(1)

        # Traiter le CSV
        process_csv(csv_path, conn, logger)

        # Vérifier que les données sont bien dans internal_products
        verify_internal_products(conn, logger)

        # Afficher le résumé
        logger.log_summary()

    finally:
        conn.close()
        logger.log("🔌 Connexion fermée")


if __name__ == "__main__":
    main()
