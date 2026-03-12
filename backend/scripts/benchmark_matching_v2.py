"""Benchmark: compare V1 (linear scan) vs V2 (BM25 + FAISS) matching results.

Dry-run — no database writes. Compares the top candidate and score for each
product between the two pipelines and reports any regressions.

Usage (inside Docker):
    docker exec -it ajt_backend_prod python scripts/benchmark_matching_v2.py

Or locally:
    cd backend && python scripts/benchmark_matching_v2.py
"""

from __future__ import annotations

import os
import sys
import time

# Ensure backend root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DATABASE_URL", "")
os.environ.setdefault("JWT_SECRET", "benchmark-key-not-used-for-auth-32bytes!")


def main():
    from app import app

    with app.app_context():
        from models import (
            LabelCache,
            Product,
            ProductCalculation,
            ProductEanHistory,
            SupplierCatalog,
        )
        from utils.llm_matching import _build_mappings, score_match
        from utils.matching.bm25_blocker import BM25Blocker

        print("=" * 70)
        print("BENCHMARK: V1 (linear) vs V2 (BM25 + FAISS) matching")
        print("=" * 70)

        # --- Load data (same as run_matching_job Phase 2 setup) ---
        all_cache_entries = LabelCache.query.filter(
            LabelCache.match_source == "extracted",
            LabelCache.product_id.is_(None),
        ).all()

        if not all_cache_entries:
            print("\nAucun LabelCache non-matché (match_source=extracted, product_id=NULL).")
            print("Rien à benchmarker.")
            return

        # Products already matched — exclude them
        matched_product_ids = {
            row[0]
            for row in ProductCalculation.query.with_entities(
                ProductCalculation.product_id
            ).filter(ProductCalculation.product_id.isnot(None)).distinct().all()
        } | {
            row[0]
            for row in LabelCache.query.with_entities(
                LabelCache.product_id
            ).filter(LabelCache.product_id.isnot(None)).distinct().all()
        }

        all_products = Product.query.all()
        products_to_process = [
            p for p in all_products if p.id not in matched_product_ids
        ]

        if not products_to_process:
            print("\nTous les produits sont déjà matchés. Rien à benchmarker.")
            return

        print(f"\nDonnées chargées:")
        print(f"  - LabelCache non-matchés: {len(all_cache_entries)}")
        print(f"  - Produits à traiter:     {len(products_to_process)}")

        # --- Build indexes ---
        mappings = _build_mappings()

        # Brand index (V1)
        brand_to_entries = {}
        for entry in all_cache_entries:
            attrs = entry.extracted_attributes or {}
            brand = (attrs.get("brand") or "").strip().lower()
            brand_to_entries.setdefault(brand, []).append(entry)

        # BM25 blocker (V2)
        bm25_blocker = BM25Blocker(all_cache_entries)
        print(f"  - BM25 index:             {bm25_blocker.size} entries")

        # FAISS (V2 — optional)
        faiss_index = None
        product_embeddings = {}
        try:
            from utils.matching.embedder import compute_label_embeddings, compute_product_embeddings
            from utils.matching.faiss_index import FAISSIndex

            label_embeddings = compute_label_embeddings(all_cache_entries)
            faiss_index = FAISSIndex()
            faiss_index.build(label_embeddings)
            product_embeddings = compute_product_embeddings(products_to_process)
            print(f"  - FAISS index:            {faiss_index.size} entries")
        except ImportError:
            print("  - FAISS:                  non disponible (sentence-transformers manquant)")

        # EAN data
        label_to_catalogs = {}
        for ti in SupplierCatalog.query.all():
            label = ti.description or ti.model or ""
            from utils.normalize import normalize_label
            normalized = normalize_label(label)
            if normalized and ti.supplier_id:
                key = (ti.supplier_id, normalized)
                label_to_catalogs.setdefault(key, []).append(ti)

        label_eans = {}
        for key, catalogs in label_to_catalogs.items():
            eans = {c.ean.strip() for c in catalogs if c.ean}
            if eans:
                label_eans[key] = eans

        ean_to_product_ids = {}
        for p in all_products:
            if p.ean:
                ean_to_product_ids.setdefault(p.ean.strip(), set()).add(p.id)
        for hist in ProductEanHistory.query.all():
            if hist.ean:
                ean_to_product_ids.setdefault(hist.ean.strip(), set()).add(hist.product_id)

        # --- Score helper ---
        def _score_with_ean(entry, product):
            attrs = dict(entry.extracted_attributes or {})
            score, details = score_match(attrs, product, mappings)
            if score > 0:
                entry_eans = label_eans.get(
                    (entry.supplier_id, entry.normalized_label), set()
                )
                for ean in entry_eans:
                    if product.id in ean_to_product_ids.get(ean, set()):
                        details["ean_bonus"] = 20
                        score = min(score + 20, 100)
                        break
            return score, details, entry

        # --- Run benchmark ---
        print(f"\nBenchmark en cours sur {len(products_to_process)} produits...\n")

        regressions = []
        improvements = []
        same = 0
        v1_not_found = 0
        v2_not_found = 0
        v1_total_time = 0.0
        v2_total_time = 0.0

        for product in products_to_process:
            prod_brand = (product.brand.brand if product.brand else "").strip().lower()

            # --- V1: linear scan ---
            t0 = time.time()
            if prod_brand:
                v1_candidates = brand_to_entries.get(prod_brand, []) + brand_to_entries.get("", [])
            else:
                v1_candidates = all_cache_entries

            v1_scored = []
            for entry in v1_candidates:
                s, d, e = _score_with_ean(entry, product)
                if s > 0:
                    v1_scored.append((s, d, e))
            v1_scored.sort(key=lambda x: x[0], reverse=True)
            v1_total_time += time.time() - t0

            v1_top = v1_scored[0] if v1_scored else None

            # --- V2: BM25 + FAISS ---
            t0 = time.time()
            bm25_results = bm25_blocker.get_candidates(product, top_k=50)
            bm25_ids = {e.id for e in bm25_results}

            faiss_ids = set()
            if faiss_index and product.id in product_embeddings:
                faiss_results = faiss_index.search(product_embeddings[product.id], top_k=100)
                faiss_ids = {lid for lid, _ in faiss_results}

            v2_candidate_ids = bm25_ids | faiss_ids
            id_to_entry = {e.id: e for e in all_cache_entries}
            v2_candidates = [id_to_entry[lid] for lid in v2_candidate_ids if lid in id_to_entry]

            v2_scored = []
            for entry in v2_candidates:
                s, d, e = _score_with_ean(entry, product)
                if s > 0:
                    v2_scored.append((s, d, e))
            v2_scored.sort(key=lambda x: x[0], reverse=True)
            v2_total_time += time.time() - t0

            v2_top = v2_scored[0] if v2_scored else None

            # --- Compare ---
            v1_score = v1_top[0] if v1_top else 0
            v2_score = v2_top[0] if v2_top else 0
            v1_label_id = v1_top[2].id if v1_top else None
            v2_label_id = v2_top[2].id if v2_top else None

            if v1_score == 0:
                v1_not_found += 1
            if v2_score == 0:
                v2_not_found += 1

            if v1_score == v2_score and v1_label_id == v2_label_id:
                same += 1
            elif v2_score < v1_score:
                product_name = product.model or product.description or f"ID:{product.id}"
                regressions.append({
                    "product_id": product.id,
                    "product": product_name,
                    "v1_score": v1_score,
                    "v2_score": v2_score,
                    "v1_label_id": v1_label_id,
                    "v2_label_id": v2_label_id,
                    "delta": v1_score - v2_score,
                })
            elif v2_score > v1_score:
                product_name = product.model or product.description or f"ID:{product.id}"
                improvements.append({
                    "product_id": product.id,
                    "product": product_name,
                    "v1_score": v1_score,
                    "v2_score": v2_score,
                    "delta": v2_score - v1_score,
                })

        # --- Report ---
        total = len(products_to_process)
        print("=" * 70)
        print("RÉSULTATS")
        print("=" * 70)
        print(f"  Produits testés:    {total}")
        print(f"  Identiques:         {same} ({same*100//total}%)")
        print(f"  Améliorations V2:   {len(improvements)}")
        print(f"  Régressions V2:     {len(regressions)}")
        print(f"  Not found V1:       {v1_not_found}")
        print(f"  Not found V2:       {v2_not_found}")
        print(f"  Temps V1:           {v1_total_time:.2f}s")
        print(f"  Temps V2:           {v2_total_time:.2f}s")
        print(f"  Speedup:            {v1_total_time/v2_total_time:.1f}x" if v2_total_time > 0 else "")

        if regressions:
            print(f"\n{'='*70}")
            print(f"RÉGRESSIONS ({len(regressions)})")
            print(f"{'='*70}")
            regressions.sort(key=lambda x: x["delta"], reverse=True)
            for r in regressions[:20]:
                print(
                    f"  [{r['product_id']:>4}] {r['product'][:40]:<40} "
                    f"V1={r['v1_score']:>3} → V2={r['v2_score']:>3} "
                    f"(Δ-{r['delta']})"
                )
            if len(regressions) > 20:
                print(f"  ... et {len(regressions)-20} autres")

        if improvements:
            print(f"\n{'='*70}")
            print(f"AMÉLIORATIONS ({len(improvements)})")
            print(f"{'='*70}")
            improvements.sort(key=lambda x: x["delta"], reverse=True)
            for r in improvements[:10]:
                print(
                    f"  [{r['product_id']:>4}] {r['product'][:40]:<40} "
                    f"V1={r['v1_score']:>3} → V2={r['v2_score']:>3} "
                    f"(Δ+{r['delta']})"
                )

        # --- Verdict ---
        print(f"\n{'='*70}")
        if not regressions:
            print("✅ AUCUNE RÉGRESSION — V2 est safe à activer")
        elif len(regressions) <= total * 0.01:
            print(f"⚠️  {len(regressions)} régressions mineures (<1%) — vérifier manuellement")
        else:
            pct = len(regressions) * 100 / total
            print(f"❌ {len(regressions)} régressions ({pct:.1f}%) — investiguer avant d'activer V2")
        print("=" * 70)


if __name__ == "__main__":
    main()
