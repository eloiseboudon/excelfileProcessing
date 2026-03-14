"""Weekly conditional fine-tuning of the bi-encoder.

Checks if enough new validation pairs have accumulated since the last
fine-tuning. Only trains if the delta exceeds the threshold (default: 100).

Designed to be called via cron on the VPS:
    0 4 * * 0  cd ~/ajtpro && docker exec ajt_backend_prod python scripts/weekly_fine_tuning.py >> /var/log/ajtpro-finetune.log 2>&1

The script kills Gunicorn to free RAM, runs training, then exits.
Docker restart policy will restart the container automatically.
"""

from __future__ import annotations

import os
import signal
import sys

NEW_PAIRS_THRESHOLD = 100

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DATABASE_URL", "")
os.environ.setdefault("JWT_SECRET", "finetune-key-not-used-for-auth-32bytes!")

from app import app

with app.app_context():
    from models import db
    from utils.matching.fine_tuner import export_training_pairs, run_fine_tuning

    # Count current pairs
    pairs = export_training_pairs(db.session)
    total = len(pairs)
    positives = sum(1 for _, _, m in pairs if m)
    negatives = sum(1 for _, _, m in pairs if not m)

    print(f"[fine-tuning] Paires disponibles: {total} ({positives} pos, {negatives} neg)")

    if total < 100:
        print(f"[fine-tuning] Pas assez de paires (minimum 100). Abandon.")
        sys.exit(0)

    # Check last training count from marker file
    marker_path = "/app/data/models/last_finetune_pairs.txt"
    last_count = 0
    if os.path.exists(marker_path):
        try:
            with open(marker_path) as f:
                last_count = int(f.read().strip())
        except (ValueError, OSError):
            pass

    delta = total - last_count
    print(f"[fine-tuning] Derniere session: {last_count} paires. Delta: +{delta}")

    if delta < NEW_PAIRS_THRESHOLD:
        print(f"[fine-tuning] Delta insuffisant (seuil: {NEW_PAIRS_THRESHOLD}). Abandon.")
        sys.exit(0)

    print(f"[fine-tuning] Lancement du fine-tuning ({total} paires, batch_size=4)...")

    # Kill Gunicorn master to free RAM (PID 1 in Docker)
    try:
        os.kill(1, signal.SIGTERM)
        print("[fine-tuning] Gunicorn arrete pour liberer la RAM.")
    except ProcessLookupError:
        pass

    path = run_fine_tuning(pairs, batch_size=4)
    print(f"[fine-tuning] Modele sauvegarde: {path}")

    # Save marker for next run
    os.makedirs(os.path.dirname(marker_path), exist_ok=True)
    with open(marker_path, "w") as f:
        f.write(str(total))

    print(f"[fine-tuning] Marqueur mis a jour: {total} paires.")
    print("[fine-tuning] Le container va redemarrer automatiquement (restart policy).")
