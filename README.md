# AJT PRO -- Gestion de tarification

Application de gestion tarifaire pour un revendeur de telephonie et electronique. AJT PRO croise les donnees produits issues d'Odoo avec les API fournisseurs afin de piloter les couts d'achat et de calculer les prix de vente. L'application permet d'importer les catalogues fournisseurs via API, de calculer les marges selon des seuils configurables et de gerer un referentiel produit complet.

---

## Table des matieres

1. [Prerequis](#prerequis)
2. [Installation et configuration](#installation-et-configuration)
3. [Demarrage rapide](#demarrage-rapide)
4. [Structure du projet](#structure-du-projet)
5. [Fonctionnalites principales](#fonctionnalites-principales)
6. [Scripts utilitaires](#scripts-utilitaires)
7. [Migrations Alembic](#migrations-alembic)
8. [Sauvegarde et restauration de la base](#sauvegarde-et-restauration-de-la-base)
9. [Documentation API](#documentation-api)
10. [Verifications locales](#verifications-locales)

---

## Prerequis

| Outil | Version minimale |
|-------|-----------------|
| Docker et Docker Compose | version recente |
| Node.js | 18+ |
| Python | 3.12 |
| PostgreSQL | 16 (fourni via Docker) |

---

## Installation et configuration

### 1. Cloner le depot

```bash
git clone <url-du-depot>
cd ajtpro
```

### 2. Variables d'environnement

Copiez le fichier d'exemple puis adaptez les valeurs a votre environnement.

```bash
cp .env.example .env
```

Contenu type du fichier `.env` :

```bash
FRONTEND_URL=http://localhost:5173
VITE_API_BASE=http://localhost:5001
FLASK_HOST=0.0.0.0
PORT=5001
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/ajtpro
FLASK_ENV=development
FLASK_DEBUG=1
POSTGRES_DB=ajtpro
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
JWT_SECRET=change-me
ODOO_ENCRYPTION_KEY=<cle-fernet-generee>
ENABLE_ODOO_SCHEDULER=false
ANTHROPIC_API_KEY=sk-ant-xxxxx
LLM_MODEL=claude-haiku-4-5-20251001
```

**Points importants :**

- `FRONTEND_URL` doit correspondre exactement a l'origine du frontend (schema + domaine) pour que la politique CORS fonctionne.
- `JWT_SECRET` doit etre remplace par une valeur aleatoire et securisee en production (minimum 32 caracteres pour SHA-256).
- `ODOO_ENCRYPTION_KEY` est la cle Fernet utilisee pour chiffrer le mot de passe Odoo en base. Generez-la avec : `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
- Le fichier `.env` est ignore par Git afin de proteger les informations sensibles.

### 3. Identifiants par defaut

Le script `backend/scripts/database/implement_tables.py` cree automatiquement un utilisateur administrateur :

- **Nom d'utilisateur** : `admin`
- **Mot de passe** : `admin`

Changez ces identifiants des le premier deploiement en production.

---

## Demarrage rapide

### Environnement de developpement

Le mode developpement utilise `docker-compose.yml` combine avec `docker-compose.override.yml`.

```bash
# Construire les images
make docker-build

# Demarrer tous les services en arriere-plan
make docker-up

# Consulter les logs d'un service
make docker-logs SERVICE=backend
```

Les services sont alors accessibles aux adresses suivantes :

| Service | Adresse |
|---------|---------|
| Frontend (Vite) | http://localhost:5173 |
| Backend (Flask) | http://localhost:5001 |
| PostgreSQL | localhost:5433 |

### Environnement de production

Le mode production utilise `docker-compose.yml` combine avec `docker-compose.prod.yml`. Le backend tourne sous Gunicorn avec 4 workers ; le frontend est servi par Nginx. Des health checks sont configures sur tous les services.

```bash
# Demarrer en production
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

| Service | Port expose |
|---------|------------|
| Frontend (Nginx) | 3000 |
| Backend (Gunicorn) | 8000 |
| PostgreSQL | 5433 |

Le script `deploy.sh` automatise le deploiement complet en production.

```bash
./deploy.sh
```

### Arreter les services

```bash
make docker-down
```

---

## Structure du projet

```
ajtpro/
├── backend/
│   ├── alembic/              # Migrations de base de donnees
│   ├── routes/
│   │   ├── auth.py           # Authentification (login, refresh, logout)
│   │   ├── imports.py        # Import de fichiers et synchronisation API
│   │   ├── main.py           # Route sante (/)
│   │   ├── matching.py       # Rapprochement LLM (run, pending, validate, reject, stats, cache)
│   │   ├── odoo.py           # Synchronisation Odoo (config, test, sync, jobs)
│   │   ├── products.py       # CRUD produits, calculs et refresh catalogue fournisseurs
│   │   ├── references.py     # Tables de reference (marques, couleurs, etc.)
│   │   ├── settings.py       # Parametres utilisateur
│   │   ├── stats.py          # Statistiques de prix
│   │   └── users.py          # Gestion des utilisateurs
│   ├── scripts/
│   │   ├── database/         # Scripts d'import et initialisation
│   │   └── run_supplier_api_sync_batch.py
│   ├── utils/
│   │   ├── auth.py            # Generation et validation JWT
│   │   ├── calculations.py    # Calculs de prix et marges
│   │   ├── crypto.py          # Chiffrement/dechiffrement Fernet (mot de passe Odoo)
│   │   ├── etl.py             # Pipeline ETL synchronisation fournisseurs
│   │   ├── llm_matching.py    # Module matching LLM (extraction, scoring, orchestration)
│   │   ├── odoo_scheduler.py  # Planificateur synchro auto Odoo
│   │   ├── odoo_sync.py       # Client XML-RPC et moteur synchro Odoo
│   │   └── pricing.py         # Constantes et fonctions de tarification partagees
│   ├── app.py                # Point d'entree Flask
│   ├── models.py             # Modeles SQLAlchemy
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AdminPage.tsx              # Administration generale
│   │   │   ├── BrandSupplierChart.tsx     # Graphique marque/fournisseur
│   │   │   ├── DataImportPage.tsx         # Synchronisation fournisseurs (onglets Synchro/Rapports/Odoo/Rapprochement)
│   │   │   ├── MatchingPanel.tsx          # Rapprochement LLM (declenchement, validation, stats)
│   │   │   ├── FormattingPage.tsx         # Mise en forme
│   │   │   ├── ImportPreviewModal.tsx     # Apercu avant import
│   │   │   ├── InfoButton.tsx             # Bouton info (i)
│   │   │   ├── LoginPage.tsx              # Page de connexion
│   │   │   ├── MultiSelectFilter.tsx      # Filtre multi-selection
│   │   │   ├── NotificationProvider.tsx   # Systeme de notifications
│   │   │   ├── OdooSyncPanel.tsx         # Synchronisation Odoo (config, sync, historique)
│   │   │   ├── PriceChart.tsx             # Graphique prix global
│   │   │   ├── ProcessingPage.tsx         # Traitement des donnees
│   │   │   ├── ProductAdmin.tsx           # Administration produits
│   │   │   ├── ProductEditModal.tsx       # Modale d'edition produit
│   │   │   ├── ProductEvolutionChart.tsx  # Graphique evolution produit
│   │   │   ├── ProductFilters.tsx         # Filtres produits
│   │   │   ├── ProductReference.tsx       # Referentiel produit
│   │   │   ├── ProductReferenceForm.tsx   # Formulaire referentiel
│   │   │   ├── ProductReferenceTable.tsx  # Table referentiel
│   │   │   ├── ProductTable.tsx           # Table produits
│   │   │   ├── ProductsPage.tsx           # Page produits principale
│   │   │   ├── ReferenceAdmin.tsx         # Admin tables de reference
│   │   │   ├── SearchControls.tsx         # Controles de recherche
│   │   │   ├── SearchPage.tsx             # Moteur de recherche
│   │   │   ├── StatisticsPage.tsx         # Statistiques de prix
│   │   │   ├── StatsFilters.tsx           # Filtres statistiques
│   │   │   ├── SupplierApiAdmin.tsx       # Admin API fournisseurs
│   │   │   ├── SupplierApiReports.tsx     # Rapports API
│   │   │   ├── SupplierApiSyncPanel.tsx   # Panel synchronisation
│   │   │   ├── SupplierPriceModal.tsx     # Modale prix fournisseur
│   │   │   ├── TranslationAdmin.tsx       # Admin traductions/couleurs
│   │   │   ├── UserAdmin.tsx              # Admin utilisateurs
│   │   │   └── WeekToolbar.tsx            # Barre d'outils hebdomadaire
│   │   ├── utils/
│   │   │   ├── date.ts          # Fonctions de date
│   │   │   ├── html.ts          # Generation HTML
│   │   │   ├── numbers.ts       # Utilitaires numeriques
│   │   │   ├── processing.ts    # Traitement et calculs
│   │   │   └── text.ts          # Normalisation de texte
│   │   ├── api.ts               # Client API centralise
│   │   ├── App.tsx              # Application principale et routeur
│   │   ├── main.tsx             # Point d'entree React
│   │   └── index.css            # Styles Tailwind
│   └── package.json
├── docker-compose.yml           # Services de base
├── docker-compose.override.yml  # Surcharges developpement
├── docker-compose.prod.yml      # Configuration production
├── Makefile                     # Commandes utilitaires
├── deploy.sh                    # Script de deploiement interactif
├── deploy-ci.sh                 # Script de deploiement CI/CD (non-interactif)
├── save_db.sh                   # Sauvegarde base de donnees
└── tips.md                      # Memo commandes Docker/Alembic
```

### Pile technique

| Couche | Technologies |
|--------|-------------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Lucide React, XLSX, Recharts |
| Backend | Python Flask, SQLAlchemy, PostgreSQL 16, Alembic, Gunicorn, Flasgger, Cryptography (Fernet) |
| Deploiement | Docker Compose (dev + prod), Nginx, script `deploy.sh` |
| Authentification | JWT (jetons d'acces + de rafraichissement) |

---

## Fonctionnalites disponibles

### Interface utilisateur

L'ensemble de l'application suit un design system coherent de type admin dashboard :

- **Navbar sticky** avec logo AJT Pro, liens de navigation style pill (fond dore quand actif) : Produits (1er, page par defaut pour non-clients) puis Moteur de recherche, menu deroulant Parametres avec separateur, responsive (icones seules sur mobile)
- **Layout centralise** : un unique wrapper `<main>` dans `App.tsx` porte les classes `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8`, identiques a celles du header. Toutes les pages heritent de ce conteneur, garantissant un alignement parfait navbar/contenu sur tous les breakpoints
- **Design system** : classes utilitaires `.card` (rounded-lg, backdrop-blur, shadow-xl, padding 15px, bordure doree `#B8860B/20`), `.btn` / `.btn-primary` / `.btn-secondary` (rounded-md), variables CSS pour les couleurs (bordures via `--color-border-subtle` et `--color-border-default`, sans modificateurs d'opacite), palette graphiques doree (#B8860B)
- **Pages structurees** : header avec icone doree + titre + description, onglets soulignes (border-b-2 doree), toolbar dans une card, contenu dans une card avec divide-y. Coherence appliquee sur toutes les pages (recherche, produits, statistiques, traitement, mise en forme, admin, synchro)
- **Theme Dark / Light** : theme sombre par defaut et theme clair. Bouton flottant en bas a droite. Choix persiste dans le `localStorage`

### Moteur de recherche

Permet d'explorer l'ensemble du catalogue fournisseurs avec :
- Recherche full-text avec suggestions et historique (par nom, description, marque, fournisseur, EAN, reference)
- Filtres avances : gamme de prix (curseur min/max), fournisseur, disponibilite stock, EAN, tri par prix
- Resultats affiches dans une card avec header (nombre de resultats, gamme selectionnee), hover sur chaque ligne, badge fournisseur colore et prix
- **Rafraichissement a la demande** : bouton "Rafraichir les catalogues" pour forcer le re-fetch de tous les catalogues fournisseurs configures (contourne le cache quotidien), avec spinner et notification de confirmation

### Administration

Accessible depuis le menu Parametres > Admin (role admin uniquement), avec 4 onglets :
- **Tables de reference** -- CRUD sur les marques, couleurs, options memoire, types d'appareils, options RAM, normes, exclusions, fournisseurs, format imports
- **Coherence des tables** -- Gestion des traductions de couleurs (mapping couleur source vers couleur cible)
- **API fournisseurs** -- Configuration des API fournisseurs : endpoints, champs de mapping, pagination, authentification
- **Utilisateurs** -- Creation et gestion des comptes avec roles (admin / client)

### Synchronisation fournisseurs

Accessible depuis le menu Parametres > Synchro (role admin uniquement), avec 4 onglets :
- **Synchronisation** -- Declenchement manuel des fetches API par fournisseur, suivi du statut en temps reel
- **Rapports** -- Historique des imports avec details (nombre de lignes, erreurs, doublons detectes)
- **Odoo** -- Synchronisation du referentiel produit avec Odoo 17 via XML-RPC
- **Rapprochement** -- Matching intelligent des produits fournisseurs avec le referentiel via extraction LLM (Claude Haiku)

### Synchronisation Odoo

Synchronisation automatique ou manuelle des produits depuis l'ERP Odoo 17 :
- **Configuration** dans l'interface (URL, base de donnees, identifiants, toggle visibilite mot de passe). Le mot de passe est chiffre en base avec Fernet (AES-128-CBC + HMAC)
- **Test de connexion** avant synchronisation (version serveur, nombre de produits)
- **Mapping complet** : nom, EAN, reference, prix, marque, couleur, memoire, RAM, type, norme
- **Extraction du nom de modele** : le nom complet Odoo est stocke dans `description` et le nom de modele epure (sans marque, couleur, memoire, RAM, norme) est extrait dans `model` via suppression par word boundaries (ex: "Apple iPhone 15 128GB Black" → model "iPhone 15", description "Apple iPhone 15 128GB Black")
- **Parsing intelligent des noms** : quand les attributs Odoo sont absents, les champs (marque, couleur, memoire, RAM, norme, type) sont extraits automatiquement du nom du produit par substring matching contre les tables de reference. Les synonymes de couleurs (ColorTranslation) sont pris en compte. Le match le plus long est prioritaire (ex: "Bleu Nuit" avant "Bleu")
- **Creation automatique** des references manquantes (marques, couleurs, types, etc.)
- **Synchronisation automatique** configurable (intervalle minimum 15 min)
- **Historique** des jobs avec rapports detailles expansibles
- **Suppression des orphelins** : les produits lies a Odoo mais absents de la synchronisation sont supprimes physiquement (references fournisseurs detachees). Compteur et rapport detaille visibles dans l'historique

Variable d'environnement : `ENABLE_ODOO_SCHEDULER=true` pour activer le planificateur automatique (desactive par defaut)

### Rapprochement LLM

Module de matching intelligent qui utilise Claude Haiku (Anthropic) pour associer les produits fournisseurs non matches au referentiel produit :

- **Extraction d'attributs** : le LLM extrait marque, modele, stockage, couleur, type d'appareil, region et connectivite depuis les libelles fournisseurs
- **Scoring multicritere** : score /100 base sur la marque (15), le modele (40, fuzzy matching), le stockage (25), la couleur (15) et la region (5)
- **3 niveaux d'action** : score >= 90 = match automatique, 50-89 = validation manuelle, < 50 = creation produit automatique
- **Lotissement (limit)** : le rapprochement peut etre lance par lots (50, 100, 200 ou tous) pour eviter les timeouts sur les grands catalogues. Le rapport indique le nombre de produits restants a traiter
- **Integration TCP/marges** : les produits matches par LLM sont automatiquement pris en compte dans le calcul des prix (TCP, marges, prix de vente) via un fallback LabelCache dans le moteur de calcul. Les produits sans marque (crees automatiquement par le LLM) sont egalement inclus dans les vues prix et statistiques
- **Gestion d'erreurs explicite** : verification de la cle API Anthropic avant traitement, messages d'erreur specifiques (cle invalide, rate limit, connexion reseau, erreur API), rapport d'erreurs visible dans l'interface avec bandeau d'avertissement
- **Robustesse des calculs** : protection NaN/Inf sur toutes les valeurs numeriques, try-except par produit dans le moteur de calcul pour eviter qu'un produit en erreur ne bloque tout le traitement
- **Cache de labels** : les resultats sont caches par fournisseur/libelle pour eviter les appels LLM redondants lors des syncs suivantes
- **Table de correspondance** : codes constructeur Samsung (SM-S938B -> Galaxy S25 Ultra, etc.) et traductions couleurs (Midnight -> Noir, etc.)
- **Interface de validation** : les matchs en attente sont presentes avec les attributs extraits, les candidats avec barre de score, et les boutons Valider/Creer/Ignorer

Pre-requis : creer un compte Anthropic, generer une cle API et ajouter `ANTHROPIC_API_KEY` dans le fichier `.env`. Cout estime : < 0.30€ par sync de 3000 produits.

### Authentification

- Page de connexion avec logo AJT Pro, champs avec icones et labels, toggle visibilite mot de passe (icone oeil)
- Jetons JWT (acces + rafraichissement)
- Acces conditionnel selon le role (admin / client)

### CI/CD

Le projet dispose d'un pipeline GitHub Actions complet :

- **CI** (`.github/workflows/ci.yml`) : tests frontend (Vitest) et backend (pytest) executes en parallele sur chaque push et pull request vers `main`. Un recap des resultats (tests passes/echoues) est affiche dans le Job Summary de chaque job. Le secret JWT de test fait 32+ octets pour eviter les warnings `InsecureKeyLengthWarning`.
- **Deploy** (`.github/workflows/deploy.yml`) : deploiement automatique sur le VPS via SSH apres chaque push sur `main`. Le pipeline lance directement le deploy SSH sans job de build intermediaire (le build frontend est fait dans le Dockerfile). Le script `deploy-ci.sh` est optimise pour un deploy en ~1 minute : layer caching Docker, build avant arret des containers (downtime ~5-10s), polling actif au lieu d'attente fixe.

### Referentiel produit

Page par defaut pour les utilisateurs non-clients. Tableau complet du referentiel produit accessible depuis l'onglet "Produits" (role admin uniquement). Permet de :
- Consulter, filtrer et rechercher l'ensemble des produits du referentiel
- Editer les produits directement dans le tableau (marque, couleur, memoire, type, RAM, norme)
- Creer de nouveaux produits via le formulaire integre
- Supprimer des produits individuellement ou en masse
- Configurer les colonnes visibles et la pagination

### Fonctionnalites en cours de developpement

Les fonctionnalites suivantes sont codees mais pas encore exposees dans la navigation. Voir [ROADMAP.md](ROADMAP.md) pour le detail.

---

## Scripts utilitaires

### Makefile

Les commandes principales du Makefile sont les suivantes :

| Commande | Description |
|----------|-------------|
| `make docker-build` | Construire les images Docker |
| `make docker-up` | Demarrer les services |
| `make docker-down` | Arreter les services |
| `make docker-logs SERVICE=x` | Afficher les logs d'un service |
| `make shell-postgres` | Ouvrir un shell psql dans le conteneur PostgreSQL |
| `make alembic-migrate MSG="message"` | Creer une nouvelle migration |
| `make alembic-upgrade` | Appliquer les migrations en attente |
| `make alembic-downgrade` | Annuler la derniere migration |
| `make alembic-current` | Afficher la revision courante |
| `make alembic-history` | Afficher l'historique des migrations |
| `make import-reference-products CSV=chemin [DELIMITER=';'] [DEFAULT_TCP=0]` | Importer un referentiel produit depuis un CSV |
| `make clean-branches` | Nettoyer les branches locales fusionnees |

Il est aussi possible de cibler un service specifique pour `docker-build`, `docker-up` et `docker-down` en ajoutant `SERVICE=nom_du_service`.

### deploy.sh

Script de deploiement interactif pour l'environnement de production. Il orchestre la construction des images, l'application des migrations et le redemarrage des conteneurs.

```bash
./deploy.sh
```

### deploy-ci.sh

Script de deploiement non-interactif utilise par GitHub Actions. Optimise pour un deploy en ~1 minute : layer caching Docker, build avant arret des containers (downtime ~5-10s), polling actif pour les health checks.

### save_db.sh

Script de sauvegarde et de restauration de la base de donnees PostgreSQL. Voir la section dediee ci-dessous.

---

## Migrations Alembic

Le projet utilise Alembic pour versionner le schema de la base de donnees. Les fichiers de migration se trouvent dans `backend/alembic/`.

```bash
# Creer une nouvelle migration a partir des modifications des modeles
make alembic-migrate MSG="description de la migration"

# Appliquer toutes les migrations en attente
make alembic-upgrade

# Annuler la derniere migration
make alembic-downgrade

# Verifier la revision courante de la base
make alembic-current

# Afficher l'historique complet des migrations
make alembic-history
```

---

## Sauvegarde et restauration de la base

Le script `save_db.sh` permet de sauvegarder et de restaurer la base de donnees PostgreSQL.

```bash
# Sauvegarder la base
./save_db.sh

# Restaurer une sauvegarde (consulter le script pour les options disponibles)
./save_db.sh restore
```

---

## Documentation API

Une documentation interactive Swagger est generee automatiquement grace a Flasgger. Une fois le backend demarre, elle est accessible a l'adresse suivante :

```
http://localhost:5001/apidocs
```

Le gabarit OpenAPI se trouve dans `backend/swagger_template.yml`.

---

## Verifications locales

### Tests backend

Le framework `pytest` est configure dans le backend (SQLite in-memory, pas besoin de PostgreSQL) — 176 tests dans 12 fichiers :

```bash
cd backend
pip install -r requirements.txt
python -m pytest tests/ -v
```

### Tests frontend

Le framework `vitest` avec Testing Library est configure dans le frontend — 127 tests dans 13 fichiers :

```bash
cd frontend
npm install
npm test          # execution unique
npm run test:watch  # mode watch
```

### Lint frontend

Apres avoir installe les dependances, executez le linter :

```bash
cd frontend
npm run lint
```

### Build frontend

Pour verifier que le frontend compile sans erreur :

```bash
cd frontend
npm run build
```

### Validation Docker

Pour verifier que l'ensemble de la pile demarre correctement :

```bash
make docker-build
make docker-up
# Verifier les logs
make docker-logs SERVICE=backend
make docker-logs SERVICE=frontend
```
