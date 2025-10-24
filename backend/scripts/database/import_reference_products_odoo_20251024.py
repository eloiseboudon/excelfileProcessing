#!/usr/bin/env python3
"""Importer des produits de référence à partir d'un fichier CSV.

Utilisation rapide
===================

1. Exporter ou copier le fichier ``products_odoo_20251023.csv`` (ou un
   équivalent) sur la machine qui possède l'accès à la base Postgres.
2. Fournir une URL de connexion Postgres soit via la variable d'environnement
   ``DATABASE_URL``, soit en passant l'option ``--database-url`` au script (le
   format attendu est ``postgresql://user:password@host:port/db`` mais les
   variantes SQLAlchemy telles que ``postgresql+psycopg2://`` sont également
   acceptées). Si aucune URL explicite n'est fournie, le script tentera
   automatiquement de construire une connexion à partir des variables
   ``POSTGRES_DB``, ``POSTGRES_USER`` et associées.
3. Lancer le script :

   ``python backend/scripts/database/import_reference_products_odoo_20251024.py \
   path/to/products_odoo_20251023.csv``

   Des options supplémentaires sont disponibles via ``--help`` (délimiteur du
   CSV, valeur TCP par défaut, génération d'un rapport JSON des références
   manquantes, etc.).

Le script peut être exécuté sur une base « vivante » : il crée les produits
absents, met à jour ceux qui existent déjà et synchronise les entrées de
``internal_products``. Il n'est donc **pas** nécessaire de vider ou de
recréer les tables cibles au préalable. Pensez néanmoins à effectuer une
sauvegarde de la base avant l'import pour pouvoir revenir en arrière en cas de
mauvaise manipulation.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import sys
import unicodedata
from urllib.parse import urlparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import connection
from psycopg2.extras import DictCursor


@dataclass
class ImportStats:
    inserted: int = 0
    updated: int = 0
    updated_by_ean: int = 0
    updated_by_name: int = 0
    skipped: int = 0
    errors: int = 0
    internal_inserted: int = 0
    internal_updated: int = 0
    missing_references: Dict[str, list[str]] = field(default_factory=dict)
    unresolved_by_name: Dict[str, list[str]] = field(default_factory=dict)
    update_reasons: Dict[str, list[int]] = field(default_factory=dict)
    truncations: Dict[int, List["TruncationInfo"]] = field(default_factory=dict)

    not_imported: Dict[int, "NotImportedInfo"] = field(default_factory=dict)



@dataclass
class TruncationInfo:
    column: str
    max_length: int
    original_length: int


@dataclass
class NotImportedInfo:
    label: str
    reason: str



COLUMN_MAP: Dict[str, str] = {
    "nom": "name",
    "name": "name",
    "modele": "model",
    "model": "model",
    "marque": "brand",
    "brand": "brand",
    "capacite": "memory",
    "memory": "memory",
    "ram": "ram",
    "couleur": "color",
    "color": "color",
    "ean": "ean",
    "partnumber": "part_number",
    "part_number": "part_number",
    "productid": "product_id",
    "insertintointernalproductsodooidproductid": "internal_product_values",
    "insertintoproductsiddescription": "product_values",
}


def _load_environment() -> None:
    """Charger les variables d'environnement disponibles."""

    current_dir = Path(__file__).resolve().parent
    candidates: list[Path] = []
    directory = current_dir
    while True:
        candidates.append(directory / ".env")
        if directory == directory.parent:
            break
        directory = directory.parent

    for path in reversed(candidates):
        if path.exists():
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


def _strip_wrapping_quotes(value: str) -> str:
    if value.startswith("\"") and value.endswith("\""):
        return value[1:-1]
    return value


def _coerce_int(value: Optional[object]) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return int(stripped)
        except ValueError:
            return None
    return None


def _parse_internal_product_values(
    raw: Optional[str],
) -> Tuple[Optional[str], Optional[int]]:
    if not raw:
        return None, None
    cleaned = _strip_wrapping_quotes(raw.strip()).rstrip(";")
    if not cleaned:
        return None, None
    try:
        parsed = ast.literal_eval(cleaned)
    except (SyntaxError, ValueError):
        return None, None
    if isinstance(parsed, (list, tuple)) and len(parsed) == 2:
        odoo_id = str(parsed[0]).strip() if parsed[0] is not None else None
        product_id = _coerce_int(parsed[1])
        return (odoo_id or None), product_id
    return None, None


