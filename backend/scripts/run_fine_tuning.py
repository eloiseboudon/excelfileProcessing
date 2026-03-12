"""Fine-tune the bi-encoder on validation history.

Stops Gunicorn workers to free RAM, runs fine-tuning, then the container
restarts automatically via Docker's restart policy.

Usage (on VPS):
    docker exec ajt_backend_prod python scripts/run_fine_tuning.py

Or to free max RAM (kills Gunicorn workers first):
    docker exec ajt_backend_prod bash -c "pkill -f gunicorn; python scripts/run_fine_tuning.py"
    docker compose -f docker-compose.prod.yml restart backend
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DATABASE_URL", "")
os.environ.setdefault("JWT_SECRET", "finetune-key-not-used-for-auth-32bytes!")

from app import app

with app.app_context():
    from models import db
    from utils.matching.fine_tuner import export_training_pairs, run_fine_tuning

    pairs = export_training_pairs(db.session)
    positives = sum(1 for _, _, m in pairs if m)
    negatives = sum(1 for _, _, m in pairs if not m)

    print(f"Paires disponibles: {len(pairs)}")
    print(f"  - Positives: {positives}")
    print(f"  - Negatives: {negatives}")

    if len(pairs) < 100:
        print("Pas assez de paires (minimum 100). Abandon.")
        sys.exit(1)

    path = run_fine_tuning(pairs, batch_size=4)
    print(f"Modele fine-tune sauvegarde: {path}")
