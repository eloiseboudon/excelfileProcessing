"""
Reset COMPLET des données Odoo.

Supprime, dans l'ordre des dépendances FK :
  1. pending_matches          (tous — les produits référencés sont supprimés)
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
    python scripts/reset_odoo_full.py           # mode interactif
    python scripts/reset_odoo_full.py --dry-run  # simulation sans commit
"""
from __future__ import annotations

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import (
    InternalProduct,
    LabelCache,
    OdooSyncJob,
    PendingMatch,
    Product,
    ProductCalculation,
    SupplierProductRef,
    db,
)


def run(dry_run: bool) -> None:
    app = create_app()
    with app.app_context():
        # Collecte des product_id liés à Odoo
        odoo_links = InternalProduct.query.all()
        odoo_product_ids = [lnk.product_id for lnk in odoo_links if lnk.product_id]
        odoo_product_ids_set = set(odoo_product_ids)

        # Comptage de l'impact
        pm_count = PendingMatch.query.count()
        lc_count = (
            LabelCache.query.filter(LabelCache.product_id.in_(odoo_product_ids_set)).count()
            if odoo_product_ids_set else 0
        )
        pc_count = (
            ProductCalculation.query.filter(
                ProductCalculation.product_id.in_(odoo_product_ids_set)
            ).count()
            if odoo_product_ids_set else 0
        )
        spr_count = (
            SupplierProductRef.query.filter(
                SupplierProductRef.product_id.in_(odoo_product_ids_set)
            ).count()
            if odoo_product_ids_set else 0
        )
        ip_count = len(odoo_links)
        p_count = len(odoo_product_ids)
        job_count = OdooSyncJob.query.count()

        print("=" * 60)
        print("RESET ODOO — MODE COMPLET")
        print("=" * 60)
        print(f"  Produits Odoo identifiés    : {p_count}")
        print()
        print("  Données à supprimer :")
        print(f"    pending_matches            : {pm_count} (tous)")
        print(f"    label_cache                : {lc_count} (liés aux produits Odoo)")
        print(f"    product_calculations       : {pc_count}")
        print(f"    supplier_product_refs      : {spr_count} product_id → NULL")
        print(f"    internal_products          : {ip_count}")
        print(f"    products                   : {p_count}")
        print(f"    odoo_sync_jobs             : {job_count}")
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
        deleted_pm = PendingMatch.query.delete(synchronize_session=False)
        print(f"  ✓ {deleted_pm} pending_matches supprimés")

        # 2. Suppression du cache LLM lié aux produits Odoo
        if odoo_product_ids_set:
            deleted_lc = LabelCache.query.filter(
                LabelCache.product_id.in_(odoo_product_ids_set)
            ).delete(synchronize_session=False)
            print(f"  ✓ {deleted_lc} label_cache supprimés")

        # 3. Suppression des calculs TCP/marge
        if odoo_product_ids_set:
            deleted_pc = ProductCalculation.query.filter(
                ProductCalculation.product_id.in_(odoo_product_ids_set)
            ).delete(synchronize_session=False)
            print(f"  ✓ {deleted_pc} product_calculations supprimés")

        # 4. Détachement des supplier_product_refs (product_id → NULL)
        if odoo_product_ids_set:
            updated_spr = SupplierProductRef.query.filter(
                SupplierProductRef.product_id.in_(odoo_product_ids_set)
            ).update({"product_id": None}, synchronize_session=False)
            print(f"  ✓ {updated_spr} supplier_product_refs détachés (product_id = NULL)")

        # 5. Suppression des liens Odoo
        deleted_ip = InternalProduct.query.delete(synchronize_session=False)
        print(f"  ✓ {deleted_ip} internal_products supprimés")

        # 6. Suppression des produits Odoo
        if odoo_product_ids_set:
            deleted_p = Product.query.filter(
                Product.id.in_(odoo_product_ids_set)
            ).delete(synchronize_session=False)
            print(f"  ✓ {deleted_p} products supprimés")

        # 7. Suppression de l'historique des syncs
        deleted_jobs = OdooSyncJob.query.delete(synchronize_session=False)
        print(f"  ✓ {deleted_jobs} odoo_sync_jobs supprimés")

        db.session.commit()

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
