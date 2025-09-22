#!/usr/bin/env python3
"""Importer des produits de référence à partir d'un fichier CSV."""

from __future__ import annotations

import argparse
import csv
import os
import sys
import unicodedata
from dataclasses import dataclass
from typing import Dict, Iterable, Optional

import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import connection
from psycopg2.extras import DictCursor


@dataclass
class ImportStats:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0


COLUMN_MAP: Dict[str, str] = {
    "nom": "name",
    "modele": "model",
    "modle": "model",
    "marque": "brand",
    "capacite": "memory",
    "capacit": "memory",
    "ram": "ram",
    "connectivite": "device_type",
    "connectivit": "device_type",
    "couleur": "color",
    "norm": "norme",
    "tokens": "tokens",
    "ean": "ean",
    "partnumber": "part_number",
}


def _load_environment() -> None:
    """Charger les variables d'environnement disponibles."""

    current_dir = os.path.dirname(__file__)
    candidates = [
        os.path.join(current_dir, ".env"),
        os.path.join(current_dir, "..", ".env"),
        os.path.join(current_dir, "..", "..", ".env"),
    ]
    for path in candidates:
        if os.path.exists(path):
            load_dotenv(path)


def _normalize_header(header: str) -> str:
    """Normaliser un nom de colonne (suppression des accents et de la ponctuation)."""

    normalized = unicodedata.normalize("NFKD", header)
    without_accents = "".join(
        ch for ch in normalized if not unicodedata.combining(ch)
    )
    return "".join(ch for ch in without_accents.lower() if ch.isalnum())


def _clean(value: Optional[str]) -> Optional[str]:
    """Nettoyer une valeur brute issue du CSV."""

    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    lowered = cleaned.lower()
    if lowered in {"na", "n/a", "none", "null"}:
        return None
    return cleaned


def _build_header_mapping(headers: Iterable[str]) -> Dict[str, Optional[str]]:
    """Créer un mapping entre les en-têtes du fichier et les clés internes."""

    mapping: Dict[str, Optional[str]] = {}
    for header in headers:
        if header is None:
            continue
        normalized = _normalize_header(header)
        mapping[header] = COLUMN_MAP.get(normalized)
    return mapping


def _connect() -> connection:
    """Créer une connexion vers la base de données."""

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ ERROR: DATABASE_URL environment variable is not set")
        sys.exit(1)
    return psycopg2.connect(db_url, cursor_factory=DictCursor)


class ReferenceCache:
    """Gestion des tables de références (marques, couleurs, etc.)."""

    def __init__(self, cursor, default_tcp: int):
        self.cursor = cursor
        self.cache: Dict[str, Dict[str, int]] = {}
        self.created: Dict[str, int] = {
            "brands": 0,
            "colors": 0,
            "memory_options": 0,
            "device_types": 0,
            "ram_options": 0,
            "norme_options": 0,
        }
        self.default_tcp = default_tcp

    def _ensure(self, table: str, column_sql: str, value: Optional[str], *, insert_sql: str, params: tuple = ()) -> Optional[int]:
        if value is None:
            return None
        key = value.lower()
        table_cache = self.cache.setdefault(table, {})
        if key in table_cache:
            return table_cache[key]

        self.cursor.execute(
            f"SELECT id FROM {table} WHERE LOWER({column_sql}) = LOWER(%s)",
            (value,),
        )
        row = self.cursor.fetchone()
        if row:
            table_cache[key] = row["id"]
            return row["id"]

        self.cursor.execute(insert_sql, (value, *params))
        new_id = self.cursor.fetchone()["id"]
        table_cache[key] = new_id
        self.created[table] += 1
        return new_id

    def brand_id(self, value: Optional[str]) -> Optional[int]:
        return self._ensure(
            "brands",
            "brand",
            value,
            insert_sql="INSERT INTO brands (brand) VALUES (%s) RETURNING id",
        )

    def color_id(self, value: Optional[str]) -> Optional[int]:
        return self._ensure(
            "colors",
            "color",
            value,
            insert_sql="INSERT INTO colors (color) VALUES (%s) RETURNING id",
        )

    def memory_id(self, value: Optional[str]) -> Optional[int]:
        return self._ensure(
            "memory_options",
            "memory",
            value,
            insert_sql="INSERT INTO memory_options (memory, tcp_value) VALUES (%s, %s) RETURNING id",
            params=(self.default_tcp,),
        )

    def device_type_id(self, value: Optional[str]) -> Optional[int]:
        return self._ensure(
            "device_types",
            '"type"',
            value,
            insert_sql='INSERT INTO device_types ("type") VALUES (%s) RETURNING id',
        )

    def ram_id(self, value: Optional[str]) -> Optional[int]:
        return self._ensure(
            "ram_options",
            "ram",
            value,
            insert_sql="INSERT INTO ram_options (ram) VALUES (%s) RETURNING id",
        )

    def norme_id(self, value: Optional[str]) -> Optional[int]:
        return self._ensure(
            "norme_options",
            "norme",
            value,
            insert_sql="INSERT INTO norme_options (norme) VALUES (%s) RETURNING id",
        )


