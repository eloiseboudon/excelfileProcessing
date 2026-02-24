#!/usr/bin/env python3
"""
repromote_region_pending.py — Remet les pending matches dans le pipe de rapprochement.

Supprime tous les PendingMatch avec status='pending' dont la région label est EU/null
afin qu'ils soient re-scorés lors du prochain job de rapprochement.

Avec la nouvelle règle (null = EU, +5 pts), les matchs qui étaient à 85-89 pts
franchiront le seuil d'auto-match (90) et seront validés automatiquement.
Le LLM ne sera PAS rappelé : les labels sont déjà en cache.

Usage:
    cd ~/ajtpro/backend && python3 scripts/repromote_region_pending.py
    cd ~/ajtpro/backend && python3 scripts/repromote_region_pending.py --dry-run

Dépendance unique : psycopg2-binary
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


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

    print("=== Repromote pending matches (région null = EU) ===")
    if dry_run:
        print("Mode DRY-RUN — aucune modification ne sera appliquée.\n")
    else:
        print()

    # Count pending matches with EU/null region
    cur.execute("""
        SELECT COUNT(*)
        FROM pending_matches
        WHERE status = 'pending'
    """)
    total_pending = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM pending_matches
        WHERE status = 'pending'
          AND COALESCE(UPPER(extracted_attributes->>'region'), 'EU') = 'EU'
    """)
    eu_pending = cur.fetchone()[0]

    print(f"Total pending matches : {total_pending}")
    print(f"  dont région EU/null  : {eu_pending}  ← à supprimer pour re-scoring")
    print(f"  dont région non-EU   : {total_pending - eu_pending}  (conservés)\n")

    if eu_pending == 0:
        print("Rien à faire.")
        conn.close()
        return

    if dry_run:
        print("DRY-RUN : ces entrées seraient supprimées.")
        print("Ensuite : lance un rapprochement depuis l'UI (sans appel LLM — labels déjà en cache).")
        conn.close()
        return

    answer = input(f"Supprimer {eu_pending} pending matches pour les re-scorer ? (yes/no) : ").strip().lower()
    if answer != "yes":
        print("Annulé.")
        conn.close()
        return

    cur.execute("""
        DELETE FROM pending_matches
        WHERE status = 'pending'
          AND COALESCE(UPPER(extracted_attributes->>'region'), 'EU') = 'EU'
    """)
    deleted = cur.rowcount
    conn.commit()

    print(f"\nSupprimé {deleted} pending matches.")
    print("→ Lance maintenant un rapprochement depuis l'UI.")
    print("  Le job re-scorera ces produits avec +5 pts région.")
    print("  Ceux à 85-89 pts passeront en auto-match (seuil 90). Pas d'appel LLM.")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Simulation sans modification")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
