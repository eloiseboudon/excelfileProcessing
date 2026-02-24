#!/usr/bin/env python3
"""
fix_region_null_matches.py — One-time data fix for region null = EU rule.

Finds and resets LabelCache auto-matched entries where the region would now
mismatch under the new "null = EU" rule:
  - EU/null label matched to a non-EU product
  - Non-EU label matched to a EU/null product

Deletes associated SupplierProductRef entries so the next matching run
can re-evaluate these products with the correct scoring.

Usage (on VPS, in project root):
    docker exec -it ajtpro-backend python backend/scripts/fix_region_null_matches.py

Or locally:
    cd backend && python scripts/fix_region_null_matches.py
"""

import os
import sys

# Allow running from project root or backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("FLASK_ENV", "production")

import psycopg2


DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("ERROR: DATABASE_URL environment variable is not set.")


def main():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    print("=== Region NULL fix ===")
    print("Rule: null region = EU. Finding auto-matched entries where regions mismatch.\n")

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
        print("No bad auto-matches found. Nothing to fix.")
        conn.close()
        return

    print(f"Found {len(bad_matches)} bad auto-matched LabelCache entries:\n")
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
        print(f"Associated SupplierProductRef entries to delete: {len(refs)}")
        for r in refs:
            print(f"  ref_id={r[0]} | supplier_id={r[1]} | product_id={r[2]}")
        print()

    # Dry run check
    answer = input("Apply fix? (yes/no): ").strip().lower()
    if answer != "yes":
        print("Aborted. No changes made.")
        conn.close()
        return

    # Delete SupplierProductRef for affected products
    if product_ids:
        cur.execute("""
            DELETE FROM supplier_product_refs
            WHERE product_id = ANY(%s)
        """, (product_ids,))
        deleted_refs = cur.rowcount
        print(f"Deleted {deleted_refs} SupplierProductRef entries.")

    # Reset LabelCache entries (unlink product, reset to extraction state)
    cur.execute("""
        UPDATE label_cache
        SET product_id = NULL,
            match_source = 'extracted',
            match_score = NULL
        WHERE id = ANY(%s)
    """, (cache_ids,))
    reset_cache = cur.rowcount
    print(f"Reset {reset_cache} LabelCache entries (product_id → NULL, match_source → 'extracted').")

    conn.commit()
    print("\nDone. Run a new matching job to re-evaluate these products with the correct region scoring.")
    conn.close()


if __name__ == "__main__":
    main()
