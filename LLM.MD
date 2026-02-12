# Spécification technique — Module de matching LLM

## Document de référence pour l'implémentation

**Projet** : AJT PRO
**Module** : Rapprochement produits fournisseurs par extraction LLM
**Date** : 11/02/2026
**Statut** : Validé — prêt pour implémentation

---

## 1. Décisions actées

| Sujet | Décision |
|-------|----------|
| Déclenchement du matching | **Sur demande** via bouton dans l'UI (pas dans le pipeline ETL auto) |
| Produits sans correspondance | **Création automatique si score < 50**, validation manuelle entre 50-89 |
| Variantes régionales | **Produits distincts** dans le référentiel (EU ≠ US Spec ≠ Indian Spec) |
| Modèle LLM | Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) via API Anthropic |
| Seuils de matching | ≥ 90 auto / 50-89 validation / < 50 création produit |
| Doublons prix/quantité | Un seul appel LLM par libellé unique, résultat en cache pour les doublons |
| Seuils configurables | Hardcodés pour la V1, configurable via UI prévu en V2 |

---

## 2. Prérequis

### 2.1 Compte API Anthropic

- Créer un compte sur [console.anthropic.com](https://console.anthropic.com)
- Générer une clé API
- Charger 5€ de crédits prépayés
- Ajouter dans `.env` :

```bash
ANTHROPIC_API_KEY=sk-ant-xxxxx
LLM_MODEL=claude-haiku-4-5-20251001
LLM_BATCH_SIZE=25
MATCH_THRESHOLD_AUTO=90
MATCH_THRESHOLD_REVIEW=50
```

### 2.2 Dépendance Python

```bash
# Ajouter dans requirements.txt
anthropic>=0.40.0
```

---

## 3. Modifications du modèle de données

### 3.1 Migration : colonne `region` sur `products`

```python
# alembic/versions/xxxx_add_region_to_products.py

def upgrade():
    op.add_column('products', sa.Column('region', sa.String(30), nullable=True))
    op.add_column('temporary_imports', sa.Column('region', sa.String(30), nullable=True))

def downgrade():
    op.drop_column('products', 'region')
    op.drop_column('temporary_imports', 'region')
```

Valeurs attendues : `null` (EU par défaut), `"US"`, `"IN"`, `"DE"`, etc.

Impact modèle SQLAlchemy (`models.py`) :
```python
class Product(db.Model):
    # ... colonnes existantes ...
    region = db.Column(db.String(30), nullable=True)  # NOUVEAU

class TemporaryImport(db.Model):
    # ... colonnes existantes ...
    region = db.Column(db.String(30), nullable=True)  # NOUVEAU
```

### 3.2 Nouvelle table : `model_references`

Table de correspondance codes constructeur → nom commercial.

```python
class ModelReference(db.Model):
    __tablename__ = "model_references"

    id = db.Column(db.Integer, primary_key=True)
    manufacturer_code = db.Column(db.String(50), nullable=False, unique=True)
    commercial_name = db.Column(db.String(100), nullable=False)
    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id"), nullable=True)
    brand = db.relationship("Brand", backref=db.backref("model_references", lazy=True))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

Données initiales (script d'insertion ou migration) :

```
SM-S938B / S938B  →  Galaxy S25 Ultra     (Samsung)
SM-S936B / S936B  →  Galaxy S25+          (Samsung)
SM-S931B / S931B  →  Galaxy S25           (Samsung)
SM-S928B / S928B  →  Galaxy S24 Ultra     (Samsung)
SM-S926B / S926B  →  Galaxy S24+          (Samsung)
SM-S921B / S921B  →  Galaxy S24           (Samsung)
SM-A566B / A566B  →  Galaxy A56           (Samsung)
SM-A556B / A556B  →  Galaxy A55           (Samsung)
SM-A546B / A546B  →  Galaxy A54           (Samsung)
SM-A356B / A356B  →  Galaxy A35           (Samsung)
SM-A166B / A166B  →  Galaxy A16           (Samsung)
SM-X230N / X230N  →  Galaxy Tab A11+      (Samsung)
```

### 3.3 Nouvelle table : `label_cache`

Cache des résultats de matching LLM pour éviter les appels redondants.

```python
class LabelCache(db.Model):
    __tablename__ = "label_cache"

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=False)
    supplier = db.relationship("Supplier", backref=db.backref("label_cache", lazy=True))
    normalized_label = db.Column(db.String(300), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    product = db.relationship("Product", backref=db.backref("label_cache", lazy=True))
    match_score = db.Column(db.Integer, nullable=True)
    match_source = db.Column(db.String(20), nullable=False)  # 'auto', 'manual', 'llm'
    extracted_attributes = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('supplier_id', 'normalized_label', name='uix_label_cache'),
    )
