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
    python3 scripts/reset_odoo_links.py           # mode interactif
    python3 scripts/reset_odoo_links.py --dry-run  # simulation sans commit

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

    cur.execute("SELECT COUNT(*) FROM internal_products")
    links = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM odoo_sync_jobs")
    jobs = cur.fetchone()[0]

    print("=" * 60)
    print("RESET ODOO — MODE MINIMAL (liens + jobs)")
    print("=" * 60)
    print(f"  internal_products  : {links} enregistrement(s)")
    print(f"  odoo_sync_jobs     : {jobs} enregistrement(s)")
    print()

    if dry_run:
        print("[DRY-RUN] Aucune modification appliquée.")
        cur.close()
        conn.close()
        return

    if links == 0 and jobs == 0:
        print("Rien à supprimer.")
        cur.close()
        conn.close()
        return

    confirm = input("Confirmer la suppression ? [oui/N] ").strip().lower()
    if confirm != "oui":
        print("Annulé.")
        cur.close()
        conn.close()
        sys.exit(0)

    cur.execute("DELETE FROM internal_products")
    cur.execute("DELETE FROM odoo_sync_jobs")
    conn.commit()
    cur.close()
    conn.close()

    print(f"✓ {links} lien(s) Odoo supprimé(s)")
    print(f"✓ {jobs} job(s) de synchronisation supprimé(s)")
    print()
    print("Vous pouvez maintenant lancer une nouvelle synchronisation Odoo.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Simulation sans commit")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
