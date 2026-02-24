#!/usr/bin/env python3
"""
fix_region_null_matches.py — One-time data fix for region null = EU rule.

Finds and resets LabelCache auto-matched entries where the region would now
mismatch under the new "null = EU" rule:
  - EU/null label matched to a non-EU product
  - Non-EU label matched to a EU/null product

Deletes associated SupplierProductRef entries so the next matching run
can re-evaluate these products with the correct scoring.

Usage:
    cd ~/ajtpro/backend && python3 scripts/fix_region_null_matches.py
    cd ~/ajtpro/backend && python3 scripts/fix_region_null_matches.py --dry-run

Dépendance unique : psycopg2-binary
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


# Load .env from project root (two levels above scripts/)
def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_dotenv(Path(__file__).resolve().parents[2] / ".env")

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 non disponible. Installe avec : pip3 install psycopg2-binary", file=sys.stderr)
    sys.exit(1)

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("ERROR: DATABASE_URL environment variable is not set.")


def main(dry_run: bool = False) -> None:
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    print("=== Region NULL fix ===")
    if dry_run:
        print("Mode DRY-RUN — aucune modification ne sera appliquée.\n")
    print("Règle : région null = EU. Recherche des auto-matchs incorrects.\n")

    # Find LabelCache entries where auto-match would now be a region mismatch
    cur.execute("""
        SELECT
            lc.id AS cache_id,
            lc.supplier_id,
            lc.normalized_label,
            lc.product_id,
            COALESCE(UPPER(lc.extracted_attributes->>'region'), 'EU') AS label_region,
            COALESCE(UPPER(p.region), 'EU') AS product_region
        FROM label_cache lc
        JOIN products p ON p.id = lc.product_id
        WHERE lc.product_id IS NOT NULL
          AND lc.match_source = 'auto'
          AND COALESCE(UPPER(lc.extracted_attributes->>'region'), 'EU')
              != COALESCE(UPPER(p.region), 'EU')
        ORDER BY lc.id
    """)
    bad_matches = cur.fetchall()

    if not bad_matches:
        print("Aucun auto-match incorrect trouvé. Rien à corriger.")
        conn.close()
        return

    print(f"Trouvé {len(bad_matches)} entrées LabelCache avec région incorrecte :\n")
    cache_ids = []
    product_ids = []
    for row in bad_matches:
        cache_id, supplier_id, label, product_id, label_region, product_region = row
        print(f"  cache_id={cache_id} | supplier={supplier_id} | label={label!r}")
        print(f"    label_region={label_region} ≠ product_region={product_region} (product_id={product_id})")
        cache_ids.append(cache_id)
        product_ids.append(product_id)

    print()

    # Find associated SupplierProductRef entries
    if product_ids:
        cur.execute("""
            SELECT id, supplier_id, product_id
            FROM supplier_product_refs
            WHERE product_id = ANY(%s)
        """, (product_ids,))
        refs = cur.fetchall()
        print(f"SupplierProductRef associés à supprimer : {len(refs)}")
        for r in refs:
            print(f"  ref_id={r[0]} | supplier_id={r[1]} | product_id={r[2]}")
        print()

    if dry_run:
        print("DRY-RUN terminé. Aucune modification appliquée.")
        conn.close()
        return

    answer = input("Appliquer le fix ? (yes/no) : ").strip().lower()
    if answer != "yes":
        print("Annulé. Aucune modification.")
        conn.close()
        return

    # Delete SupplierProductRef for affected products
    if product_ids:
        cur.execute("""
            DELETE FROM supplier_product_refs
            WHERE product_id = ANY(%s)
        """, (product_ids,))
        deleted_refs = cur.rowcount
        print(f"Supprimé {deleted_refs} entrées SupplierProductRef.")

    # Reset LabelCache entries
    cur.execute("""
        UPDATE label_cache
        SET product_id = NULL,
            match_source = 'extracted',
            match_score = NULL
        WHERE id = ANY(%s)
    """, (cache_ids,))
    reset_cache = cur.rowcount
    print(f"Réinitialisé {reset_cache} entrées LabelCache (product_id → NULL, match_source → 'extracted').")

    conn.commit()
    print("\nTerminé. Lance un nouveau rapprochement pour re-évaluer ces produits avec le bon scoring région.")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Simulation sans modification")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
