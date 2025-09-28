#!/usr/bin/env python3
"""Importer des produits de référence à partir d'un fichier CSV."""

from __future__ import annotations

import argparse
import csv
import os
import sys
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional, Set, Tuple

import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import connection
from psycopg2.extras import DictCursor


@dataclass
class ImportStats:
    inserted: int = 0
    updated: int = 0
    updated_by_ean: int = 0
    updated_by_model: int = 0
    skipped: int = 0
    errors: int = 0
    missing_references: Dict[str, list[str]] = field(default_factory=dict)
    unresolved_by_name: Dict[str, list[str]] = field(default_factory=dict)
    update_reasons: Dict[str, list[int]] = field(default_factory=dict)


COLUMN_MAP: Dict[str, str] = {
    "nom": "name",
    "modele": "model",
    "marque": "brand",
    "capacite": "memory",
    "ram": "ram",
    "couleur": "color",
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
    without_accents = "".join(ch for ch in normalized if not unicodedata.combining(ch))
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


def _strip_accents_lower(text: str) -> str:
    """Retirer les accents et convertir en minuscules."""

    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


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
        self.missing: Dict[str, Set[str]] = {
            "brands": set(),
            "colors": set(),
            "memory_options": set(),
            "device_types": set(),
            "ram_options": set(),
            "norme_options": set(),
        }
        self.unresolved_from_name: Dict[str, Set[str]] = {
            "device_types": set(),
            "ram_options": set(),
            "memory_options": set(),
            "norme_options": set(),
        }
        self.table_values_cache: Dict[tuple[str, str], list[tuple[int, list[str]]]] = {}
        self.table_columns_cache: Dict[str, Set[str]] = {}
        self.default_tcp = default_tcp

    def _column_name(self, column_sql: str) -> str:
        return column_sql.replace('"', "").strip()

    def _get_table_columns(self, table: str) -> Set[str]:
        if table not in self.table_columns_cache:
            self.cursor.execute(
                """
                SELECT column_name
                  FROM information_schema.columns
                 WHERE table_schema = 'public' AND table_name = %s
                """,
                (table,),
            )
            self.table_columns_cache[table] = {
                row["column_name"] for row in self.cursor.fetchall()
            }
        return self.table_columns_cache[table]

    def _load_table_values(self, table: str, column_sql: str) -> list[tuple[int, list[str]]]:
        key = (table, column_sql)
        if key in self.table_values_cache:
            return self.table_values_cache[key]

        columns = self._get_table_columns(table)
        primary_column = self._column_name(column_sql)
        extras = [
            col
            for col in ("name", "nom")
            if col in columns and col != primary_column
        ]
        select_parts = [f"{column_sql} AS primary_value"]
        for extra in extras:
            select_parts.append(f"{extra} AS {extra}")

        self.cursor.execute(
            f"SELECT id, {', '.join(select_parts)} FROM {table}"
        )
        rows: list[tuple[int, list[str]]] = []
        for row in self.cursor.fetchall():
            values: list[str] = []
            primary_value = row.get("primary_value")
            if primary_value:
                normalized = _strip_accents_lower(str(primary_value))
                if normalized:
                    values.append(normalized)
            for extra in extras:
                extra_value = row.get(extra)
                if extra_value:
                    normalized_extra = _strip_accents_lower(str(extra_value))
                    if normalized_extra:
                        values.append(normalized_extra)
            if values:
                rows.append((row["id"], values))

        self.table_values_cache[key] = rows
        return rows

    def _match_by_product_name(
        self, table: str, column_sql: str, product_name: Optional[str]
    ) -> Optional[int]:
        if not product_name:
            return None
        normalized_name = _strip_accents_lower(product_name)
        if not normalized_name:
            return None

        matches: list[tuple[int, int]] = []
        for item_id, values in self._load_table_values(table, column_sql):
            for value in values:
                if value and value in normalized_name:
                    matches.append((len(value), item_id))
                    break

        if not matches:
            return None

        matches.sort(reverse=True)
        return matches[0][1]

    def _ensure(
        self,
        table: str,
        column_sql: str,
        value: Optional[str],
        *,
        search_in_name: bool = False,
        product_name: Optional[str] = None,
    ) -> Optional[int]:
        candidate_id: Optional[int] = None
        if value is not None:
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

        if search_in_name:
            candidate_id = self._match_by_product_name(table, column_sql, product_name)
            if candidate_id:
                if value:
                    key = value.lower()
                    self.cache.setdefault(table, {})[key] = candidate_id
                return candidate_id
            if value is None and product_name:
                self.unresolved_from_name.setdefault(table, set()).add(product_name)

        if value:
            self.missing.setdefault(table, set()).add(value)
        return candidate_id

    def brand_id(self, value: Optional[str]) -> Optional[int]:
        return self._ensure("brands", "brand", value)

    def color_id(self, value: Optional[str]) -> Optional[int]:
        if value is None:
            return None

        key = value.lower()
        colors_cache = self.cache.setdefault("colors", {})
        if key in colors_cache:
            return colors_cache[key]

        self.cursor.execute(
            "SELECT id FROM colors WHERE LOWER(color) = LOWER(%s)",
            (value,),
        )
        row = self.cursor.fetchone()
        if row:
            colors_cache[key] = row["id"]
            return row["id"]

        translations_cache = self.cache.setdefault("color_translations", {})
        if key in translations_cache:
            return translations_cache[key]

        self.cursor.execute(
            """
            SELECT color_target_id
              FROM color_translations
             WHERE LOWER(color_source) = LOWER(%s)
            """,
            (value,),
        )
        row = self.cursor.fetchone()
        if row:
            translations_cache[key] = row["color_target_id"]
            colors_cache[key] = row["color_target_id"]
            return row["color_target_id"]

        self.missing.setdefault("colors", set()).add(value)
        return None

    def memory_id(
        self, value: Optional[str], product_name: Optional[str]
    ) -> Optional[int]:
        return self._ensure(
            "memory_options",
            "memory",
            value,
            search_in_name=True,
            product_name=product_name,
        )

    def device_type_id(
        self, value: Optional[str], product_name: Optional[str]
    ) -> Optional[int]:
        return self._ensure(
            "device_types",
            '"type"',
            value,
            search_in_name=True,
            product_name=product_name,
        )

    def ram_id(self, value: Optional[str], product_name: Optional[str]) -> Optional[int]:
        return self._ensure(
            "ram_options",
            "ram",
            value,
            search_in_name=True,
            product_name=product_name,
        )

    def norme_id(self, value: Optional[str], product_name: Optional[str]) -> Optional[int]:
        return self._ensure(
            "norme_options",
            "norme",
            value,
            search_in_name=True,
            product_name=product_name,
        )


def _find_product_id(
    cursor, ean: Optional[str], model: Optional[str], brand_id: Optional[int]
) -> Tuple[Optional[int], Optional[str]]:
    """Tenter de retrouver un produit existant et indiquer la logique utilisée."""

    if ean:
        cursor.execute("SELECT id FROM products WHERE ean = %s", (ean,))
        row = cursor.fetchone()
        if row:
            return row["id"], "ean"

    if model:
        if brand_id:
            cursor.execute(
                "SELECT id FROM products WHERE LOWER(model) = LOWER(%s) AND brand_id = %s",
                (model, brand_id),
            )
            reason = "model+brand"
        else:
            cursor.execute(
                "SELECT id FROM products WHERE LOWER(model) = LOWER(%s)",
                (model,),
            )
            reason = "model"
        row = cursor.fetchone()
        if row:
            return row["id"], reason
    return None, None


def process_csv(
    conn: connection, csv_path: str, delimiter: str, default_tcp: int
) -> ImportStats:
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
            print(
                "⚠️  AVERTISSEMENT: les colonnes Nom ou Modèle sont absentes, les produits risquent d'être ignorés"
            )

        with conn.cursor() as cursor:
            ref_cache = ReferenceCache(cursor, default_tcp=default_tcp)

            for index, row in enumerate(
                reader, start=2
            ):  # Start at 2 to tenir compte de l'en-tête
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

                name_hint = description or model

                brand_id = ref_cache.brand_id(normalized.get("brand"))
                memory_id = ref_cache.memory_id(
                    normalized.get("memory"), name_hint
                )
                color_id = ref_cache.color_id(normalized.get("color"))
                type_id = ref_cache.device_type_id(
                    normalized.get("device_type"), name_hint
                )
                ram_id = ref_cache.ram_id(normalized.get("ram"), name_hint)
                norme_id = ref_cache.norme_id(normalized.get("norme"), name_hint)

                ean = normalized.get("ean")
                part_number = normalized.get("part_number")

                product_id, match_reason = _find_product_id(
                    cursor, ean, model, brand_id
                )

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
                        if match_reason == "ean":
                            stats.updated_by_ean += 1
                        elif match_reason in {"model", "model+brand"}:
                            stats.updated_by_model += 1
                        if match_reason:
                            stats.update_reasons.setdefault(match_reason, []).append(index)
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
            if stats.updated:
                print(
                    f"      ↳ dont {stats.updated_by_ean} par EAN et {stats.updated_by_model} par modèle"
                )
            print(f"   ⏭️  Produits ignorés : {stats.skipped}")
            print(f"   ⚠️  Lignes en erreur : {stats.errors}")

            stats.missing_references = {
                table: sorted(values)
                for table, values in ref_cache.missing.items()
                if values
            }
            stats.unresolved_by_name = {
                table: sorted(values)
                for table, values in ref_cache.unresolved_from_name.items()
                if values
            }

            if stats.missing_references or stats.unresolved_by_name:
                print("\n⚠️  Références manquantes ou non résolues :")
                for table, values in stats.missing_references.items():
                    joined = ", ".join(values)
                    print(f"   - {table}: {joined}")
                for table, names in stats.unresolved_by_name.items():
                    joined = "; ".join(names)
                    print(f"   - {table} (d'après le nom): {joined}")
            else:
                print("\n✅ Toutes les références nécessaires ont été trouvées.")

            if stats.update_reasons:
                print("\nℹ️  Détails des mises à jour :")
                for reason, lines in stats.update_reasons.items():
                    joined = ", ".join(str(line) for line in lines)
                    print(f"   - {reason}: lignes {joined}")

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Importer des produits de référence en base"
    )
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