def _find_product_id(cursor, ean: Optional[str], model: Optional[str], brand_id: Optional[int]) -> Optional[int]:
    """Tenter de retrouver un produit existant."""

    if ean:
        cursor.execute("SELECT id FROM products WHERE ean = %s", (ean,))
        row = cursor.fetchone()
        if row:
            return row["id"]

    if model:
        if brand_id:
            cursor.execute(
                "SELECT id FROM products WHERE LOWER(model) = LOWER(%s) AND brand_id = %s",
                (model, brand_id),
            )
        else:
            cursor.execute(
                "SELECT id FROM products WHERE LOWER(model) = LOWER(%s)",
                (model,),
            )
        row = cursor.fetchone()
        if row:
            return row["id"]
    return None


def process_csv(conn: connection, csv_path: str, delimiter: str, default_tcp: int) -> ImportStats:
    stats = ImportStats()
    errors: list[str] = []

    with open(csv_path, newline="", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=delimiter)
        if not reader.fieldnames:
            print("❌ ERROR: impossible de lire les en-têtes du fichier CSV")
            sys.exit(1)

        header_map = _build_header_mapping(reader.fieldnames)
        recognized = {raw: mapped for raw, mapped in header_map.items() if mapped}
        if not recognized:
            print("❌ ERROR: aucune colonne reconnue dans le fichier CSV")
            sys.exit(1)

        missing_core = {"name", "model"} - set(recognized.values())
        if missing_core == {"name", "model"}:
            print("⚠️  AVERTISSEMENT: les colonnes Nom ou Modèle sont absentes, les produits risquent d'être ignorés")

        with conn.cursor() as cursor:
            ref_cache = ReferenceCache(cursor, default_tcp=default_tcp)

            for index, row in enumerate(reader, start=2):  # Start at 2 to tenir compte de l'en-tête
                normalized: Dict[str, Optional[str]] = {}
                for raw_key, value in row.items():
                    mapped = header_map.get(raw_key)
                    if not mapped:
                        continue
                    normalized[mapped] = _clean(value)

                description = normalized.get("name")
                model = normalized.get("model") or description

                if not description and not model:
                    stats.skipped += 1
                    continue

                brand_id = ref_cache.brand_id(normalized.get("brand"))
                memory_id = ref_cache.memory_id(normalized.get("memory"))
                color_id = ref_cache.color_id(normalized.get("color"))
                type_id = ref_cache.device_type_id(normalized.get("device_type"))
                ram_id = ref_cache.ram_id(normalized.get("ram"))
                norme_id = ref_cache.norme_id(normalized.get("norme"))

                ean = normalized.get("ean")
                part_number = normalized.get("part_number")

                product_id = _find_product_id(cursor, ean, model, brand_id)

                try:
                    if product_id:
                        cursor.execute(
                            """
                            UPDATE products
                               SET description = %s,
                                   model = %s,
                                   brand_id = %s,
                                   memory_id = %s,
                                   color_id = %s,
                                   type_id = %s,
                                   "RAM_id" = %s,
                                   norme_id = %s,
                                   ean = %s,
                                   part_number = %s
                             WHERE id = %s
                            """,
                            (
                                description,
                                model,
                                brand_id,
                                memory_id,
                                color_id,
                                type_id,
                                ram_id,
                                norme_id,
                                ean,
                                part_number,
                                product_id,
                            ),
                        )
                        stats.updated += 1
                    else:
                        cursor.execute(
                            """
                            INSERT INTO products (
                                description, model, brand_id, memory_id, color_id,
                                type_id, "RAM_id", norme_id, ean, part_number
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING id
                            """,
                            (
                                description,
                                model,
                                brand_id,
                                memory_id,
                                color_id,
                                type_id,
                                ram_id,
                                norme_id,
                                ean,
                                part_number,
                            ),
                        )
                        cursor.fetchone()
                        stats.inserted += 1
                    conn.commit()
                except Exception as exc:  # pylint: disable=broad-except
                    conn.rollback()
                    stats.errors += 1
                    errors.append(f"Ligne {index}: {exc}")

            if stats.errors:
                print("\n❌ Des erreurs ont été rencontrées lors de l'import :")
                for err in errors:
                    print(f"   - {err}")

            print("\n📊 Résumé de l'import :")
            print(f"   ➕ Produits insérés : {stats.inserted}")
            print(f"   🔁 Produits mis à jour : {stats.updated}")
            print(f"   ⏭️  Produits ignorés : {stats.skipped}")
            print(f"   ⚠️  Lignes en erreur : {stats.errors}")

            print("\n🗃️  Nouvelles entrées dans les tables de références :")
            for table, count in ref_cache.created.items():
                print(f"   - {table}: {count}")

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Importer des produits de référence en base")
    parser.add_argument("csv", help="Chemin du fichier CSV à importer")
    parser.add_argument(
        "--delimiter",
        default=";",
        help="Délimiteur utilisé dans le fichier (défaut: ';')",
    )
    parser.add_argument(
        "--default-tcp",
        type=int,
        default=0,
        help="Valeur TCP par défaut pour les nouvelles capacités mémoire",
    )
    args = parser.parse_args()

    csv_path = os.path.abspath(args.csv)
    if not os.path.exists(csv_path):
        print(f"❌ ERROR: fichier introuvable: {csv_path}")
        sys.exit(1)

    _load_environment()

    print("🚀 Début de l'import des produits de référence...")
    conn = _connect()
    try:
        process_csv(conn, csv_path, args.delimiter, args.default_tcp)
    finally:
        conn.close()
        print("✅ Import terminé")


if __name__ == "__main__":
    main()