```

### 3.4 Nouvelle table : `pending_matches`

File d'attente pour les matchs en attente de validation (score 50-89).

```python
class PendingMatch(db.Model):
    __tablename__ = "pending_matches"

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=False)
    supplier = db.relationship("Supplier")
    temporary_import_id = db.Column(db.Integer, db.ForeignKey("temporary_imports.id"), nullable=True)
    source_label = db.Column(db.String(300), nullable=False)
    extracted_attributes = db.Column(db.JSON, nullable=False)
    candidates = db.Column(db.JSON, nullable=False)  # [{product_id, score, details}]
    status = db.Column(db.String(20), default='pending')  # 'pending', 'validated', 'rejected', 'created'
    resolved_product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
```

### 3.5 Enrichissement `color_translations`

Couleurs à ajouter d'après l'analyse des données Yukatel et PlusPos :

| color_source | color_target_id (couleur cible) |
|-------------|-------------------------------|
| Midnight | → Noir |
| Starlight | → Blanc |
| Space Black | → Noir |
| Space Grey | → Gris |
| Space Gray | → Gris |
| Graphite | → Gris |
| Cloud White | → Blanc |
| Mist Blue | → Bleu |
| Sky Blue | → Bleu |
| Deep Blue | → Bleu |
| Cosmic Orange | → Orange |
| Desert Titanium | → Titane Désert * |
| Natural Titanium | → Titane Naturel * |
| Black Titanium | → Titane Noir * |
| White Titanium | → Titane Blanc * |
| Deep Purple | → Violet |
| Jetblack | → Noir |
| Jet Black | → Noir |
| Light Gold | → Or |
| Lavender | → Lavande * |
| Sage | → Vert |
| Obsidian | → Noir |
| Moonstone | → Bleu |
| Charcoal | → Gris |

\* Ces couleurs n'existent peut-être pas encore dans la table `colors` → à créer.

---

## 4. Backend — Module LLM matching

### 4.1 Architecture fichiers

```
backend/
├── utils/
│   └── llm_matching.py          # NOUVEAU — logique complète du matching
├── routes/
│   └── matching.py              # NOUVEAU — endpoints API
├── models.py                    # Modifié — nouvelles tables + colonne region
```

### 4.2 `backend/utils/llm_matching.py`

#### Fonction 1 : `normalize_label(label: str) -> str`

Normalise un libellé pour servir de clé de cache.

```python
def normalize_label(label: str) -> str:
    """
    Supprime les espaces multiples, met en minuscule,
    retire les caractères spéciaux inutiles.
    'Apple iPhone 15 128GB - Black' → 'apple iphone 15 128gb black'
    """
```

#### Fonction 2 : `build_extraction_prompt(labels: list[str], context: dict) -> str`

Construit le prompt système avec injection dynamique des valeurs de référence.

```python
def build_extraction_prompt(labels: list[str], context: dict) -> str:
    """
    context contient :
    - brands: list[str] depuis Brand.query.all()
    - colors: dict[str, list[str]] depuis Color + ColorTranslation
    - storage_options: list[str] depuis MemoryOption.query.all()
    - model_references: dict[str, str] depuis ModelReference.query.all()
    - device_types: list[str] depuis DeviceType.query.all()
    """
