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
from collections import Counter
from urllib.parse import urlparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Set, Tuple

import psycopg2
from psycopg2 import errors
from dotenv import load_dotenv, dotenv_values
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
    internal_unchanged: int = 0
    internal_missing_product: int = 0
    internal_missing_odoo: int = 0
    missing_references: Dict[str, list[str]] = field(default_factory=dict)
    unresolved_by_name: Dict[str, list[str]] = field(default_factory=dict)
    update_reasons: Dict[str, list[int]] = field(default_factory=dict)
    truncations: Dict[int, List["TruncationInfo"]] = field(default_factory=dict)

    not_imported: Dict[int, "NotImportedInfo"] = field(default_factory=dict)
    missing_reference_tables: List[str] = field(default_factory=list)
    missing_reference_columns: Dict[str, List[str]] = field(default_factory=dict)



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
    "id": "product_id",
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
    "odooid": "odoo_id",
    "insertintointernalproductsodooidproductid": "internal_product_values",
    "insertintoproductsiddescription": "product_values",
}


PRODUCT_COLUMN_MAPPING: list[tuple[str, str]] = [
    ("name", "name"),
    ("description", "description"),
    ("model", "model"),
    ("brand_id", "brand_id"),
    ("memory_id", "memory_id"),
    ("color_id", "color_id"),
    ("type_id", "type_id"),
    ("RAM_id", '"RAM_id"'),
    ("norme_id", "norme_id"),
    ("ean", "ean"),
    ("part_number", "part_number"),
]


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


def _split_table_identifier(table: str) -> tuple[str, str]:
    if "." in table:
        schema, name = table.split(".", 1)
        return schema.strip('"'), name.strip('"')
    return "public", table.strip('"')


def _get_table_columns(cursor, table: str) -> Set[str]:
    schema, name = _split_table_identifier(table)
    cursor.execute(
        """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_schema = %s AND table_name = %s
        """,
        (schema, name),
    )
    return {row["column_name"] for row in cursor.fetchall()}


