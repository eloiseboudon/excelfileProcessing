# Architecture technique -- AJT PRO

Document de reference pour l'architecture du projet AJT PRO, application de gestion tarifaire destinee a un revendeur de telephonie et electronique. L'application croise une base de references internes avec les donnees issues des API fournisseurs afin de calculer des prix de vente optimaux selon des marges configurables.

---

## 1. Vue d'ensemble

```
+------------------+       HTTPS        +----------------------------+
|                  | -----------------> |                            |
|   Navigateur     |                    |   Frontend                 |
|   (SPA React)    | <----------------- |   React 18 / TypeScript    |
|                  |    HTML/JS/CSS     |   Vite + Tailwind CSS      |
+------------------+                    |   (Nginx en production)    |
                                        +----------------------------+
                                                    |
                                                    | API REST (JSON)
                                                    | JWT Bearer Token
                                                    v
                                        +----------------------------+
                                        |                            |
                                        |   Backend                  |
                                        |   Python Flask             |
                                        |   SQLAlchemy ORM           |
                                        |   (Gunicorn en production) |
                                        +----------------------------+
                                            |                |
                                            |                |
                              +-------------+                +----------------+
                              |                                               |
                              v                                               v
                +----------------------------+              +----------------------------+
                |                            |              |                            |
                |   PostgreSQL 16            |              |   APIs fournisseurs        |
                |   Base de donnees          |              |   (HTTP/REST externes)     |
                |   principale               |              |                            |
                +----------------------------+              +----------------------------+
```

**Frontend** : Application monopage (SPA) construite avec React 18, TypeScript, Vite et Tailwind CSS. Le routage est gere par React Router. En production, les fichiers statiques sont servis par Nginx.

**Backend** : Serveur Flask exposant une API REST. L'ORM SQLAlchemy gere l'acces aux donnees. Les migrations sont pilotees par Alembic. En production, le serveur est lance via Gunicorn avec 4 workers.

**Base de donnees** : PostgreSQL 16 heberge l'ensemble des donnees metier, des references produits, des calculs de prix et des configurations d'API fournisseurs.

**APIs fournisseurs** : Le backend interroge les APIs externes des fournisseurs pour recuperer les catalogues produits. Les configurations de connexion (URL, authentification, pagination) sont stockees en base.

---

## 2. Modele de donnees

Le schema se decompose en plusieurs groupes fonctionnels.

### 2.1 Fournisseurs et configuration API

| Table              | Role                                                                                     |
| ------------------ | ---------------------------------------------------------------------------------------- |
| `suppliers`        | Informations fournisseur (nom, email, telephone, adresse).                               |
| `supplier_apis`    | Configuration d'acces API par fournisseur (base_url, type d'authentification, headers, rate_limit). Types d'auth supportes : `none`, `api_key`, `basic`, `oauth2`. |
| `api_endpoints`    | Definition des endpoints (path, methode HTTP, query_params, body_template, items_path). Modes de pagination : `none`, `page`, `cursor`, `link`, `offset`. |
| `field_maps`       | Regles de mapping entre les champs de la reponse API et les champs internes.             |
| `mapping_versions` | Versionnage des configurations de mapping pour tracabilite.                               |

Relations :
- Un `supplier` possede une ou plusieurs `supplier_apis`.
- Chaque `supplier_api` est associee a un ou plusieurs `api_endpoints`.
- Chaque `api_endpoint` est lie a un ou plusieurs `field_maps`, eux-memes versionnes via `mapping_versions`.

### 2.2 Pipeline ETL et donnees brutes

| Table                  | Role                                                                                     |
| ---------------------- | ---------------------------------------------------------------------------------------- |
| `api_fetch_jobs`       | Historique des jobs de synchronisation (statut : `running`, `success`, `failed`, horodatages, rapports). |
| `raw_ingests`          | Stockage brut des reponses API pour audit et rejeu.                                      |
| `parsed_items`         | Donnees normalisees extraites des reponses API apres application du mapping.             |
| `supplier_catalog`    | Table de staging pour les produits importes avant integration definitive.                 |
| `supplier_product_refs`| References produit propres a chaque fournisseur (EAN, part_number, supplier_sku, last_seen_at). |

Relations :
- Un `api_fetch_job` produit un ou plusieurs `raw_ingests`.
- Les `raw_ingests` alimentent les `parsed_items` via le mapping.
- Les `parsed_items` sont ensuite injectes dans `supplier_catalog`.
- Les `supplier_product_refs` font le lien entre un fournisseur (`supplier`) et un produit interne (`products`).

### 2.3 Produits et references internes