```

**Prompt système :**

```
Tu es un expert en identification de produits électroniques (smartphones,
tablettes, accessoires, audio). À partir de chaque libellé fournisseur,
extrais les attributs structurés.

MARQUES CONNUES : {brands}

COULEURS CONNUES (nom français → synonymes acceptés) :
{colors_with_all_synonyms}

STOCKAGES CONNUS : {storage_options}

CORRESPONDANCES CODES CONSTRUCTEUR :
{model_references}

TYPES D'APPAREILS : {device_types}

RÈGLES D'EXTRACTION :
1. brand : identifie la marque parmi les marques connues
2. model_family : le nom commercial du modèle SANS la marque, le stockage
   ni la couleur. Ex: "iPhone 15 Pro Max", "Galaxy S25 Ultra", "AirPods 4 ANC"
   - Si un code constructeur Samsung est présent (S938B, A566B...),
     utilise la table de correspondance
3. storage : capacité de stockage en "Go" (128GB → "128 Go"). null si absent
4. color : normalise en français en utilisant les synonymes fournis.
   Si la couleur n'est dans aucun synonyme, garde le nom original
5. device_type : Smartphone, Tablette, Accessoire, Audio, etc.
6. region : null si standard EU. "US" si US Spec, "IN" si Indian Spec,
   "DE" si (DE), etc.
7. connectivity : "WiFi" si [W], "Cellular" si mention cellular/LTE,
   "5G" si mentionné, null sinon
8. grade : A, B, C si mentionné, null sinon
9. confidence : score entre 0.0 et 1.0

Réponds UNIQUEMENT avec un JSON array, sans markdown ni texte autour.
Un objet par libellé, dans le même ordre que les entrées.
```

**Message utilisateur :**

```
Extrais les attributs de ces {n} libellés :
1. {label_1}
2. {label_2}
...
```

#### Fonction 3 : `call_llm_extraction(labels: list[str], context: dict) -> list[dict]`

Appel API Claude et parsing de la réponse.

```python
import anthropic

def call_llm_extraction(labels: list[str], context: dict) -> list[dict]:
    """
    Envoie un batch de libellés à Claude Haiku.
    Retourne une liste de dicts avec les attributs extraits.
    
    Gestion d'erreurs :
    - Retry 2x en cas de timeout ou erreur 5xx
    - Si le JSON est invalide, retente avec un batch plus petit
    - Log chaque appel (nombre de tokens in/out, durée, coût)
    """
    client = anthropic.Anthropic()  # utilise ANTHROPIC_API_KEY depuis env
    
    prompt = build_extraction_prompt(labels, context)
    
    response = client.messages.create(
        model=os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001"),
        max_tokens=4096,
        system=prompt,
        messages=[{
            "role": "user",
            "content": f"Extrais les attributs de ces {len(labels)} libellés :\n"
                       + "\n".join(f"{i+1}. {l}" for i, l in enumerate(labels))
        }]
    )
    
    return json.loads(response.content[0].text)
```

#### Fonction 4 : `score_match(extracted: dict, product: Product) -> int`

Calcule un score de correspondance entre les attributs extraits et un produit du référentiel.

```python
def score_match(extracted: dict, product: Product, mappings: dict) -> int:
    """
    Score sur 100.
    
    Pondération :
    - brand:        15 pts (match exact insensible casse, sinon 0 et arrêt)
    - model_family: 40 pts (exact=40, fuzzy Levenshtein≤3 = 20-30, sinon 0)
    - storage:      25 pts (match exact obligatoire, sinon disqualifiant)
    - color:        15 pts (exact ou via color_translations=15, sinon -5)
    - region:        5 pts (match exact, null==null=5)
    
    Si brand ou storage ne matchent pas → retourne 0 directement.
    """
```

#### Fonction 5 : `find_best_matches(extracted: dict, products: list, top_n=3) -> list`

Trouve les meilleurs candidats dans le référentiel.

```python
def find_best_matches(extracted: dict, products: list, mappings: dict, top_n=3):
    """
    Retourne les top_n meilleurs matchs triés par score décroissant.
    
    Optimisation : pré-filtre sur brand_id avant le scoring complet
    pour éviter de scorer tous les produits.
    
    Retour : [{"product_id": int, "score": int, "product_name": str, "details": dict}]
    """