def _ensure_internal_products_structure(conn: connection) -> bool:
    """Créer la table ``internal_products`` si elle n'existe pas encore."""

    with conn.cursor() as cursor:
        cursor.execute("SELECT to_regclass('public.internal_products')")
        row = cursor.fetchone()
        if row and row[0]:
            try:
                cursor.execute(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_internal_products_odoo_id_unique
                        ON internal_products (odoo_id)
                    """
                )
                cursor.execute(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_internal_products_product_id_unique
                        ON internal_products (product_id)
                    """
                )
                conn.commit()
            except psycopg2.Error:
                conn.rollback()
            return True

        try:
            cursor.execute(
                """
                CREATE TABLE internal_products (
                    id SERIAL PRIMARY KEY,
                    product_id INTEGER NOT NULL REFERENCES products(id),
                    odoo_id VARCHAR(200) NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_internal_products_odoo_id_unique
                    ON internal_products (odoo_id)
                """
            )
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_internal_products_product_id_unique
                    ON internal_products (product_id)
                """
            )
            conn.commit()
            print(
                "🆕 Table internal_products créée automatiquement pour stocker les correspondances produit/Odoo."
            )
            return True
        except psycopg2.Error as exc:  # pragma: no cover - dépend d'un env externe
            conn.rollback()
            print(
                "⚠️  Impossible de créer automatiquement la table internal_products :"
                f" {exc}"
            )
            return False


def _strip_accents_lower(text: str) -> str:
    """Retirer les accents et convertir en minuscules."""

    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def _dedupe_headers(headers: Iterable[str]) -> list[str]:
    seen: Dict[str, int] = {}
    result: list[str] = []
    for header in headers:
        if header is None:
            result.append(header)
            continue
        count = seen.get(header, 0)
        if count:
            result.append(f"{header}__{count + 1}")
        else:
            result.append(header)
        seen[header] = count + 1
    return result


def _build_header_mapping(
    headers: Iterable[str],
    original_headers: Optional[Iterable[str]] = None,
) -> Dict[str, Optional[str]]:
    """Créer un mapping entre les en-têtes du fichier et les clés internes."""

    header_list = list(headers)
    original_list = list(original_headers) if original_headers is not None else header_list

    if len(original_list) != len(header_list):
        raise ValueError("Le nombre d'en-têtes originaux doit correspondre aux en-têtes dédupliqués")

    normalized_counts = Counter(
        _normalize_header(header)
        for header in original_list
        if header is not None
    )

    occurrences: Dict[str, int] = {}
    mapping: Dict[str, Optional[str]] = {}
    for header, original in zip(header_list, original_list):
        if header is None:
            continue
        normalized_original = _normalize_header(original)
        index = occurrences.get(normalized_original, 0)
        occurrences[normalized_original] = index + 1

        if normalized_original == "id" and normalized_counts.get("id", 0) > 1:
            if index == 0:
                mapping[header] = "odoo_id"
            else:
                mapping[header] = "product_id"
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


def _build_db_url_from_parts(values: Optional[Mapping[str, object]] = None) -> Optional[str]:
    """Construire une URL à partir des variables ``POSTGRES_*`` le cas échéant."""

    def get(*keys: str, default: Optional[str] = None) -> Optional[str]:
        for key in keys:
            raw: Optional[object]
            if values is None:
                raw = os.getenv(key)
            else:
                raw = values.get(key) if key in values else None
            if raw is None:
                continue
            if isinstance(raw, str):
                return raw
            return str(raw)
        return default

    database = _clean(get("POSTGRES_DB", "PGDATABASE"))
    user = _clean(get("POSTGRES_USER", "PGUSER"))
    password = get("POSTGRES_PASSWORD", "PGPASSWORD")
    host = _clean(
        get(
            "POSTGRES_HOST",
            "PGHOST",
            "POSTGRES_SERVER",
            "DB_HOST",
            "DATABASE_HOST",
        )
        or "localhost"
    )
    port = _clean(
        get("POSTGRES_PORT", "PGPORT", "DB_PORT", "DATABASE_PORT") or "5432"
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


def _discover_dotenv_files() -> list[Path]:
    """Trouver les fichiers ``.env*`` pertinents à analyser."""

    names = (
        ".env",
        ".env.local",
        ".env.development",
        ".env.example",
    )
    current_dir = Path(__file__).resolve().parent
    directories: list[Path] = []
    directory = current_dir
    while True:
        directories.append(directory)
        if directory == directory.parent:
            break
        directory = directory.parent

    files: list[Path] = []
    seen: Set[Path] = set()
    for base in directories:
        for name in names:
            candidate = base / name
            if candidate in seen or not candidate.exists():
                continue
            seen.add(candidate)
            files.append(candidate)
    return files


def _load_dotenv_candidates() -> list[Mapping[str, object]]:
    """Charger les valeurs de connexion potentielles à partir des fichiers ``.env``."""

    candidates: list[Mapping[str, object]] = []
    for path in _discover_dotenv_files():
        try:
            values = dotenv_values(path)
        except Exception:  # pragma: no cover - dépend de fichiers utilisateur
            continue
        if not values:
            continue
        cleaned: Dict[str, object] = {}
        for key, value in values.items():
            if value is None:
                continue
            cleaned[key] = value
        if cleaned:
            candidates.append(cleaned)
    return candidates


def _expand_host_variants(db_url: str) -> list[str]:
    """Générer des variantes de l'URL avec des hôtes locaux courants."""

    parsed = urlparse(db_url)
    if parsed.scheme not in {"postgresql", "postgres"}:
        return [db_url]

    username = parsed.username or ""
    password = parsed.password
    port = parsed.port
    database = parsed.path.lstrip("/")
    host = parsed.hostname

    if not database:
        return [db_url]

    auth = username
    if auth and password is not None:
        auth = f"{username}:{password}"
    elif not auth:
        auth = None

    def build(hostname: str) -> str:
        netloc = hostname
        if port:
            netloc = f"{hostname}:{port}"
        if auth:
            netloc = f"{auth}@{netloc}"
        return f"{parsed.scheme}://{netloc}/{database}"

    variants = [db_url]
    for candidate_host in ("localhost", "127.0.0.1"):
        if candidate_host == host or host is None:
            continue
        variants.append(build(candidate_host))
    return variants


