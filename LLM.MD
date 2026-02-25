# Référence technique — Module matching LLM

**Statut** : En production
**Dernière mise à jour** : 2026-02-25
**Pour la description fonctionnelle (UI, vues, statistiques)** → voir `docs/VUES.md` Vue 11 et Vue 14

---

## 1. Décisions actées

| Sujet | Décision courante |
|-------|-------------------|
| Déclenchement | Sur demande (bouton UI) **ou** automatique via pipeline nightly |
| Modèle LLM | Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) via API Anthropic |
| Taille de batch | 25 libellés par appel LLM |
| Seuil auto-match | ≥ 90 pts → `SupplierProductRef` créé automatiquement |
| Seuil validation | 50-89 pts → `PendingMatch(status='pending')` |
| Seuil rejet | < 50 pts → `PendingMatch(status='rejected')` |
| Création produit | **Supprimée** (commit 7f7540d) — la création se fait via Admin > Référence |
| Direction matching | Product-centric : on itère sur les produits Odoo non matchés (commit b86c248) |
| Seuils configurables | Hardcodés (V1). Variables d'env prévues en V2 |

---

## 2. Configuration

```bash
ANTHROPIC_API_KEY=sk-ant-xxxxx
LLM_MODEL=claude-haiku-4-5-20251001
LLM_BATCH_SIZE=25
MATCH_THRESHOLD_AUTO=90
MATCH_THRESHOLD_REVIEW=50
```

---

## 3. Algorithme de scoring

### Score sur 95 pts

| Critère | Pts max | Hard disqualify si mismatch |
|---------|---------|----------------------------|
| Marque | 15 | Oui — les deux côtés non-null |
| Couleur | 15 | Oui — les deux côtés non-null |
| Stockage | 25 | Oui — les deux côtés ont une valeur identifiable |
| Famille modèle | 40 | Non (fuzzy matching Levenshtein) |
| Région | ×0 ou ×1 | Oui — les deux côtés non-null |
| Similarité libellé | variable | Non |

**Région = gate multiplier** : si les deux côtés ont une région non-null ET différente → score ×0 (hard disqualify). Sinon → score ×1 (inchangé). La région n'ajoute aucun point additif.

### Règle both-sides-non-null pour le stockage

Hard disqualify uniquement si les **deux côtés** ont un stockage identifiable :
- Côté Odoo : champ `memory.memory` OU stockage lisible dans le nom du modèle (ex: "iPhone 14 128GB")
- Côté fournisseur : champ `storage` extrait par le LLM

Si un seul côté a le stockage → 0 pts, pas de hard disqualification.

### Auto-rejet

Si **tous** les candidats d'un produit déclenchent un hard disqualifier → `PendingMatch(status='rejected')` créé automatiquement avec le meilleur candidat disqualifié pour traçabilité.

---

## 4. LabelCache — bibliothèque historique

### Structure

| Champ | Rôle | Comportement nightly |
|-------|------|---------------------|
| `normalized_label` | Clé de cache (libellé normalisé par fournisseur) | — |
| `extracted_attributes` | JSON : résultat extraction LLM (marque, modèle, stockage…) | **Jamais effacé** |
| `product_id` | Produit Odoo associé (match validé) | Effacé au reset nightly, restauré après auto-validation |
| `match_source` | `'auto'`, `'manual'`, `'llm'`, `'attr_share'` | — |
| `match_reasoning` | JSONB : détail du score par critère | Mis à jour à chaque décision |

### Optimisations Phase 1

- **Cache hit** : libellé déjà vu avec `extracted_attributes` non-null → 0 appel LLM. Seule la Phase 2 (scoring) est relancée.
- **Cross-supplier sharing** (`match_source='attr_share'`) : attributs extraits identiques à une entrée validée d'un autre fournisseur → `product_id` assigné directement, Phase 2 contournée.
- **N-shot learning** : jusqu'à 10 extractions validées à haute confiance injectées dans le prompt LLM, max 3 par marque (diversification).

### Mode nightly (`skip_already_matched=True`)

En mode nightly, l'exclusion normale (`ProductCalculation` + `LabelCache.product_id`) est bypassed :
- Tous les `PendingMatch` sont supprimés
- `LabelCache.product_id` est remis à NULL (les `extracted_attributes` sont conservés)
- `run_matching_job(skip_already_matched=True)` re-score **tous** les produits
- Après matching, `_apply_validation_history()` auto-valide les matches stables

---

## 5. Endpoints API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/matching/run` | Lance le job de rapprochement (async) |
| `GET` | `/matching/status` | Statut et résultat du dernier run (in-memory) |
| `GET` | `/matching/pending` | Liste paginée des matchs (filtre statut/fournisseur) |
| `POST` | `/matching/validate` | Valide un match (`pending` ou `rejected`) |
| `POST` | `/matching/reject` | Rejette un match |
| `GET` | `/matching/stats` | Statistiques globales (couverture, par fournisseur) |
| `GET` | `/matching/cache` | Liste des entrées LabelCache |
| `DELETE` | `/matching/cache/<id>` | Supprime une entrée (force re-extraction) |
| `POST` | `/matching/assign-types` | Assigne automatiquement les `device_type` manquants |

---

## 6. Pipeline nightly

Voir `docs/VUES.md` **Vue 14** pour la description complète.

Paramètre clé dans `run_matching_job` :

```python
def run_matching_job(
    supplier_id: Optional[int] = None,
    limit: Optional[int] = None,
    skip_already_matched: bool = False,   # True en mode nightly
) -> Dict[str, Any]:
```

Quand `skip_already_matched=True` :
- `matched_product_ids = set()` — ignore `ProductCalculation`
- `pending_product_ids = set()` — ignore `PendingMatch` existants

Variables d'environnement nightly :

```bash
ENABLE_NIGHTLY_SCHEDULER=false   # true pour activer le scheduler auto
NIGHTLY_WEBHOOK_URL=             # URL webhook n8n pour le rapport email
FRONTEND_URL=                    # Utilisé dans le lien du rapport email
```

---

## 7. Coût estimé

| Scénario | Coût |
|----------|------|
| 3 000 produits — run initial | < 0.30€ (Claude Haiku 4.5) |
| Runs nightly suivants | ~0€ si libellés inchangés (100% cache hit) |
| Nouveaux libellés / jour | ~0.001€ par libellé nouveau |