```

#### Fonction 6 : `create_product_from_extraction(extracted: dict) -> Product`

Crée un nouveau produit dans le référentiel à partir des attributs LLM.

```python
def create_product_from_extraction(extracted: dict) -> Product:
    """
    Crée un Product avec :
    - model = extracted["model_family"]
    - description = label fournisseur original
    - brand_id = lookup Brand par nom
    - memory_id = lookup MemoryOption par stockage
    - color_id = lookup Color par nom (+ color_translations)
    - type_id = lookup DeviceType par type
    - region = extracted["region"]
    
    Si une couleur/mémoire/marque n'existe pas → la créer dans la table de ref.
    
    Flag : le champ description contient "[AUTO]" en préfixe pour repérage.
    """
```

#### Fonction 7 : `run_matching_job(supplier_id: int | None = None) -> dict`

Orchestre tout le processus de matching.

```python
def run_matching_job(supplier_id: int | None = None) -> dict:
    """
    Flux principal :
    
    1. Charger les temporary_imports (filtrés par supplier_id si fourni)
    2. Dédupliquer les libellés uniques
    3. Pour chaque libellé unique :
       a. Vérifier le label_cache → si trouvé, utiliser le résultat caché
       b. Sinon, ajouter au batch LLM
    4. Envoyer les batchs au LLM (par lots de 25)
    5. Pour chaque résultat d'extraction :
       a. Scorer contre le référentiel products
       b. Score ≥ 90 → créer supplier_product_ref + alimenter label_cache
       c. Score 50-89 → créer pending_match
       d. Score < 50 → créer le produit + supplier_product_ref + label_cache
    6. Retourner le rapport :
       {
         "total_labels": int,
         "from_cache": int,
         "llm_calls": int,
         "auto_matched": int,
         "pending_review": int,
         "auto_created": int,
         "errors": int,
         "cost_estimate": float,
         "duration_seconds": float
       }
    """
```

### 4.3 `backend/routes/matching.py`

```python
bp = Blueprint("matching", __name__)

@bp.route("/matching/run", methods=["POST"])
@token_required("admin")
def run_matching():
    """
    Lance le matching LLM sur les temporary_imports.
    Body optionnel : {"supplier_id": int}
    Retourne le rapport de matching.
    """

@bp.route("/matching/pending", methods=["GET"])
@token_required("admin")
def list_pending():
    """
    Liste les matchs en attente de validation.
    Query params : supplier_id, page, per_page
    Retourne : [{id, source_label, extracted_attributes, candidates, created_at}]
    """

@bp.route("/matching/validate", methods=["POST"])
@token_required("admin")
def validate_match():
    """
    Valide un match proposé.
    Body : {"pending_match_id": int, "product_id": int}
    Actions :
    - Met à jour pending_match.status = 'validated'
    - Crée le supplier_product_ref
    - Alimente le label_cache (source: 'manual')
    - Enrichit color_translations si couleur corrigée
    """

@bp.route("/matching/reject", methods=["POST"])
@token_required("admin")
def reject_match():
    """
    Rejette un match et optionnellement crée un nouveau produit.
    Body : {"pending_match_id": int, "create_product": bool}
    """

@bp.route("/matching/stats", methods=["GET"])
@token_required("admin")
def matching_stats():
    """
    Statistiques globales du matching.
    Retourne : {
      total_cached, total_pending, total_auto_matched,
      total_auto_created, cache_hit_rate,
      by_supplier: [{name, cached, pending, matched, created}]
    }
    """

@bp.route("/matching/cache", methods=["GET"])
@token_required("admin")
def list_cache():
    """
    Consultation du cache de labels.
    Permet de voir et purger des entrées si besoin.
    """

@bp.route("/matching/cache/<int:cache_id>", methods=["DELETE"])
@token_required("admin")
def delete_cache_entry(cache_id):
    """Supprime une entrée du cache (force un re-matching au prochain run)."""