def _candidate_db_urls(explicit: Optional[str]) -> list[str]:
    candidates: list[str] = []
    seen: Set[str] = set()

    def add(url: Optional[str], *, expand: bool = True) -> None:
        if not url:
            return
        normalized = _normalise_db_url(url.strip())
        if normalized and normalized not in seen:
            seen.add(normalized)
            candidates.append(normalized)

            if expand:
                for variant in _expand_host_variants(normalized):
                    if variant != normalized:
                        add(variant, expand=False)

    add(explicit)
    add(os.getenv("DATABASE_URL"))
    add(_build_db_url_from_parts())

    for mapping in _load_dotenv_candidates():
        add(mapping.get("DATABASE_URL"))
        add(_build_db_url_from_parts(mapping))

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
        self.missing_tables: Set[str] = set()
        self.missing_columns: Dict[str, Set[str]] = {}

    def _column_name(self, column_sql: str) -> str:
        return column_sql.replace('"', "").strip()

    def _safe_execute(
        self,
        query: str,
        params,
        *,
        table: str,
        column: Optional[str] = None,
    ) -> bool:
        try:
            self.cursor.execute(query, params)
            return True
        except errors.UndefinedTable:
            self.missing_tables.add(table)
            self.cursor.connection.rollback()
        except errors.UndefinedColumn:
            if column:
                self.missing_columns.setdefault(table, set()).add(column)
            self.cursor.connection.rollback()
        except psycopg2.Error:
            self.cursor.connection.rollback()
            raise
        return False

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
        if not columns:
            self.missing_tables.add(table)
            self.table_values_cache[key] = []
            return []

        primary_column = self._column_name(column_sql)
        normalized_columns = {col.lower() for col in columns}
        if primary_column.lower() not in normalized_columns:
            self.missing_columns.setdefault(table, set()).add(primary_column)
            self.table_values_cache[key] = []
            return []

        extras = [
            col
            for col in ("name", "nom")
            if col in columns and col != primary_column
        ]
        select_parts = [f"{column_sql} AS primary_value"]
        for extra in extras:
            select_parts.append(f"{extra} AS {extra}")

        if not self._safe_execute(
            f"SELECT id, {', '.join(select_parts)} FROM {table}",
            None,
            table=table,
            column=self._column_name(column_sql),
        ):
            self.table_values_cache[key] = []
            return []

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
        columns = self._get_table_columns(table)
        if not columns:
            self.missing_tables.add(table)
            return None

        normalized_columns = {col.lower() for col in columns}
        primary_column = self._column_name(column_sql)
        if primary_column.lower() not in normalized_columns:
            self.missing_columns.setdefault(table, set()).add(primary_column)
            return None

        candidate_id: Optional[int] = None
        if value is not None:
            key = value.lower()
            table_cache = self.cache.setdefault(table, {})
            if key in table_cache:
                return table_cache[key]

            if not self._safe_execute(
                f"SELECT id FROM {table} WHERE LOWER({column_sql}) = LOWER(%s)",
                (value,),
                table=table,
                column=self._column_name(column_sql),
            ):
                return candidate_id
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

        if not self._safe_execute(
            "SELECT id FROM colors WHERE LOWER(color) = LOWER(%s)",
            (value,),
            table="colors",
            column="color",
        ):
            return None
        row = self.cursor.fetchone()
        if row:
            colors_cache[key] = row["id"]
            return row["id"]

        translations_cache = self.cache.setdefault("color_translations", {})
        if key in translations_cache:
            return translations_cache[key]

        if not self._safe_execute(
            """
            SELECT color_target_id
              FROM color_translations
             WHERE LOWER(color_source) = LOWER(%s)
            """,
            (value,),
            table="color_translations",
            column="color_source",
        ):
            return None
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
    *,
    available_columns: Optional[Set[str]] = None,
) -> Tuple[Optional[int], Optional[str]]:
    """Tenter de retrouver un produit existant et indiquer la logique utilisée."""

    columns = available_columns or set()

    if explicit_id is not None:
        cursor.execute("SELECT id FROM products WHERE id = %s", (explicit_id,))
        row = cursor.fetchone()
        if row:
            return row["id"], "id"

    if ean and (not columns or "ean" in columns):
        cursor.execute("SELECT id FROM products WHERE ean = %s", (ean,))
        row = cursor.fetchone()
        if row:
            return row["id"], "ean"

    search_label = name or model
    description_available = (not columns) or ("description" in columns)
    brand_available = (not columns) or ("brand_id" in columns)
    if search_label and description_available:
        if brand_id and brand_available:
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

    model_available = (not columns) or ("model" in columns)
    if model and not name and model_available:
        if brand_id and brand_available:
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
) -> Tuple[bool, bool, bool]:
    if not odoo_id or not product_id:
        return False, False, False

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
            return False, True, False
        return False, False, True

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
            return False, True, False
        return False, False, True

    cursor.execute(
        "INSERT INTO internal_products (odoo_id, product_id) VALUES (%s, %s)",
        (odoo_id, product_id),
    )
    return True, False, False