def _parse_product_values(
    raw: Optional[str],
) -> Tuple[Optional[int], Optional[str]]:
    if not raw:
        return None, None
    cleaned = _strip_wrapping_quotes(raw.strip()).rstrip(";")
    if not cleaned:
        return None, None
    try:
        parsed = ast.literal_eval(cleaned)
    except (SyntaxError, ValueError):
        return None, None
    if isinstance(parsed, (list, tuple)) and parsed:
        product_id = _coerce_int(parsed[0])
        description: Optional[str] = None
        if len(parsed) > 1 and parsed[1] is not None:
            description = str(parsed[1]).strip() or None
        return product_id, description
    return None, None


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


def _normalise_db_url(db_url: str) -> str:
    """Adapter l'URL de connexion aux formats attendus par ``psycopg2``.

    Les projets basés sur SQLAlchemy utilisent souvent des schémas de la
    forme ``postgresql+psycopg2://`` (ou ``postgresql+asyncpg://``). Ces
    variantes ne sont pas comprises par ``psycopg2.connect`` qui attend un
    schéma « pur » (``postgresql://``). Cette fonction supprime simplement la
    partie ``+driver`` quand le schéma est compatible Postgres.
    """

    if "://" not in db_url:
        return db_url

    scheme, rest = db_url.split("://", 1)
    if "+" in scheme:
        base_scheme, _driver = scheme.split("+", 1)
        if base_scheme in {"postgresql", "postgres"}:
            return f"{base_scheme}://{rest}"
    if scheme == "postgres":
        return f"postgresql://{rest}"
    return db_url


def _build_db_url_from_parts() -> Optional[str]:
    """Construire une URL à partir des variables ``POSTGRES_*`` le cas échéant."""

    database = _clean(os.getenv("POSTGRES_DB") or os.getenv("PGDATABASE"))
    user = _clean(os.getenv("POSTGRES_USER") or os.getenv("PGUSER"))
    password = os.getenv("POSTGRES_PASSWORD") or os.getenv("PGPASSWORD")
    host = _clean(
        os.getenv("POSTGRES_HOST")
        or os.getenv("PGHOST")
        or os.getenv("POSTGRES_SERVER")
        or os.getenv("DB_HOST")
        or os.getenv("DATABASE_HOST")
        or "localhost"
    )
    port = _clean(
        os.getenv("POSTGRES_PORT")
        or os.getenv("PGPORT")
        or os.getenv("DB_PORT")
        or os.getenv("DATABASE_PORT")
        or "5432"
    )

    if not database or not user:
        return None

    credentials = user
    if password:
        credentials = f"{user}:{password}"

    host_part = host or "localhost"
    port_part = f":{port}" if port else ""
    return f"postgresql://{credentials}@{host_part}{port_part}/{database}"


def _describe_db_url(db_url: str) -> str:
    parsed = urlparse(db_url)
    username = parsed.username or "?"
    hostname = parsed.hostname or "?"
    port = parsed.port or "?"
    database = parsed.path.lstrip("/") or "?"
    return f"user={username} host={hostname} port={port} db={database}"


def _candidate_db_urls(explicit: Optional[str]) -> list[str]:
    candidates: list[str] = []
    seen: Set[str] = set()

    def add(url: Optional[str]) -> None:
        if not url:
            return
        normalized = _normalise_db_url(url.strip())
        if normalized and normalized not in seen:
            seen.add(normalized)
            candidates.append(normalized)

    add(explicit)
    add(os.getenv("DATABASE_URL"))
    add(_build_db_url_from_parts())

    return candidates


