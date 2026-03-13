# Module Matching LLM — Documentation technique

## Vue d'ensemble

Le matching LLM rapproche automatiquement les labels fournisseurs avec les produits du référentiel Odoo. Il fonctionne en 2 phases :

1. **Phase 1 — Extraction** : Claude Haiku extrait les attributs structurés de chaque label fournisseur
2. **Phase 2 — Scoring** : Chaque produit Odoo est comparé aux extractions pour trouver le meilleur match

### Pipeline V2 (avancé)

Activable via `MATCHING_V2_ENABLED=true`, le pipeline V2 remplace le scan linéaire de Phase 2 par un retrieval multi-étapes plus intelligent :

**En V1**, le système parcourait tous les labels fournisseurs un par un pour chaque produit (scan linéaire filtré par marque). Ça fonctionne, mais c'est lent et ne s'améliore pas avec le temps.

**En V2**, le système utilise deux méthodes complémentaires pour présélectionner rapidement les candidats les plus pertinents, puis les affine :

```
Label fournisseur
    ↓
[BM25 blocking] → top-200 candidats par mots-clés (recherche textuelle)
    ↓
[FAISS ANN search] → top-200 candidats par similarité sémantique (embeddings IA)
    ↓
[Union + dédup] → fusion des deux listes de candidats
    ↓
[score_match()] → scoring déterministe par attributs (identique à la V1)
    ↓
[Cross-encoder] → affinage IA pour les cas ambigus (scores 70-90)
    ↓
Décision : auto-match / pending / auto-rejeté / non trouvé
```

**Avantage clé** : le modèle IA (bi-encoder) s'améliore avec le temps. Chaque validation manuelle (acceptée ou rejetée) enrichit les données d'entraînement. Le fine-tuning périodique du modèle rend les embeddings plus précis pour le domaine télécoms/électronique, ce qui améliore la qualité de la présélection.

**Modules** (`backend/utils/matching/`) :

| Module | Rôle | Dépendance |
|--------|------|------------|
| `bm25_blocker.py` | Pré-sélection top-k candidats par TF-IDF (BM25Plus) | `rank-bm25` |
| `embedder.py` | Bi-encoder sémantique (`paraphrase-multilingual-mpnet-base-v2`) | `sentence-transformers` |
| `faiss_index.py` | Index ANN pour recherche sub-milliseconde sur embeddings | `faiss-cpu` |
| `cross_encoder.py` | Reranking cross-encoder pour la zone grise (scores 70-90) | `sentence-transformers` |
| `fine_tuner.py` | Fine-tuning du bi-encoder sur l'historique de validations | `sentence-transformers` |
| `retrieval_pipeline.py` | Orchestrateur qui relie BM25 + FAISS + cross-encoder | — |

**Configuration** :

| Variable d'environnement | Défaut | Description |
|--------------------------|--------|-------------|
| `MATCHING_V2_ENABLED` | `false` | Active le pipeline V2 complet (BM25 + FAISS + cross-encoder) |
| `MATCHING_MODEL_PATH` | `/app/data/models/matching-finetuned` | Chemin du modèle fine-tuné |
| `FAISS_INDEX_DIR` | `/app/data/faiss` | Répertoire de persistance FAISS |

Un seul flag active tout. Si `sentence-transformers`/`faiss-cpu` ne sont pas installés, FAISS et le cross-encoder sont désactivés automatiquement (fallback gracieux sur BM25 seul).

**Rollback** : désactiver `MATCHING_V2_ENABLED` revient instantanément au scan linéaire V1 sans redéploiement.

### Fine-tuning

Le bi-encoder peut être fine-tuné sur les validations manuelles (PendingMatch validated/rejected) et les auto-matchs haute confiance (score ≥ 95). Minimum 100 paires requis. Le fine-tuning se lance manuellement (pas dans le nightly).

Le modèle fine-tuné est sauvegardé dans `/app/data/models/matching-finetuned` (volume Docker persistant). Au démarrage, l'embedder charge automatiquement ce modèle s'il existe, sinon il utilise le modèle de base.

```bash
# Lancer le fine-tuning (tuer Gunicorn d'abord pour libérer la RAM)
docker exec ajt_backend_prod bash -c "kill -TERM 1; python scripts/run_fine_tuning.py"
docker compose -f docker-compose.prod.yml restart backend
```

### Comparaison V1 vs V2 — Benchmark du 12 mars 2026

Un benchmark a été réalisé sur 912 produits non-matchés pour comparer les deux pipelines. Le scoring déterministe (attributs, seuils) est identique — seule la méthode de pré-sélection des candidats change.

| Métrique | V1 (scan linéaire) | V2 (BM25 + FAISS) |
|----------|--------------------|--------------------|
| **Résultats identiques** | — | 704 / 912 (77%) |
| **Régressions** | — | 13 (1.4%) |
| **Not found** | 495 | 505 |
| **Temps de traitement** | 230 s | 97 s |
| **Speedup** | — | **2.4x plus rapide** |

**Détail des 13 régressions** : toutes dans la zone "pending review" (scores entre 50 et 55), aucune dans la zone auto-match (≥ 90). Les candidats concernés étaient en limite de détection par BM25, rattrapés par le scan exhaustif V1 mais pas par le top-200 V2. L'impact fonctionnel est négligeable : ces produits passent en validation manuelle au lieu d'être auto-matchés.