| Table                  | Role                                                                                     |
| ---------------------- | ---------------------------------------------------------------------------------------- |
| `products`             | Reference produit interne (nom, marque, couleur, memoire, RAM, norme, type d'appareil, EAN, TCP). |
| `product_calculations` | Calculs de prix par produit, fournisseur et semaine (prix d'achat, prix de vente, marge, TCP, quantite). |
| `brands`               | Table de reference des marques.                                                          |
| `colors`               | Table de reference des couleurs.                                                         |
| `color_translations`   | Synonymes de noms de couleurs pour le matching (ex. : "Noir" / "Black" / "Midnight").    |
| `memory_options`       | Options de stockage (32 Go, 64 Go, 128 Go, etc.).                                       |
| `ram_options`          | Options de RAM.                                                                          |
| `norms`                | Normes (grades de qualite).                                                              |
| `device_types`         | Types d'appareils (smartphone, tablette, etc.).                                          |

Relations :
- Un `product` reference une `brand`, une `color`, un `memory_option`, un `ram_option`, une `norm` et un `device_type`.
- Les `product_calculations` relient un `product` a un `supplier` pour une semaine donnee.

### 2.4 Rapprochement LLM

| Table                  | Role                                                                                     |
| ---------------------- | ---------------------------------------------------------------------------------------- |
| `model_references`     | Correspondances codes constructeur → nom commercial (ex: SM-S938B → Galaxy S25 Ultra).   |
| `label_cache`          | Cache des resultats d'extraction LLM par fournisseur et libelle normalise.               |
| `pending_matches`      | Matchs en attente de validation manuelle (attributs extraits + candidats scores).         |

Relations :
- Un `label_cache` reference un `supplier` et optionnellement un `product`.
- Un `pending_match` reference un `supplier` et optionnellement un `supplier_catalog` et un `product` (resolu).

### 2.5 Utilisateurs, parametres et Odoo

| Table              | Role                                                                                     |
| ------------------ | ---------------------------------------------------------------------------------------- |
| `users`            | Comptes utilisateurs (username, password_hash, role : `admin` ou `user`).                |
| `user_settings`    | Preferences utilisateur (ex. : graphiques visibles sur le tableau de bord).              |
| `graph_settings`   | Activation/desactivation des types de graphiques sur la page statistiques.               |
| `odoo_config`      | Configuration de connexion Odoo (URL, base, identifiants chiffres Fernet).               |
| `odoo_sync_jobs`   | Historique des jobs de synchronisation Odoo (statut, rapport, horodatages).              |

---

## 3. Pipeline ETL (synchronisation fournisseur)

La synchronisation des donnees fournisseur suit un pipeline en cinq etapes, orchestre par la fonction `run_fetch_job()`.

### Declenchement

L'utilisateur declenche la synchronisation depuis le composant `SupplierApiSyncPanel` du frontend. Un appel `POST /supplier_api/<supplier_id>` est envoye au backend, qui selectionne l'endpoint et le mapping a utiliser, puis cree un enregistrement `ApiFetchJob` avec le statut `running`.

### Etapes du pipeline

```
1. _validate_fetch_params()
   |   Charge le job, l'endpoint, le mapping et le fournisseur.
   |   Verifie la coherence des parametres.
   v
2. _execute_api_request()
   |   Effectue l'appel HTTP vers l'API fournisseur.
   |   Stocke la reponse brute dans raw_ingests (audit).
   |   Extrait les items via le champ items_path de l'endpoint.
   v
3. _parse_and_deduplicate()
   |   Applique les regles de field_maps sur chaque item.
   |   Normalise les donnees (couleurs, marques, memoire, etc.).
   v
4. _persist_supplier_catalog()
   |   Deduplique les items normalises.
   |   Insere dans parsed_items et supplier_catalog.
   v
5. Post-traitement
      Met a jour supplier_product_refs.last_seen_at pour les
      references reconnues.
      Recalcule les prix dans product_calculations via le
      module de pricing.
      Retourne un rapport : produits mis a jour, absents de
      la base, absents de l'API.
```

### Statuts du job

| Statut    | Signification                                     |
| --------- | ------------------------------------------------- |
| `running` | Le job est en cours d'execution.                  |
| `success` | Le pipeline s'est execute sans erreur.            |
| `failed`  | Une erreur est survenue ; le rapport contient les details. |

Le rapport final contient trois categories :
- **Produits mis a jour** : references internes dont le prix a ete recalcule.
- **Absents de la base** : produits presents chez le fournisseur mais sans correspondance interne.
- **Absents de l'API** : produits internes non retrouves dans le catalogue fournisseur.

---

## 4. Systeme d'authentification JWT

L'authentification repose sur des JSON Web Tokens (JWT) signes en HS256.

### Tokens

| Token          | Duree de vie                           | Usage                                      |
| -------------- | -------------------------------------- | ------------------------------------------ |
| Access token   | Courte (configurable via `TOKEN_EXPIRATION`)         | Authentifie chaque requete API.            |
| Refresh token  | Longue (configurable via `REFRESH_TOKEN_EXPIRATION`) | Permet d'obtenir un nouvel access token.   |

### Contenu du payload

```json
{
  "user_id": 42,
  "exp": 1700000000,
  "iat": 1699999000,
  "type": "access"
}
```

Les champs `exp` (expiration) et `iat` (issued at) sont des timestamps UNIX. Le champ `type` distingue les access tokens des refresh tokens.

### Stockage cote client

- L'access token est conserve en memoire (variable JavaScript).
- Le refresh token est stocke dans le `localStorage` du navigateur.
- Le client API centralise (`api.ts`) injecte automatiquement le header `Authorization: Bearer <token>` via la fonction utilitaire `crudRequest()`.

### Protection des routes

Le decorateur `@token_required` est applique sur les routes protegees du backend. Il :
1. Extrait le token du header `Authorization`.
2. Verifie la signature HS256 avec le secret `JWT_SECRET`.
3. Controle la date d'expiration.
4. Injecte l'identifiant utilisateur dans le contexte de la requete.

Si le token est expire, le frontend utilise le refresh token pour en obtenir un nouveau de maniere transparente.

---

## 5. Calcul des prix et marges

Le module de pricing est partage entre le backend (`backend/utils/pricing.py`) et le frontend (`frontend/src/utils/processing.ts`) pour garantir la coherence des calculs.

### Constantes

```python
COMMISSION_RATE = 0.045  # 4,5 %

PRICE_THRESHOLDS = [15, 29, 49, 79, 99, 129, 149, 179, 209, 299, 499, 799, 999]

PRICE_MULTIPLIERS = [
    1.25,  # prix <= 15
    1.22,  # prix <= 29
    1.20,  # prix <= 49
    1.18,  # prix <= 79
    1.15,  # prix <= 99
    1.11,  # prix <= 129
    1.10,  # prix <= 149
    1.09,  # prix <= 179
    1.09,  # prix <= 209
    1.08,  # prix <= 299
    1.08,  # prix <= 499
    1.07,  # prix <= 799
    1.07,  # prix <= 999
    1.06,  # prix > 999
]
```

### Formules

**TCP (Cout Technique Produit)** : valeur forfaitaire liee a la capacite de stockage.

| Capacite    | TCP    |
| ----------- | ------ |
| 32 Go       | 10 EUR |
| 64 Go       | 12 EUR |
| 128 Go +    | 14 EUR |

**Commission** :

```
commission = prix_achat * COMMISSION_RATE
```

**Prix avec TCP** :

```
prix_tcp = prix_achat + TCP + commission
```

**Prix avec marge** : le multiplicateur est determine par la tranche dans laquelle tombe le prix d'achat.

```
prix_marge = prix_achat * multiplicateur
```

**Prix de vente final** :

```
prix_vente = ceil(max(prix_tcp, prix_marge))
```

Le prix retenu est l'arrondi superieur du maximum entre le prix integrant le TCP et le prix integrant la marge. Cela garantit que la marge minimale couvre toujours les couts techniques et la commission.

---

## 6. Mapping dynamique des champs API

Chaque fournisseur expose ses donnees dans un format propre. Le systeme de mapping dynamique permet d'adapter l'ingestion sans modification de code.

### Fonctionnement

1. **Configuration** : pour chaque endpoint (`api_endpoints`), un ensemble de regles de mapping est defini dans `field_maps`. Chaque regle associe un chemin dans la reponse JSON du fournisseur a un champ interne normalise (nom, marque, couleur, memoire, prix, EAN, etc.).

2. **Versionnage** : les configurations de mapping sont versionnees via `mapping_versions`. Cela permet de revenir a une version anterieure en cas de regression et d'auditer les changements.

3. **Application** : lors de l'etape `_parse_and_deduplicate()` du pipeline ETL, chaque item extrait de la reponse brute est transforme en appliquant les regles du mapping actif. Les valeurs sont normalisees (traduction des couleurs via `color_translations`, resolution des marques, etc.).

### Exemple de mapping

Un fournisseur retourne :

```json
{
  "articles": [
    {
      "ref": "IP15-128-BLK",
      "designation": "iPhone 15 128Go Noir",
      "prix_ht": 650.00,
      "code_ean": "1234567890123"
    }
  ]
}
```

Configuration correspondante :
- `items_path` de l'endpoint : `articles`
- Regles de mapping :
  - `ref` -> `supplier_sku`
  - `designation` -> `name`
  - `prix_ht` -> `purchase_price`
  - `code_ean` -> `ean`

### Types d'authentification supportes

| Type      | Description                                                        |
| --------- | ------------------------------------------------------------------ |
| `none`    | Aucune authentification requise.                                   |
| `api_key` | Cle API transmise en header ou en parametre de requete.            |
| `basic`   | Authentification HTTP Basic (username/password).                   |
| `oauth2`  | Flux OAuth2 (les parametres sont stockes dans `auth_config`).      |

### Types de pagination supportes

| Type     | Description                                                         |
| -------- | ------------------------------------------------------------------- |
| `none`   | Pas de pagination, toutes les donnees sont retournees en une fois.  |
| `page`   | Pagination par numero de page.                                      |
| `cursor` | Pagination par curseur (token de continuation).                     |
| `link`   | Pagination via les headers `Link` (RFC 5988).                       |
| `offset` | Pagination par offset/limit.                                        |

---

## 7. Infrastructure et deploiement

### Architecture Docker Compose

L'application est containerisee via Docker Compose avec trois services.

```
+-------------------+     +-------------------+     +-------------------+
|                   |     |                   |     |                   |
|   Nginx           |---->|   Gunicorn        |---->|   PostgreSQL 16   |
|   (port 80/443)   |     |   Flask backend   |     |   (port 5432)     |
|   fichiers static |     |   4 workers       |     |                   |
|                   |     |                   |     |                   |
+-------------------+     +-------------------+     +-------------------+
```

### Environnement de developpement

| Service    | Outil                     | Port par defaut |
| ---------- | ------------------------- | --------------- |
| Frontend   | Vite dev server           | 5173            |
| Backend    | Flask dev server          | 5000            |
| Base       | PostgreSQL 16             | 5432            |

En developpement, le frontend (Vite) et le backend (Flask) tournent chacun dans leur propre conteneur avec rechargement a chaud.

### Environnement de production

| Service    | Outil                     | Details                            |
| ---------- | ------------------------- | ---------------------------------- |
| Frontend   | Nginx                     | Sert les fichiers statiques du build React. Reverse proxy vers le backend. |
| Backend    | Gunicorn (4 workers)      | Sert l'API Flask.                  |
| Base       | PostgreSQL 16             | Health checks configures.          |

### Scripts utilitaires

| Script        | Role                                                              |
| ------------- | ----------------------------------------------------------------- |
| `deploy.sh`   | Deploiement complet (build, migration, redemarrage des services). |
| `save_db.sh`  | Sauvegarde et restauration de la base de donnees.                 |

### Organisation du backend

Les routes sont organisees par domaine fonctionnel :

| Module       | Responsabilite                                  |
| ------------ | ----------------------------------------------- |
| `auth`       | Authentification, gestion des tokens.           |
| `products`   | CRUD produits, calculs, refresh catalogue fournisseurs. |
| `imports`    | Import de fichiers, integration des donnees.    |
| `matching`   | Rapprochement LLM (run, pending, validate, reject, stats, cache). |
| `odoo`       | Synchronisation Odoo (config, test, sync, jobs, auto-sync). |
| `references` | Tables de reference (marques, couleurs, etc.).  |
| `stats`      | Statistiques et tableaux de bord.               |
| `settings`   | Parametres utilisateur et application.          |
| `users`      | Gestion des comptes utilisateurs.               |

### Organisation des utilitaires backend

| Module               | Responsabilite                                               |
| -------------------- | ------------------------------------------------------------ |
| `utils/auth`         | Generation et verification des JWT, decorateur `@token_required`. |
| `utils/calculations` | Fonctions de calcul de prix et de marge.                     |
| `utils/crypto`       | Chiffrement/dechiffrement Fernet (mot de passe Odoo).        |
| `utils/etl`          | Pipeline de synchronisation fournisseur (`run_fetch_job`).   |
| `utils/llm_matching` | Module matching LLM (extraction, scoring, orchestration).    |
| `utils/odoo_scheduler` | Planificateur de synchronisation automatique Odoo.         |
| `utils/odoo_sync`    | Client XML-RPC et moteur de synchronisation Odoo.            |
| `utils/pricing`      | Constantes partagees (seuils, multiplicateurs, commission).  |

### Organisation du frontend

Le frontend suit une architecture par composants :

- **Pages** : `ProductsPage`, `StatisticsPage`, `SearchPage`, etc. Chaque page correspond a une route React Router.
- **Composants** : sous-composants reutilisables, organises par fonctionnalite.
- **API client** : module centralise `api.ts` avec la fonction `crudRequest()` qui gere les headers d'authentification, la serialisation JSON et la gestion d'erreurs.
- **Utilitaires** : `processing.ts` contient les constantes et fonctions de calcul de prix, dupliquees depuis le backend pour le calcul cote client.