def _connect(candidates: list[str]) -> connection:
    """Créer une connexion vers la base de données à partir des candidats."""

    attempts: list[tuple[str, str]] = []
    last_error: Optional[Exception] = None

    for url in candidates:
        description = _describe_db_url(url)
        print(f"🔌 Tentative de connexion ({description})")
        try:
            return psycopg2.connect(url, cursor_factory=DictCursor)
        except psycopg2.OperationalError as exc:  # pragma: no cover - dépend d'un env externe
            attempts.append((description, str(exc).strip()))
            last_error = exc
        except psycopg2.Error as exc:  # pragma: no cover - dépend d'un env externe
            attempts.append((description, str(exc).strip()))
            last_error = exc

    details = [
        "❌ Impossible de se connecter à la base de données après plusieurs tentatives:",
    ]
    for description, error in attempts:
        details.append(f"   - {description}: {error}")
    details.append(
        "   → Vérifiez vos identifiants ou fournissez l'option --database-url"
        " (ex: postgresql://user:password@host:5432/ajtpro)."
    )

    message = "\n".join(details)
    if last_error is not None:
        raise RuntimeError(message) from last_error
    raise RuntimeError(message)


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


class ProductValueSanitizer:
    """S'assure que les valeurs texte respectent les contraintes de longueur."""

    def __init__(self, cursor):
        self.max_lengths = self._load_column_lengths(cursor)

    def _load_column_lengths(self, cursor) -> Dict[str, Optional[int]]:
        cursor.execute(
            """
            SELECT column_name, character_maximum_length
              FROM information_schema.columns
             WHERE table_schema = 'public' AND table_name = 'products'
            """
        )
        lengths: Dict[str, Optional[int]] = {}
        for row in cursor.fetchall():
            lengths[row["column_name"]] = row["character_maximum_length"]
        return lengths

    def sanitize(
        self, values: Dict[str, Optional[str]]
    ) -> Tuple[Dict[str, Optional[str]], List[TruncationInfo]]:
        sanitized = dict(values)
        truncations: List[TruncationInfo] = []
        for column, value in values.items():
            if value is None:
                continue
            max_length = self.max_lengths.get(column)
            if max_length and len(value) > max_length:
                sanitized[column] = value[:max_length].rstrip()
                truncations.append(
                    TruncationInfo(
                        column=column,
                        max_length=max_length,
                        original_length=len(value),
                    )
                )
        return sanitized, truncations


def _find_product_id(
    cursor,
    ean: Optional[str],
    name: Optional[str],
    model: Optional[str],
    brand_id: Optional[int],
    explicit_id: Optional[int] = None,
) -> Tuple[Optional[int], Optional[str]]:
    """Tenter de retrouver un produit existant et indiquer la logique utilisée."""

    if explicit_id is not None:
        cursor.execute("SELECT id FROM products WHERE id = %s", (explicit_id,))
        row = cursor.fetchone()
        if row:
            return row["id"], "id"

    if ean:
        cursor.execute("SELECT id FROM products WHERE ean = %s", (ean,))
        row = cursor.fetchone()
        if row:
            return row["id"], "ean"

    search_label = name or model
    if search_label:
        if brand_id:
            cursor.execute(
                """
                SELECT id FROM products
                 WHERE LOWER(description) = LOWER(%s) AND brand_id = %s
                """,
                (search_label, brand_id),
            )
            reason = "name+brand"
        else:
            cursor.execute(
                "SELECT id FROM products WHERE LOWER(description) = LOWER(%s)",
                (search_label,),
            )
            reason = "name"
        row = cursor.fetchone()
        if row:
            return row["id"], reason

    if model and not name:
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
            return row["id"], "model"
    return None, None


def _sync_internal_product(
    cursor, odoo_id: Optional[str], product_id: Optional[int]
) -> Tuple[bool, bool]:
    if not odoo_id or not product_id:
        return False, False

    cursor.execute(
        "SELECT id, product_id FROM internal_products WHERE odoo_id = %s",
        (odoo_id,),
    )
    row = cursor.fetchone()
    if row:
        if row["product_id"] != product_id:
            cursor.execute(
                "UPDATE internal_products SET product_id = %s WHERE id = %s",
                (product_id, row["id"]),
            )
            return False, True
        return False, False

    cursor.execute(
        "SELECT id, odoo_id FROM internal_products WHERE product_id = %s",
        (product_id,),
    )
    row = cursor.fetchone()
    if row:
        if row["odoo_id"] != odoo_id:
            cursor.execute(
                "UPDATE internal_products SET odoo_id = %s WHERE id = %s",
                (odoo_id, row["id"]),
            )
            return False, True
        return False, False

    cursor.execute(
        "INSERT INTO internal_products (odoo_id, product_id) VALUES (%s, %s)",
        (odoo_id, product_id),
    )
    return True, False


