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
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


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
    from sqlalchemy import create_engine, text
except ImportError:
    print("ERROR: sqlalchemy non disponible.", file=sys.stderr)
    print("       pip3 install sqlalchemy psycopg2-binary", file=sys.stderr)
    sys.exit(1)

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL non défini. Vérifier le fichier .env à la racine du projet.", file=sys.stderr)
    sys.exit(1)


def run(dry_run: bool) -> None:
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Collecte des product_id liés à Odoo
        rows = conn.execute(
            text("SELECT product_id FROM internal_products WHERE product_id IS NOT NULL")
        ).fetchall()
        odoo_product_ids = [r[0] for r in rows]

        # Comptage de l'impact
        p_count = len(odoo_product_ids)
        ip_count = conn.execute(text("SELECT COUNT(*) FROM internal_products")).scalar()
        pm_count = conn.execute(text("SELECT COUNT(*) FROM pending_matches")).scalar()
        job_count = conn.execute(text("SELECT COUNT(*) FROM odoo_sync_jobs")).scalar()

        lc_count = pc_count = spr_count = 0
        if odoo_product_ids:
            ids_tuple = tuple(odoo_product_ids)
            lc_count = conn.execute(
                text("SELECT COUNT(*) FROM label_cache WHERE product_id = ANY(:ids)"),
                {"ids": list(ids_tuple)},
            ).scalar()
            pc_count = conn.execute(
                text("SELECT COUNT(*) FROM product_calculations WHERE product_id = ANY(:ids)"),
                {"ids": list(ids_tuple)},
            ).scalar()
            spr_count = conn.execute(
                text("SELECT COUNT(*) FROM supplier_product_refs WHERE product_id = ANY(:ids)"),
                {"ids": list(ids_tuple)},
            ).scalar()

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
            return

        if p_count == 0 and job_count == 0:
            print("Rien à supprimer.")
            return

        print("⚠️  Cette opération est IRRÉVERSIBLE.")
        confirm = input("Taper 'RESET' pour confirmer : ").strip()
        if confirm != "RESET":
            print("Annulé.")
            sys.exit(0)

        # 1. Suppression de tous les pending_matches
        r = conn.execute(text("DELETE FROM pending_matches"))
        print(f"  ✓ {r.rowcount} pending_matches supprimés")

        # 2. Suppression du cache LLM lié aux produits Odoo
        if odoo_product_ids:
            r = conn.execute(
                text("DELETE FROM label_cache WHERE product_id = ANY(:ids)"),
                {"ids": odoo_product_ids},
            )
            print(f"  ✓ {r.rowcount} label_cache supprimés")

        # 3. Suppression des calculs TCP/marge
        if odoo_product_ids:
            r = conn.execute(
                text("DELETE FROM product_calculations WHERE product_id = ANY(:ids)"),
                {"ids": odoo_product_ids},
            )
            print(f"  ✓ {r.rowcount} product_calculations supprimés")

        # 4. Détachement des supplier_product_refs (product_id → NULL)
        if odoo_product_ids:
            r = conn.execute(
                text("UPDATE supplier_product_refs SET product_id = NULL WHERE product_id = ANY(:ids)"),
                {"ids": odoo_product_ids},
            )
            print(f"  ✓ {r.rowcount} supplier_product_refs détachés (product_id = NULL)")

        # 5. Suppression des liens Odoo
        r = conn.execute(text("DELETE FROM internal_products"))
        print(f"  ✓ {r.rowcount} internal_products supprimés")

        # 6. Suppression des produits Odoo
        if odoo_product_ids:
            r = conn.execute(
                text("DELETE FROM products WHERE id = ANY(:ids)"),
                {"ids": odoo_product_ids},
            )
            print(f"  ✓ {r.rowcount} products supprimés")

        # 7. Suppression de l'historique des syncs
        r = conn.execute(text("DELETE FROM odoo_sync_jobs"))
        print(f"  ✓ {r.rowcount} odoo_sync_jobs supprimés")

        conn.commit()

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
