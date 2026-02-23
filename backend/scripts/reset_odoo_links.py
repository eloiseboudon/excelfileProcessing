"""
Reset minimal des données Odoo.

Supprime UNIQUEMENT :
  - internal_products  (les liens Odoo ID → Product)
  - odoo_sync_jobs     (l'historique des synchronisations)

Les produits, prix, marges, données fournisseurs et historique de matching
LLM sont conservés intégralement.

Cas d'usage : changement d'URL / de base Odoo, avec un catalogue produit
identique. La prochaine sync recréera les liens en matchant sur EAN /
part_number.

Usage :
    cd backend
    python scripts/reset_odoo_links.py           # mode interactif
    python scripts/reset_odoo_links.py --dry-run  # simulation sans commit
"""
from __future__ import annotations

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import InternalProduct, OdooSyncJob, db


def run(dry_run: bool) -> None:
    app = create_app()
    with app.app_context():
        links = InternalProduct.query.count()
        jobs = OdooSyncJob.query.count()

        print("=" * 60)
        print("RESET ODOO — MODE MINIMAL (liens + jobs)")
        print("=" * 60)
        print(f"  internal_products  : {links} enregistrement(s)")
        print(f"  odoo_sync_jobs     : {jobs} enregistrement(s)")
        print()

        if dry_run:
            print("[DRY-RUN] Aucune modification appliquée.")
            return

        if links == 0 and jobs == 0:
            print("Rien à supprimer.")
            return

        confirm = input("Confirmer la suppression ? [oui/N] ").strip().lower()
        if confirm != "oui":
            print("Annulé.")
            sys.exit(0)

        InternalProduct.query.delete(synchronize_session=False)
        OdooSyncJob.query.delete(synchronize_session=False)
        db.session.commit()

        print()
        print(f"✓ {links} lien(s) Odoo supprimé(s)")
        print(f"✓ {jobs} job(s) de synchronisation supprimé(s)")
        print()
        print("Vous pouvez maintenant lancer une nouvelle synchronisation Odoo.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Simulation sans commit")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
