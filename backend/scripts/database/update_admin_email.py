#!/usr/bin/env python3
"""
update_admin_email.py — Modifie l'email du compte admin.

Usage:
    docker exec -it ajt_backend_prod python scripts/database/update_admin_email.py --email nouveau@email.com
    docker exec -it ajt_backend_prod python scripts/database/update_admin_email.py --email nouveau@email.com --username admin
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


_load_dotenv(Path(__file__).resolve().parents[3] / ".env")

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 non disponible.", file=sys.stderr)
    sys.exit(1)

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("ERROR: DATABASE_URL environment variable is not set.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True, help="Nouvel email")
    parser.add_argument("--username", default="admin", help="Username cible (défaut: admin)")
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("SELECT id, username, email FROM users WHERE username = %s", (args.username,))
    user = cur.fetchone()

    if not user:
        print(f"ERROR: aucun utilisateur avec username='{args.username}' trouvé.")
        conn.close()
        sys.exit(1)

    print(f"Utilisateur trouvé : id={user[0]}, username={user[1]}, email actuel={user[2]}")
    print(f"Nouveau email      : {args.email}")

    answer = input("Confirmer ? (yes/no) : ").strip().lower()
    if answer != "yes":
        print("Annulé.")
        conn.close()
        return

    cur.execute("UPDATE users SET email = %s WHERE username = %s", (args.email, args.username))
    conn.commit()
    print(f"Email mis à jour : {args.username} → {args.email}")
    conn.close()


if __name__ == "__main__":
    main()