```

### 4.4 Enregistrement du blueprint

Dans `app.py`, ajouter :

```python
from routes.matching import bp as matching_bp
app.register_blueprint(matching_bp)
```

---

## 5. Frontend

### 5.1 Bouton de déclenchement

Sur `DataImportPage.tsx`, dans le panel de synchronisation, ajouter un bouton :

```
[🔗 Lancer le rapprochement]  (par fournisseur ou global)
```

Au clic :
- Appel `POST /matching/run` (avec ou sans `supplier_id`)
- Affichage d'un spinner + barre de progression si possible
- À la fin, notification avec le résumé :
  "342 matchés automatiquement, 8 en attente de validation, 15 nouveaux produits créés"

### 5.2 Page de validation (`MatchingValidationPage.tsx`)

Nouvelle page accessible depuis la navigation (ou onglet dans DataImportPage).

**Éléments :**
- Badge dans la navigation avec le nombre de matchs en attente
- Liste filtrable par fournisseur
- Pour chaque pending_match :
  - Le libellé fournisseur original
  - Les attributs extraits par le LLM (brand, model, storage, color, region)
  - Les candidats proposés avec leur score
  - Boutons : Valider / Voir alternatives / Créer produit / Ignorer
- Actions en masse : valider tout au-dessus d'un certain score

### 5.3 Widget statistiques

Dans le dashboard existant, un petit widget :
- Taux de cache hit (%)
- Nombre de matchs en attente
- Répartition auto / manual / créé par semaine

---

## 6. Flux complet — Scénario type

```
1. L'admin lance la sync Yukatel (pipeline ETL existant)
   → 3000 lignes dans temporary_imports
   → Rapport : "2100 matchés par EAN, 900 sans correspondance"

2. L'admin clique sur [🔗 Lancer le rapprochement]
   → Le module LLM traite les 900 libellés non matchés
   → 700 en cache (déjà vus lors d'une précédente sync) → match instantané
   → 200 nouveaux → 8 appels LLM (batchs de 25)
   → Résultat :
     - 150 matchés automatiquement (score ≥ 90)
     - 30 en attente de validation (score 50-89)
     - 20 nouveaux produits créés (score < 50)

3. L'admin va sur la page de validation
   → Valide 25 matchs, corrige 3, rejette 2
   → Les 25 validés alimentent le cache

4. Prochaine sync : les 25 labels corrigés sont en cache
   → Encore moins d'appels LLM nécessaires
```

---

## 7. Planning d'implémentation

| Jour | Tâches | Livrable |
|------|--------|----------|
| **J1** | Migration Alembic (region, model_references, label_cache, pending_matches) + modèles SQLAlchemy + seed color_translations + seed model_references | Base de données prête |
| **J2** | `llm_matching.py` : fonctions 1-3 (normalize, prompt, appel LLM) + tests unitaires avec libellés réels | Extraction LLM fonctionnelle en CLI |
| **J3** | `llm_matching.py` : fonctions 4-6 (scoring, matching, création produit) | Matching complet en CLI |
| **J4** | `llm_matching.py` : fonction 7 (orchestration) + `routes/matching.py` (tous les endpoints) | API REST complète |
| **J5** | Test end-to-end avec données Yukatel + PlusPos réelles, calibrage des seuils | Rapport de performance |
| **J6** | Frontend : bouton de déclenchement + page de validation | UI fonctionnelle |
| **J7** | Frontend : widget stats + polish + tests + déploiement | Production |

---

## 8. Métriques de succès

| Métrique | Cible V1 | Cible après 1 mois |
|----------|----------|---------------------|
| Taux de match automatique (score ≥ 90) | > 70% | > 90% |
| Taux de cache hit (2ème sync+) | > 60% | > 95% |
| Temps de matching pour 3000 produits | < 5 min | < 30 sec (grâce au cache) |
| Coût LLM par sync | < 0.30€ | < 0.05€ |
| Faux positifs (match auto incorrect) | < 5% | < 2% |