**Conclusion** : la V2 reproduit fidèlement les résultats de la V1 tout en étant 2.4x plus rapide. Les 13 régressions mineures sont acceptables. L'avantage principal de la V2 est sa capacité à s'améliorer avec le temps grâce au fine-tuning sur les validations manuelles — plus il y a de validations, plus les embeddings sont précis et plus le retrieval est pertinent.

## Attributs extraits (12)

| # | Attribut | Type | Description |
|---|----------|------|-------------|
| 1 | `brand` | string | Marque identifiée parmi les marques connues |
| 2 | `model_family` | string | Nom commercial SANS marque, stockage, couleur |
| 3 | `storage` | string/null | Capacité stockage normalisée en "Go" |
| 4 | `color` | string/null | Couleur normalisée en français |
| 5 | `device_type` | string | Smartphone, Tablette, Accessoire, Audio, etc. |
| 6 | `region` | string | "EU" par défaut, "US", "IN", "DE", etc. Jamais null |
| 7 | `connectivity` | string/null | "WiFi", "Cellular", "5G", null |
| 8 | `grade` | string/null | A, B, C si mentionné |
| 9 | `confidence` | float | Score de confiance LLM (0.0-1.0) |
| 10 | `ram` | string/null | RAM en "Go" si mentionnée séparément du stockage |
| 11 | `dual_sim` | bool | true si Dual SIM / DS détecté |
| 12 | `enterprise_edition` | bool | true si Enterprise Edition / EE détecté |

## Scoring (0-100 pts)

| Composant | Points | Type |
|-----------|--------|------|
| Brand | 15 | Hard disqualifier si mismatch |
| Device Type | 0 | Hard disqualifier si mismatch |
| Storage | 25 | Hard disqualifier si mismatch |
| Model Family | 0-45 | Fuzzy matching (ratio ≥0.6) |
| Model Variant | 0 | Hard disqualifier si suffixe diffère (Pro/Plus/Ultra/Max/Lite/FE/FE+/Mini/S) |
| Color | 15 | Hard disqualifier si mismatch |
| Enterprise Edition | -20 | Soft malus si mismatch |
| Dual SIM | -10 | Soft malus si mismatch |
| Region | ×0/×1 | Gate (mismatch → score 0) |
| Label similarity | ±10 | Bonus/malus fuzzy sur le label brut |

**Seuils** : ≥90 → auto-match, 50-89 → pending review, <50 → not found

## Post-traitement regex (`_apply_post_processing`)

Après l'extraction LLM, un post-traitement déterministe enrichit/corrige les attributs via regex. Cela rattrape les patterns que le LLM peut manquer :

| Pattern | Champ enrichi | Exemple |
|---------|--------------|---------|
| `enterprise edition` | `enterprise_edition = True` | "Galaxy A36 Enterprise Edition" |
| `EE` (isolé) | `enterprise_edition = True` | "S25 5G 256GB EE Silver" |
| `dual sim` | `dual_sim = True` | "Galaxy A16 Dual Sim 128GB" |
| `DS` (isolé) | `dual_sim = True` | "Galaxy A07 DS 64GB" |
| `Xgb ram Ygb` | `ram = "X Go"` | "6GB RAM 128GB" → ram="6 Go" |
| `X/Ygb` | `ram = "X Go"` | "12/256GB" → ram="12 Go" |
| `{W}` ou `w` isolé | `connectivity = "WiFi"` | "Tab S10 128Go W EU" |
| `tablet ` préfixe | `device_type = "Tablette"` | "Tablet Samsung Galaxy Tab..." |
| `watch ` préfixe | `device_type = "Montre"` | "Watch Samsung Galaxy Watch..." |

## Nettoyage model (`_clean_model_for_scoring`)

Avant le fuzzy matching du model_family, les deux côtés (extraction + produit) sont nettoyés symétriquement :

- Stockage : `128GB`, `256 Go`, `1 To` → supprimé
- RAM/Storage combiné : `12/128GB`, `6gb ram` → supprimé
- Enterprise Edition / EE → supprimé
- Dual SIM / DS → supprimé
- Region : `Indian Spec`, `US Spec`, `(DE)` → supprimé
- Connectivity : `5G`, `4G`, `LTE`, `WiFi` → supprimé
- Parenthèses vides, espaces multiples → nettoyés

## Conventions par fournisseur

### einsAmobile (Ensa) — Labels compacts

| Convention | Exemple | Signification |
|-----------|---------|---------------|
| `W` ou `w` suffixe | `tab s10 lite 128go silver w eu` | WiFi |
| `EU` / `DE` suffixe | `256go black eu` | Région |
| Pas de marqueur | `iphone 16 256gb black` | EU par défaut |
| `EE` suffixe | `s25 5g 256gb ee silver` | Enterprise Edition |
| Stockage seul | `256go` | Pas de RAM dans le label |

### Yuka — Labels verbeux

| Convention | Exemple | Signification |
|-----------|---------|---------------|
| `Dual Sim` explicite | `galaxy a16 dual sim 128gb` | Dual SIM |
| `Xgo ram Ygo` | `12go ram 512go` | RAM + Stockage séparés |
| `Enterprise Edition` | `s26 12go ram 512go enterprise edition` | EE en toutes lettres |
| `WiFi` | `tab x400 wifi 256go` | Connectivité |
| Préfixes catégorie | `tablet`, `watch`, `laptop` | Type d'appareil |
| `region west` | `watch 7 lte region west` | Région |