def process_csv(
    conn: connection,
    csv_path: str,
    delimiter: str,
    default_tcp: int,
    missing_report_path: Optional[str] = None,
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
            sanitizer = ProductValueSanitizer(cursor)

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

                internal_odoo_id, internal_product_id = _parse_internal_product_values(
                    normalized.get("internal_product_values")
                )
                tuple_product_id, tuple_description = _parse_product_values(
                    normalized.get("product_values")
                )

                if (
                    internal_product_id is not None
                    and tuple_product_id is not None
                    and internal_product_id != tuple_product_id
                ):
                    stats.errors += 1
                    errors.append(
                        "Ligne {}: incohérence des identifiants produits ({}/{}).".format(
                            index, internal_product_id, tuple_product_id
                        )
                    )
                    product_label = (
                        description
                        or tuple_description
                        or normalized.get("model")
                        or "(inconnu)"
                    )
                    stats.not_imported[index] = NotImportedInfo(
                        label=product_label,
                        reason="Identifiants produit différents entre les colonnes d'insertion",
                    )
                    continue

                explicit_product_id = _coerce_int(normalized.get("product_id"))
                for candidate in (internal_product_id, tuple_product_id):
                    if explicit_product_id is None and candidate is not None:
                        explicit_product_id = candidate

                if not description and tuple_description:
                    description = tuple_description
                if not model and description:
                    model = description

                if not description and not model:
                    product_label = normalized.get("name") or normalized.get("model") or "(inconnu)"
                    stats.skipped += 1
                    stats.not_imported[index] = NotImportedInfo(
                        label=product_label,
                        reason="Nom et modèle absents après nettoyage",
                    )
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

                sanitized_strings, truncations = sanitizer.sanitize(
                    {
                        "description": description,
                        "model": model,
                        "ean": ean,
                        "part_number": part_number,
                    }
                )
                description = sanitized_strings.get("description")
                model = sanitized_strings.get("model") or description
                ean = sanitized_strings.get("ean")
                part_number = sanitized_strings.get("part_number")
                if truncations:
                    stats.truncations[index] = truncations

                product_id, match_reason = _find_product_id(
                    cursor,
                    ean,
                    description,
                    model,
                    brand_id,
                    explicit_product_id,
                )

                try:
                    final_product_id: Optional[int]
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
                        final_product_id = product_id
                        if match_reason == "ean":
                            stats.updated_by_ean += 1
                        elif match_reason in {
                            "name",
                            "name+brand",
                            "model",
                        }:
                            stats.updated_by_name += 1
                        if match_reason:
                            stats.update_reasons.setdefault(match_reason, []).append(index)
                    else:
                        columns = [
                            "description",
                            "model",
                            "brand_id",
                            "memory_id",
                            "color_id",
                            "type_id",
                            '"RAM_id"',
                            "norme_id",
                            "ean",
                            "part_number",
                        ]
                        values = [
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
                        ]
                        if explicit_product_id is not None:
                            columns.insert(0, "id")
                            values.insert(0, explicit_product_id)
                        placeholders = ", ".join(["%s"] * len(columns))
                        cursor.execute(
                            f"INSERT INTO products ({', '.join(columns)}) "
                            f"VALUES ({placeholders}) RETURNING id",
                            values,
                        )
                        row = cursor.fetchone()
                        final_product_id = row["id"] if row else None
                        stats.inserted += 1
                    if final_product_id is not None:
                        inserted_internal, updated_internal = _sync_internal_product(
                            cursor, internal_odoo_id, final_product_id
                        )
                        if inserted_internal:
                            stats.internal_inserted += 1
                        if updated_internal:
                            stats.internal_updated += 1
                    conn.commit()
                except Exception as exc:  # pylint: disable=broad-except
                    conn.rollback()
                    stats.errors += 1
                    errors.append(f"Ligne {index}: {exc}")
                    product_label = description or model or "(inconnu)"
                    stats.not_imported[index] = NotImportedInfo(
                        label=product_label,
                        reason=f"Erreur lors de l'écriture en base: {exc}",
                    )

            if stats.errors:
                print("\n❌ Des erreurs ont été rencontrées lors de l'import :")
                for err in errors:
                    print(f"   - {err}")

            print("\n📊 Résumé de l'import :")
            print(f"   ➕ Produits insérés : {stats.inserted}")
            print(f"   🔁 Produits mis à jour : {stats.updated}")
            if stats.updated:
                print(
                    f"      ↳ dont {stats.updated_by_ean} par EAN et {stats.updated_by_name} par nom"
                )
            print(
                f"   🧩 Liens internal_products insérés : {stats.internal_inserted}"
            )
            print(
                f"   🛠️  Liens internal_products mis à jour : {stats.internal_updated}"
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

            has_missing = bool(stats.missing_references or stats.unresolved_by_name)

            if has_missing:
                print("\n⚠️  Références manquantes ou non résolues :")
                for table, values in stats.missing_references.items():
                    joined = ", ".join(values)
                    print(f"   - {table}: {joined}")
                for table, names in stats.unresolved_by_name.items():
                    joined = "; ".join(names)
                    print(f"   - {table} (d'après le nom): {joined}")
            else:
                print("\n✅ Toutes les références nécessaires ont été trouvées.")

            if missing_report_path:
                _write_missing_report(missing_report_path, stats, has_missing)

            if stats.update_reasons:
                print("\nℹ️  Détails des mises à jour :")
                for reason, lines in stats.update_reasons.items():
                    joined = ", ".join(str(line) for line in lines)
                    print(f"   - {reason}: lignes {joined}")

            if stats.truncations:
                print("\n✂️  Valeurs tronquées pour respecter les contraintes :")
                for line, infos in sorted(stats.truncations.items()):
                    details = ", ".join(
                        f"{info.column} (max {info.max_length}, initiale {info.original_length} caractères)"
                        for info in infos
                    )
                    print(f"   - Ligne {line}: {details}")

            if stats.not_imported:
                print("\n🚫 Produits non importés :")
                for line, info in sorted(stats.not_imported.items()):
                    label = info.label.strip()
                    display = f" ({label})" if label and label != "(inconnu)" else ""
                    print(f"   - Ligne {line}{display}: {info.reason}")


    return stats


def _write_missing_report(path: str, stats: ImportStats, has_missing: bool) -> None:
    """Sauvegarder les références manquantes ou confirmées dans un fichier JSON."""

    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    payload = {
        "missing_references": stats.missing_references,
        "unresolved_by_name": stats.unresolved_by_name,
    }

    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)

    status = "enregistré" if has_missing else "créé (aucune référence manquante)"
    print(f"   → Rapport {status} dans : {os.path.abspath(path)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Importer des produits de référence en base"
    )
    parser.add_argument("csv", help="Chemin du fichier CSV à importer")
    parser.add_argument(
        "--database-url",
        help="URL de connexion Postgres (sinon utiliser la variable d'environnement DATABASE_URL)",
    )
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
    parser.add_argument(
        "--missing-report",
        help="Chemin du fichier JSON où enregistrer les références manquantes",
    )
    args = parser.parse_args()

    csv_path = os.path.abspath(args.csv)
    if not os.path.exists(csv_path):
        print(f"❌ ERROR: fichier introuvable: {csv_path}")
        sys.exit(1)

    _load_environment()

    print("🚀 Début de l'import des produits de référence...")
    candidates = _candidate_db_urls(args.database_url)
    if not candidates:
        print("❌ ERROR: aucune URL de base de données disponible.")
        print(
            "   → définissez la variable d'environnement DATABASE_URL,"
            " POSTGRES_DB/POSTGRES_USER ou passez l'option",
            " --database-url postgresql://user:password@host:port/db",
        )
        sys.exit(1)

    try:
        conn = _connect(candidates)
    except RuntimeError as exc:
        print(exc)
        sys.exit(2)
    try:
        process_csv(
            conn,
            csv_path,
            args.delimiter,
            args.default_tcp,
            args.missing_report,
        )
    finally:
        conn.close()
        print("✅ Import terminé")


if __name__ == "__main__":
    main()