def _apply_internal_links(
    conn: connection,
    pending_links: Iterable[Tuple[str, int]],
    stats: ImportStats,
    *,
    enabled: bool,
) -> None:
    """Synchroniser en base toutes les correspondances internal_products en attente."""

    if not enabled:
        return

    links = list(pending_links)
    if not links:
        return

    try:
        with conn.cursor() as cursor:
            for odoo_id, product_id in links:
                inserted, updated, unchanged = _sync_internal_product(
                    cursor, odoo_id, product_id
                )
                if inserted:
                    stats.internal_inserted += 1
                if updated:
                    stats.internal_updated += 1
                if unchanged:
                    stats.internal_unchanged += 1
        conn.commit()
    except Exception:  # pylint: disable=broad-except
        conn.rollback()
        raise


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
        original_headers = reader.fieldnames
        if not original_headers:
            print("❌ ERROR: impossible de lire les en-têtes du fichier CSV")
            sys.exit(1)

        deduped_headers = _dedupe_headers(original_headers)
        if deduped_headers != original_headers:
            reader.fieldnames = deduped_headers

        header_map = _build_header_mapping(reader.fieldnames, original_headers)
        recognized = {raw: mapped for raw, mapped in header_map.items() if mapped}
        if not recognized:
            print("❌ ERROR: aucune colonne reconnue dans le fichier CSV")
            sys.exit(1)

        missing_core = {"name", "model"} - set(recognized.values())
        if missing_core == {"name", "model"}:
            print(
                "⚠️  AVERTISSEMENT: les colonnes Nom ou Modèle sont absentes, les produits risquent d'être ignorés"
            )

        internal_structure_ready = _ensure_internal_products_structure(conn)

        with conn.cursor() as meta_cursor:
            product_columns = _get_table_columns(meta_cursor, "products")
        missing_product_columns = {
            column
            for column, _sql_identifier in PRODUCT_COLUMN_MAPPING
            if column not in product_columns
        }

        with conn.cursor() as meta_cursor:
            internal_columns = _get_table_columns(meta_cursor, "internal_products")

        required_internal_columns = {"id", "odoo_id", "product_id"}
        missing_internal_columns: Set[str] = set()
        internal_table_missing = not internal_columns
        if internal_columns:
            missing_internal_columns = required_internal_columns - internal_columns

        internal_sync_enabled = bool(internal_columns) and not missing_internal_columns
        internal_sync_reason = None
        if internal_table_missing:
            if internal_structure_ready:
                internal_sync_reason = "table introuvable"
            else:
                internal_sync_reason = "table introuvable (création automatique impossible)"
        elif missing_internal_columns:
            missing_list = ", ".join(sorted(missing_internal_columns))
            internal_sync_reason = f"colonnes manquantes ({missing_list})"

        pending_links: list[Tuple[str, int]] = []
        ref_cache: Optional[ReferenceCache] = None

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

                name_value = normalized.get("name")
                description = normalized.get("description") or name_value
                model = normalized.get("model") or name_value

                internal_odoo_id, internal_product_id = _parse_internal_product_values(
                    normalized.get("internal_product_values")
                )
                if not internal_odoo_id:
                    internal_odoo_id = normalized.get("odoo_id")
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
                        name_value
                        or description
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

                if not name_value and tuple_description:
                    name_value = tuple_description
                if not description and tuple_description:
                    description = tuple_description
                if not model and description:
                    model = description
                if not name_value and model:
                    name_value = model

                if not name_value and not model:
                    product_label = (
                        normalized.get("name")
                        or normalized.get("model")
                        or tuple_description
                        or "(inconnu)"
                    )
                    stats.skipped += 1
                    stats.not_imported[index] = NotImportedInfo(
                        label=product_label,
                        reason="Nom et modèle absents après nettoyage",
                    )
                    continue

                description = description or name_value
                model = model or description
                name_value = name_value or description

                name_hint = name_value or model

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
                        "name": name_value,
                        "description": description,
                        "model": model,
                        "ean": ean,
                        "part_number": part_number,
                    }
                )
                name_value = sanitized_strings.get("name") or name_value
                description = (
                    sanitized_strings.get("description")
                    or description
                    or name_value
                )
                model = sanitized_strings.get("model") or model or description
                ean = sanitized_strings.get("ean")
                part_number = sanitized_strings.get("part_number")
                if truncations:
                    stats.truncations[index] = truncations

                product_id, match_reason = _find_product_id(
                    cursor,
                    ean,
                    name_value,
                    model,
                    brand_id,
                    explicit_product_id,
                    available_columns=product_columns,
                )

                final_product_id: Optional[int] = None
                link_product_id: Optional[int] = explicit_product_id

                try:
                    if product_id:
                        product_payload: Dict[str, Optional[object]] = {
                            "name": name_value,
                            "description": description,
                            "model": model,
                            "brand_id": brand_id,
                            "memory_id": memory_id,
                            "color_id": color_id,
                            "type_id": type_id,
                            "RAM_id": ram_id,
                            "norme_id": norme_id,
                            "ean": ean,
                            "part_number": part_number,
                        }

                        update_clauses: list[str] = []
                        update_values: list[Optional[object]] = []
                        for column, sql_identifier in PRODUCT_COLUMN_MAPPING:
                            if column not in product_columns:
                                continue
                            update_clauses.append(f"{sql_identifier} = %s")
                            update_values.append(product_payload[column])

                        if update_clauses:
                            cursor.execute(
                                f"UPDATE products SET {', '.join(update_clauses)} WHERE id = %s",
                                (*update_values, product_id),
                            )
                        stats.updated += 1
                        final_product_id = product_id
                        link_product_id = final_product_id or link_product_id
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
                        product_payload = {
                            "name": name_value,
                            "description": description,
                            "model": model,
                            "brand_id": brand_id,
                            "memory_id": memory_id,
                            "color_id": color_id,
                            "type_id": type_id,
                            "RAM_id": ram_id,
                            "norme_id": norme_id,
                            "ean": ean,
                            "part_number": part_number,
                        }

                        available_pairs = [
                            (column, sql_identifier)
                            for column, sql_identifier in PRODUCT_COLUMN_MAPPING
                            if column in product_columns
                        ]

                        columns = [sql_identifier for _column, sql_identifier in available_pairs]
                        values = [product_payload[column] for column, _sql_identifier in available_pairs]
                        if explicit_product_id is not None:
                            columns.insert(0, "id")
                            values.insert(0, explicit_product_id)
                        if not columns:
                            raise RuntimeError(
                                "Aucune colonne disponible pour insérer le produit dans la table cible"
                            )
                        placeholders = ", ".join(["%s"] * len(columns))
                        cursor.execute(
                            f"INSERT INTO products ({', '.join(columns)}) "
                            f"VALUES ({placeholders}) RETURNING id",
                            values,
                        )
                        row = cursor.fetchone()
                        final_product_id = row["id"] if row else None
                        if final_product_id is not None:
                            link_product_id = final_product_id
                        stats.inserted += 1

                    if internal_sync_enabled:
                        if internal_odoo_id and link_product_id is not None:
                            pending_links.append(
                                (internal_odoo_id, int(link_product_id))
                            )
                        elif internal_odoo_id and link_product_id is None:
                            stats.internal_missing_product += 1
                        elif not internal_odoo_id and link_product_id is not None:
                            stats.internal_missing_odoo += 1
                    conn.commit()
                except Exception as exc:  # pylint: disable=broad-except
                    conn.rollback()
                    stats.errors += 1
                    errors.append(f"Ligne {index}: {exc}")
                    product_label = name_value or description or model or "(inconnu)"
                    stats.not_imported[index] = NotImportedInfo(
                        label=product_label,
                        reason=f"Erreur lors de l'écriture en base: {exc}",
                    )
                    continue

    try:
        _apply_internal_links(conn, pending_links, stats, enabled=internal_sync_enabled)
    except Exception as exc:  # pylint: disable=broad-except
        message = f"Erreur lors de la synchronisation internal_products: {exc}"
        conn.rollback()
        stats.errors += 1
        errors.append(message)
        print(f"\n⚠️  {message}")

    if ref_cache is not None:
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
        stats.missing_reference_tables = sorted(ref_cache.missing_tables)
        stats.missing_reference_columns = {
            table: sorted(columns)
            for table, columns in ref_cache.missing_columns.items()
            if columns
        }
    else:
        stats.missing_references = {}
        stats.unresolved_by_name = {}
        stats.missing_reference_tables = []
        stats.missing_reference_columns = {}

    if missing_product_columns:
        existing = set(stats.missing_reference_columns.get("products", []))
        existing.update(missing_product_columns)
        stats.missing_reference_columns["products"] = sorted(existing)

    if internal_table_missing:
        tables = set(stats.missing_reference_tables)
        tables.add("internal_products")
        stats.missing_reference_tables = sorted(tables)
    elif missing_internal_columns:
        existing = set(stats.missing_reference_columns.get("internal_products", []))
        existing.update(missing_internal_columns)
        stats.missing_reference_columns["internal_products"] = sorted(existing)

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
    print(f"   🧩 Liens internal_products insérés : {stats.internal_inserted}")
    print(f"   🛠️  Liens internal_products mis à jour : {stats.internal_updated}")
    if stats.internal_unchanged:
        print(
            f"   💤 Liens internal_products déjà présents : {stats.internal_unchanged}"
        )
    print(f"   ⏭️  Produits ignorés : {stats.skipped}")
    print(f"   ⚠️  Lignes en erreur : {stats.errors}")

    if stats.internal_missing_product or stats.internal_missing_odoo:
        print("\n⚠️  Liens internal_products non créés faute de données complètes :")
        if stats.internal_missing_product:
            print(
                "   - Odoo_id connu mais aucun identifiant produit final"
                f" (occurrences: {stats.internal_missing_product})"
            )
        if stats.internal_missing_odoo:
            print(
                "   - Identifiant produit trouvé mais colonne Odoo vide"
                f" (occurrences: {stats.internal_missing_odoo})"
            )

    if stats.missing_reference_tables:
        print("\n⚠️  Tables de référence introuvables :")
        for table in stats.missing_reference_tables:
            print(f"   - {table}")

    if stats.missing_reference_columns:
        print("\n⚠️  Colonnes de référence introuvables :")
        for table, columns in stats.missing_reference_columns.items():
            joined = ", ".join(columns)
            print(f"   - {table}: {joined}")

    if internal_sync_reason:
        print(
            "\n⚠️  Synchronisation des liens internal_products ignorée ("
            f"{internal_sync_reason})."
        )

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

    if stats.missing_reference_tables:
        payload["missing_reference_tables"] = stats.missing_reference_tables
    if stats.missing_reference_columns:
        payload["missing_reference_columns"] = stats.missing_reference_columns

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
