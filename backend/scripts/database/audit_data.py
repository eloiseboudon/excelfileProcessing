"""Data integrity audit script.

Checks all tables for inconsistencies, orphans, duplicates, and suspect data.
Run via Docker: docker exec -it ajt_backend_prod python scripts/database/audit_data.py
Or via SSH:     ssh vps "cd ~/ajtpro && docker exec ajt_backend_prod python scripts/database/audit_data.py"
"""

import sys
from collections import defaultdict

sys.path.insert(0, "/app" if __name__ == "__main__" else ".")

from app import create_app

app = create_app()

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
WARN = "\033[93m⚠\033[0m"


def run_audit():
    issues = []
    warnings = []

    with app.app_context():
        from sqlalchemy import text

        from models import (
            Brand,
            Color,
            ColorTranslation,
            DeviceType,
            InternalProduct,
            LabelCache,
            MatchingRun,
            MemoryOption,
            NightlyJob,
            PendingMatch,
            Product,
            ProductCalculation,
            ProductEanHistory,
            RAMOption,
            Supplier,
            SupplierCatalog,
            SupplierProductRef,
            db,
        )

        print("=" * 70)
        print("AUDIT DE COHERENCE — Base de données AJT Pro")
        print("=" * 70)

        # ---------------------------------------------------------------
        # 1. PRODUCTS — Données manquantes
        # ---------------------------------------------------------------
        print("\n--- 1. PRODUITS ---")

        total_products = Product.query.count()
        print(f"  Total produits: {total_products}")

        no_brand = Product.query.filter(Product.brand_id.is_(None)).count()
        no_memory = Product.query.filter(
            Product.memory_id.is_(None), Product.type_id.isnot(None)
        ).count()
        no_color = Product.query.filter(Product.color_id.is_(None)).count()
        no_type = Product.query.filter(Product.type_id.is_(None)).count()
        no_description = Product.query.filter(
            (Product.description.is_(None)) | (Product.description == "")
        ).count()

        if no_brand:
            issues.append(f"Produits sans marque: {no_brand}")
            print(f"  {FAIL} Produits sans marque: {no_brand}")
        else:
            print(f"  {PASS} Tous les produits ont une marque")

        if no_color:
            warnings.append(f"Produits sans couleur: {no_color}")
            print(f"  {WARN} Produits sans couleur: {no_color}")

        if no_type:
            warnings.append(f"Produits sans type: {no_type}")
            print(f"  {WARN} Produits sans type (device_type): {no_type}")

        if no_description:
            issues.append(f"Produits sans description: {no_description}")
            print(f"  {FAIL} Produits sans description: {no_description}")

        # Produits avec couleur incohérente (description dit une couleur, color_id en dit une autre)
        color_mismatches = db.session.execute(text("""
            SELECT p.id, p.description, c.color
            FROM products p
            JOIN colors c ON c.id = p.color_id
            WHERE p.description IS NOT NULL
            AND (
                (lower(p.description) LIKE '%grey%' AND lower(c.color) NOT IN ('gris'))
                OR (lower(p.description) LIKE '%black%' AND lower(c.color) NOT IN ('noir', 'titane noir'))
                OR (lower(p.description) LIKE '%white%' AND lower(c.color) NOT IN ('blanc', 'titane blanc'))
                OR (lower(p.description) LIKE '% blue%' AND lower(c.color) NOT IN ('bleu', 'lilac blue'))
                OR (lower(p.description) LIKE '%green%' AND lower(c.color) NOT IN ('vert'))
                OR (lower(p.description) LIKE '% red%' AND lower(c.color) NOT IN ('rouge', 'rouge/bleu'))
                OR (lower(p.description) LIKE '%purple%' AND lower(c.color) NOT IN ('violet'))
            )
        """)).fetchall()
        if color_mismatches:
            issues.append(f"Produits avec couleur incohérente: {len(color_mismatches)}")
            print(f"  {FAIL} Produits avec couleur incohérente description/color_id: {len(color_mismatches)}")
            for row in color_mismatches[:10]:
                print(f"       #{row[0]} desc=\"{row[1]}\" color=\"{row[2]}\"")
            if len(color_mismatches) > 10:
                print(f"       ... et {len(color_mismatches) - 10} autres")
        else:
            print(f"  {PASS} Couleurs cohérentes avec les descriptions")

        # Doublons de produits (même description)
        dup_descriptions = db.session.execute(text("""
            SELECT description, COUNT(*) as cnt
            FROM products
            WHERE description IS NOT NULL
            GROUP BY description
            HAVING COUNT(*) > 1
            ORDER BY cnt DESC
            LIMIT 10
        """)).fetchall()
        if dup_descriptions:
            warnings.append(f"Descriptions en double: {len(dup_descriptions)}")
            print(f"  {WARN} Descriptions en double: {len(dup_descriptions)}")
            for row in dup_descriptions[:5]:
                print(f"       \"{row[0]}\" ({row[1]}x)")

        # ---------------------------------------------------------------
        # 2. INTERNAL_PRODUCTS — Orphelins et doublons
        # ---------------------------------------------------------------
        print("\n--- 2. INTERNAL_PRODUCTS (lien Odoo) ---")

        orphan_internal = db.session.execute(text("""
            SELECT ip.id, ip.odoo_id FROM internal_products ip
            LEFT JOIN products p ON p.id = ip.product_id
            WHERE p.id IS NULL
        """)).fetchall()
        if orphan_internal:
            issues.append(f"InternalProduct sans produit: {len(orphan_internal)}")
            print(f"  {FAIL} InternalProduct pointant vers un produit supprimé: {len(orphan_internal)}")
        else:
            print(f"  {PASS} Tous les InternalProduct ont un produit valide")

        dup_odoo = db.session.execute(text("""
            SELECT odoo_id, COUNT(*) as cnt FROM internal_products
            GROUP BY odoo_id HAVING COUNT(*) > 1
        """)).fetchall()
        if dup_odoo:
            issues.append(f"Doublons odoo_id: {len(dup_odoo)}")
            print(f"  {FAIL} odoo_id en double: {len(dup_odoo)}")
            for row in dup_odoo[:5]:
                print(f"       odoo_id={row[0]} ({row[1]}x)")
        else:
            print(f"  {PASS} Pas de doublons odoo_id")

        # ---------------------------------------------------------------
        # 3. COLOR_TRANSLATIONS — Cohérence
        # ---------------------------------------------------------------
        print("\n--- 3. COLOR_TRANSLATIONS ---")

        bad_translations = db.session.execute(text("""
            SELECT ct.color_source, ct.color_target, ct.color_target_id, c.color as actual_color
            FROM color_translations ct
            JOIN colors c ON c.id = ct.color_target_id
            WHERE ct.color_target != c.color
        """)).fetchall()
        if bad_translations:
            issues.append(f"Traductions couleur incohérentes: {len(bad_translations)}")
            print(f"  {FAIL} color_target != colors.color pour color_target_id: {len(bad_translations)}")
            for row in bad_translations:
                print(f"       \"{row[0]}\" → target=\"{row[1]}\" mais id pointe vers \"{row[3]}\"")
        else:
            print(f"  {PASS} Toutes les traductions sont cohérentes")

        # Traductions suspectes (gris traduit en noir, etc.)
        suspect_trans = db.session.execute(text("""
            SELECT color_source, color_target FROM color_translations
            WHERE (lower(color_source) LIKE '%grey%' AND lower(color_target) = 'noir')
               OR (lower(color_source) LIKE '%gray%' AND lower(color_target) = 'noir')
               OR (lower(color_source) LIKE '%white%' AND lower(color_target) = 'noir')
               OR (lower(color_source) LIKE '%blue%' AND lower(color_target) = 'noir')
        """)).fetchall()
        if suspect_trans:
            issues.append(f"Traductions suspectes: {len(suspect_trans)}")
            print(f"  {FAIL} Traductions suspectes:")
            for row in suspect_trans:
                print(f"       \"{row[0]}\" → \"{row[1]}\" (suspect!)")
        else:
            print(f"  {PASS} Pas de traductions suspectes")

        # ---------------------------------------------------------------
        # 4. PRODUCT_CALCULATIONS — Orphelins
        # ---------------------------------------------------------------
        print("\n--- 4. PRODUCT_CALCULATIONS ---")

        orphan_calc = db.session.execute(text("""
            SELECT pc.id FROM product_calculations pc
            LEFT JOIN products p ON p.id = pc.product_id
            WHERE p.id IS NULL
        """)).fetchall()
        if orphan_calc:
            issues.append(f"ProductCalculation orphelins: {len(orphan_calc)}")
            print(f"  {FAIL} Calculs pointant vers un produit supprimé: {len(orphan_calc)}")
        else:
            print(f"  {PASS} Tous les calculs ont un produit valide")

        orphan_calc_supplier = db.session.execute(text("""
            SELECT pc.id FROM product_calculations pc
            WHERE pc.supplier_id IS NOT NULL
            AND pc.supplier_id NOT IN (SELECT id FROM suppliers)
        """)).fetchall()
        if orphan_calc_supplier:
            issues.append(f"ProductCalculation avec supplier invalide: {len(orphan_calc_supplier)}")
            print(f"  {FAIL} Calculs avec supplier_id invalide: {len(orphan_calc_supplier)}")
        else:
            print(f"  {PASS} Tous les suppliers de calculs sont valides")

        # ---------------------------------------------------------------
        # 5. LABEL_CACHE — Orphelins et incohérences
        # ---------------------------------------------------------------
        print("\n--- 5. LABEL_CACHE ---")

        total_cache = LabelCache.query.count()
        matched_cache = LabelCache.query.filter(LabelCache.product_id.isnot(None)).count()
        print(f"  Total: {total_cache} | Matchés: {matched_cache}")

        orphan_label_product = db.session.execute(text("""
            SELECT lc.id, lc.normalized_label FROM label_cache lc
            WHERE lc.product_id IS NOT NULL
            AND lc.product_id NOT IN (SELECT id FROM products)
        """)).fetchall()
        if orphan_label_product:
            issues.append(f"LabelCache pointant vers produit supprimé: {len(orphan_label_product)}")
            print(f"  {FAIL} LabelCache avec product_id invalide: {len(orphan_label_product)}")
        else:
            print(f"  {PASS} Tous les product_id de LabelCache sont valides")

        orphan_label_supplier = db.session.execute(text("""
            SELECT lc.id FROM label_cache lc
            WHERE lc.supplier_id NOT IN (SELECT id FROM suppliers)
        """)).fetchall()
        if orphan_label_supplier:
            issues.append(f"LabelCache avec supplier invalide: {len(orphan_label_supplier)}")
            print(f"  {FAIL} LabelCache avec supplier_id invalide: {len(orphan_label_supplier)}")
        else:
            print(f"  {PASS} Tous les supplier_id de LabelCache sont valides")

        # LabelCache auto-matchés sans extracted_attributes
        auto_no_attrs = LabelCache.query.filter(
            LabelCache.match_source == "auto",
            LabelCache.extracted_attributes.is_(None),
        ).count()
        if auto_no_attrs:
            warnings.append(f"Auto-matchs sans attributs extraits: {auto_no_attrs}")
            print(f"  {WARN} Auto-matchés sans extracted_attributes: {auto_no_attrs}")

        # ---------------------------------------------------------------
        # 6. PENDING_MATCHES — Orphelins
        # ---------------------------------------------------------------
        print("\n--- 6. PENDING_MATCHES ---")

        total_pending = PendingMatch.query.filter_by(status="pending").count()
        total_validated = PendingMatch.query.filter_by(status="validated").count()
        total_rejected = PendingMatch.query.filter_by(status="rejected").count()
        print(f"  Pending: {total_pending} | Validés: {total_validated} | Rejetés: {total_rejected}")

        orphan_pm_product = db.session.execute(text("""
            SELECT pm.id FROM pending_matches pm
            WHERE pm.resolved_product_id IS NOT NULL
            AND pm.resolved_product_id NOT IN (SELECT id FROM products)
        """)).fetchall()
        if orphan_pm_product:
            issues.append(f"PendingMatch avec resolved_product_id invalide: {len(orphan_pm_product)}")
            print(f"  {FAIL} PendingMatch pointant vers produit supprimé: {len(orphan_pm_product)}")
        else:
            print(f"  {PASS} Tous les resolved_product_id sont valides")

        # PendingMatch validated sans resolved_product_id
        validated_no_product = PendingMatch.query.filter(
            PendingMatch.status == "validated",
            PendingMatch.resolved_product_id.is_(None),
        ).count()
        if validated_no_product:
            issues.append(f"PendingMatch validés sans produit résolu: {validated_no_product}")
            print(f"  {FAIL} Validés sans resolved_product_id: {validated_no_product}")
        else:
            print(f"  {PASS} Tous les matchs validés ont un produit résolu")

        # ---------------------------------------------------------------
        # 7. MATCHING_RUNS / NIGHTLY_JOBS — Stuck
        # ---------------------------------------------------------------
        print("\n--- 7. MATCHING_RUNS / NIGHTLY_JOBS ---")

        stuck_runs = MatchingRun.query.filter_by(status="running").count()
        if stuck_runs:
            issues.append(f"MatchingRun bloqués en 'running': {stuck_runs}")
            print(f"  {FAIL} MatchingRun bloqués en 'running': {stuck_runs}")
        else:
            print(f"  {PASS} Aucun MatchingRun bloqué")

        stuck_jobs = NightlyJob.query.filter_by(status="running").count()
        if stuck_jobs:
            issues.append(f"NightlyJob bloqués en 'running': {stuck_jobs}")
            print(f"  {FAIL} NightlyJob bloqués en 'running': {stuck_jobs}")
        else:
            print(f"  {PASS} Aucun NightlyJob bloqué")

        # ---------------------------------------------------------------
        # 8. SUPPLIER_PRODUCT_REF — FK orphelins
        # ---------------------------------------------------------------
        print("\n--- 8. SUPPLIER_PRODUCT_REF ---")

        orphan_ref = db.session.execute(text("""
            SELECT spr.id FROM supplier_product_refs spr
            LEFT JOIN products p ON p.id = spr.product_id
            WHERE p.id IS NULL
        """)).fetchall()
        if orphan_ref:
            issues.append(f"SupplierProductRef orphelins: {len(orphan_ref)}")
            print(f"  {FAIL} Refs fournisseur vers produit supprimé: {len(orphan_ref)}")
        else:
            print(f"  {PASS} Toutes les refs fournisseur sont valides")

        # ---------------------------------------------------------------
        # 9. MEMORY_OPTIONS — Valeurs non normalisées
        # ---------------------------------------------------------------
        print("\n--- 9. REFERENCE DATA ---")

        non_norm_memory = db.session.execute(text("""
            SELECT memory FROM memory_options
            WHERE memory !~ '^[0-9]+ (Go|To)$'
            ORDER BY memory
        """)).fetchall()
        if non_norm_memory:
            warnings.append(f"Mémoires non normalisées: {len(non_norm_memory)}")
            print(f"  {WARN} Mémoires non normalisées: {[r[0] for r in non_norm_memory]}")
        else:
            print(f"  {PASS} Toutes les mémoires sont normalisées")

        unused_brands = db.session.execute(text("""
            SELECT b.id, b.brand FROM brands b
            LEFT JOIN products p ON p.brand_id = b.id
            WHERE p.id IS NULL
        """)).fetchall()
        if unused_brands:
            warnings.append(f"Marques orphelines (aucun produit): {len(unused_brands)}")
            print(f"  {WARN} Marques sans produit: {len(unused_brands)}")

        unused_colors = db.session.execute(text("""
            SELECT c.id, c.color FROM colors c
            LEFT JOIN products p ON p.color_id = c.id
            LEFT JOIN color_translations ct ON ct.color_target_id = c.id
            WHERE p.id IS NULL AND ct.id IS NULL
        """)).fetchall()
        if unused_colors:
            warnings.append(f"Couleurs orphelines: {len(unused_colors)}")
            print(f"  {WARN} Couleurs sans produit ni traduction: {[r[1] for r in unused_colors]}")

        # ---------------------------------------------------------------
        # SUMMARY
        # ---------------------------------------------------------------
        print("\n" + "=" * 70)
        print(f"RÉSUMÉ: {len(issues)} erreur(s), {len(warnings)} avertissement(s)")
        print("=" * 70)

        if issues:
            print(f"\n{FAIL} ERREURS:")
            for issue in issues:
                print(f"  - {issue}")

        if warnings:
            print(f"\n{WARN} AVERTISSEMENTS:")
            for warning in warnings:
                print(f"  - {warning}")

        if not issues and not warnings:
            print(f"\n{PASS} Base de données cohérente !")

        return len(issues)


if __name__ == "__main__":
    sys.exit(run_audit())
