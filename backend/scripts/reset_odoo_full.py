"""
Reset COMPLET des données Odoo.

Supprime, dans l'ordre des dépendances FK :
  1. pending_matches          (tous)
  2. label_cache              (entrées liées aux produits Odoo)
  3. product_calculations     (calculs TCP/marge liés aux produits Odoo)
  4. supplier_product_refs    (product_id mis à NULL — les entrées catalog restent)
  5. internal_products        (les liens Odoo ID → Product)
  6. products                 (uniquement ceux ayant eu un lien Odoo)
  7. odoo_sync_jobs           (historique des synchronisations)

Ce qui est CONSERVÉ :
  - supplier_catalog          (catalogue fournisseurs)
  - supplier_product_refs     (entrées sans product_id, pour re-matching futur)
  - brands / colors / memory_options / device_types / norme_options
  - odoo_configs              (configuration de connexion Odoo)

Cas d'usage : la base Odoo a changé de structure ou de contenu, le
catalogue produit doit être entièrement reconstruit depuis la nouvelle base.

Usage :
    cd backend
    python3 scripts/reset_odoo_full.py           # mode interactif
    python3 scripts/reset_odoo_full.py --dry-run  # simulation sans commit

Dépendance unique : psycopg2-binary
    pip3 install psycopg2-binary
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# Chargement du .env (racine du projet, deux niveaux au-dessus de scripts/)
# ---------------------------------------------------------------------------
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
    print("ERROR: psycopg2 non disponible.", file=sys.stderr)
    print("       pip3 install psycopg2-binary", file=sys.stderr)
    sys.exit(1)

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL non défini. Vérifier le fichier .env à la racine du projet.", file=sys.stderr)
    sys.exit(1)


def _connect():
    parsed = urlparse(DATABASE_URL)
    return psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        dbname=parsed.path.lstrip("/"),
        user=parsed.username,
        password=parsed.password,
    )


def run(dry_run: bool) -> None:
    conn = _connect()
    conn.autocommit = False
    cur = conn.cursor()

    # Collecte des product_id liés à Odoo
    cur.execute("SELECT product_id FROM internal_products WHERE product_id IS NOT NULL")
    odoo_product_ids = [r[0] for r in cur.fetchall()]

    # Si internal_products est vide (reset partiel précédent), récupérer tous les produits restants
    if not odoo_product_ids:
        cur.execute("SELECT id FROM products")
        odoo_product_ids = [r[0] for r in cur.fetchall()]

    # Comptage de l'impact
    p_count = len(odoo_product_ids)
    cur.execute("SELECT COUNT(*) FROM internal_products")
    ip_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM pending_matches")
    pm_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM odoo_sync_jobs")
    job_count = cur.fetchone()[0]

    lc_count = pc_count = spr_count = 0
    if odoo_product_ids:
        cur.execute("SELECT COUNT(*) FROM label_cache WHERE product_id = ANY(%s)", (odoo_product_ids,))
        lc_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM product_calculations WHERE product_id = ANY(%s)", (odoo_product_ids,))
        pc_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM supplier_product_refs WHERE product_id = ANY(%s)", (odoo_product_ids,))
        spr_count = cur.fetchone()[0]

    print("=" * 60)
    print("RESET ODOO — MODE COMPLET")
    print("=" * 60)
    print(f"  Produits Odoo identifiés       : {p_count}")
    print()
    print("  Données à supprimer :")
    print(f"    pending_matches              : {pm_count} (tous)")
    print(f"    label_cache                  : {lc_count} (liés aux produits Odoo)")
    print(f"    product_calculations         : {pc_count}")
    print(f"    supplier_product_refs        : {spr_count} product_id → NULL")
    print(f"    internal_products            : {ip_count}")
    print(f"    products                     : {p_count}")
    print(f"    odoo_sync_jobs               : {job_count}")
    print()

    if dry_run:
        print("[DRY-RUN] Aucune modification appliquée.")
        cur.close()
        conn.close()
        return

    if p_count == 0 and job_count == 0:
        print("Rien à supprimer.")
        cur.close()
        conn.close()
        return

    print("⚠️  Cette opération est IRRÉVERSIBLE.")
    confirm = input("Taper 'RESET' pour confirmer : ").strip()
    if confirm != "RESET":
        print("Annulé.")
        cur.close()
        conn.close()
        sys.exit(0)

    # 1. Suppression de tous les pending_matches
    cur.execute("DELETE FROM pending_matches")
    print(f"  ✓ {cur.rowcount} pending_matches supprimés")

    # 2. Suppression du cache LLM lié aux produits Odoo
    if odoo_product_ids:
        cur.execute("DELETE FROM label_cache WHERE product_id = ANY(%s)", (odoo_product_ids,))
        print(f"  ✓ {cur.rowcount} label_cache supprimés")

    # 3. Suppression des calculs TCP/marge
    if odoo_product_ids:
        cur.execute("DELETE FROM product_calculations WHERE product_id = ANY(%s)", (odoo_product_ids,))
        print(f"  ✓ {cur.rowcount} product_calculations supprimés")

    # 4. Détachement des supplier_product_refs (product_id → NULL)
    if odoo_product_ids:
        cur.execute(
            "UPDATE supplier_product_refs SET product_id = NULL WHERE product_id = ANY(%s)",
            (odoo_product_ids,),
        )
        print(f"  ✓ {cur.rowcount} supplier_product_refs détachés (product_id = NULL)")

    # 5. Suppression des liens Odoo
    cur.execute("DELETE FROM internal_products")
    print(f"  ✓ {cur.rowcount} internal_products supprimés")

    # 6. Suppression des produits Odoo
    if odoo_product_ids:
        cur.execute("DELETE FROM products WHERE id = ANY(%s)", (odoo_product_ids,))
        print(f"  ✓ {cur.rowcount} products supprimés")

    # 7. Suppression de l'historique des syncs
    cur.execute("DELETE FROM odoo_sync_jobs")
    print(f"  ✓ {cur.rowcount} odoo_sync_jobs supprimés")

    conn.commit()
    cur.close()
    conn.close()

    print()
    print("✓ Reset complet terminé.")
    print()
    print("Étapes suivantes :")
    print("  1. Vérifier la configuration Odoo (URL, base, identifiants)")
    print("  2. Lancer une synchronisation Odoo depuis l'interface")
    print("  3. Relancer le matching LLM sur les articles fournisseurs")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Simulation sans commit")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
