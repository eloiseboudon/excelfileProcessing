"""Fine-tuning pipeline for the bi-encoder on validation history.

Exports training pairs from PendingMatch (validated/rejected) and
LabelCache (high-confidence auto-matches), then fine-tunes the
sentence-transformer model.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List, Optional, Tuple

MIN_PAIRS_REQUIRED = 100


def export_training_pairs(db_session) -> List[Tuple[str, str, bool]]:
    """Extract training pairs from the database.

    Returns list of (label_text, product_text, is_match).
    """
    from models import LabelCache, PendingMatch, Product

    pairs: List[Tuple[str, str, bool]] = []

    # Positive pairs from validated PendingMatches
    validated = PendingMatch.query.filter_by(status="validated").all()
    for pm in validated:
        label_text = pm.source_label or ""
        if not label_text or not pm.candidates:
            continue
        for c in pm.candidates:
            pid = c.get("product_id")
            if not pid:
                continue
            product = db_session.get(Product, pid)
            if product:
                product_text = _product_to_text(product)
                if label_text and product_text:
                    pairs.append((label_text, product_text, True))

    # Negative pairs from rejected PendingMatches
    rejected = PendingMatch.query.filter_by(status="rejected").all()
    for pm in rejected:
        label_text = pm.source_label or ""
        if not label_text or not pm.candidates:
            continue
        for c in pm.candidates:
            pid = c.get("product_id")
            if not pid:
                continue
            product = db_session.get(Product, pid)
            if product:
                product_text = _product_to_text(product)
                if label_text and product_text:
                    pairs.append((label_text, product_text, False))

    # High-confidence auto-matches as positive pairs
    auto_matched = LabelCache.query.filter(
        LabelCache.product_id.isnot(None),
        LabelCache.match_source == "auto",
        LabelCache.match_score >= 95,
    ).all()
    for lc in auto_matched:
        raw_label = (lc.extracted_attributes or {}).get("raw_label", "")
        if not raw_label:
            raw_label = lc.normalized_label or ""
        product = db_session.get(Product, lc.product_id)
        if product and raw_label:
            product_text = _product_to_text(product)
            if product_text:
                pairs.append((raw_label, product_text, True))

    return pairs


def run_fine_tuning(
    pairs: List[Tuple[str, str, bool]],
    output_path: Optional[str] = None,
    epochs: int = 3,
    batch_size: int = 16,
) -> str:
    """Fine-tune the bi-encoder on training pairs.

    Args:
        pairs: list of (text_a, text_b, is_match).
        output_path: where to save the fine-tuned model.
        epochs: number of training epochs.
        batch_size: training batch size.

    Returns:
        Path to the saved model.

    Raises:
        ValueError: if not enough training pairs.
    """
    if len(pairs) < MIN_PAIRS_REQUIRED:
        raise ValueError(
            f"Need at least {MIN_PAIRS_REQUIRED} pairs, got {len(pairs)}"
        )

    from sentence_transformers import InputExample, SentenceTransformer, losses
    from torch.utils.data import DataLoader

    from utils.matching.embedder import _MODEL_NAME

    if output_path is None:
        output_path = os.environ.get(
            "MATCHING_MODEL_PATH", "/app/data/models/matching-finetuned"
        )

    model = SentenceTransformer(_MODEL_NAME)

    train_examples = [
        InputExample(texts=[a, b], label=1.0 if match else 0.0)
        for a, b, match in pairs
    ]

    train_dataloader = DataLoader(
        train_examples, shuffle=True, batch_size=batch_size
    )
    train_loss = losses.CosineSimilarityLoss(model)

    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=epochs,
        warmup_steps=int(len(train_dataloader) * 0.1),
        output_path=output_path,
        show_progress_bar=True,
    )

    return output_path


def _product_to_text(product) -> str:
    """Build text representation for a Product."""
    parts = [
        product.brand.brand if product.brand else "",
        product.model or "",
        product.description or "",
        product.memory.memory if product.memory else "",
        product.color.color if product.color else "",
    ]
    return " ".join(p for p in parts if p).strip()
