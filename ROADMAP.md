# Roadmap AJT PRO

Ce document recense les fonctionnalites prevues pour les prochaines versions. Le code backend et frontend existe deja pour la plupart de ces modules ; il reste a les activer dans la navigation et a les valider en conditions reelles.

---

## Tableau referentiel produit (implementee)

Mise a disposition d'un tableau complet du referentiel produit avec :

- **Filtres multi-selection** sur chaque colonne de reference : marque, couleur, memoire, type d'appareil, RAM, norme
- **Recherche textuelle** sur le modele et la description
- **Edition inline** de chaque produit directement dans le tableau (modification de la marque, couleur, memoire, type, RAM, norme)
- **Creation de produits** via un formulaire dedie (modele, description, EAN, marque, couleur, memoire, type, RAM, norme)
- **Suppression** individuelle et en masse (selection multiple avec checkbox)
- **Import CSV** pour alimentation en masse du referentiel
- **Colonnes visibles configurables** (affichage/masquage par colonne)
- **Pagination configurable** (nombre de lignes par page)

Composants concernes : `ProductReference`, `ProductReferenceTable`, `ProductReferenceForm`

---

## Tableau des calculs de prix

Tableau croise affichant pour chaque produit les prix d'achat et de vente par fournisseur :

- **Prix d'achat (PA)** par fournisseur avec colonne dediee
- **Prix de vente** calcule selon la grille de marges (TCP, commission 4.5 %, multiplicateurs par seuil)
- **Marge** affichee en valeur absolue et en pourcentage
- **Edition inline des prix** avec sauvegarde en masse
- **Modification de marge en masse** sur une selection de produits
- **Detail par fournisseur** via une modale dediee (historique des prix, stock, derniere mise a jour)
- **Edition complete d'un produit** via modale (modele, description, marque, couleur, memoire, type, RAM, norme)
- **Export Excel** du tableau filtre avec horodatage
- **Navigation par semaine** (barre d'outils hebdomadaire)
- **Vue client** simplifiee (colonnes reduites : prix de vente, modele, description uniquement)

Composants concernes : `ProductsPage`, `ProductTable`, `ProductFilters`, `ProductEditModal`, `SupplierPriceModal`, `WeekToolbar`

---

## Synchronisation API fournisseurs (implementee)

Page dediee a l'import et au suivi des donnees fournisseurs, accessible depuis Parametres > Synchro :

- **Panel de synchronisation** : declenchement manuel des fetches API par fournisseur, suivi du statut en temps reel
- **Rapports de synchronisation** : historique des imports avec details (nombre de lignes, erreurs, doublons detectes)
- **Import de fichiers Excel** avec apercu avant validation
- **Calcul automatique** des prix de vente apres import

Composants concernes : `DataImportPage`, `SupplierApiSyncPanel`, `SupplierApiReports`, `ProcessingPage`, `ImportPreviewModal`

---

## Statistiques fournisseurs (v2 — implementee)

Module d'analyse graphique recentre sur les donnees brutes du catalogue fournisseur (`supplier_catalog`) avec 4 visualisations claires :

| Graphique | Source | Description |
|-----------|--------|-------------|
| Prix moyen par fournisseur | `supplier_catalog` | Prix de vente moyen de chaque fournisseur (BarChart gold) |
| Evolution des prix par fournisseur | `product_calculations` | Prix moyen par fournisseur par semaine avec legendes couleur (MultiLineChart) |
| Nombre de produits par fournisseur | `supplier_catalog` | Nombre de references dans le catalogue de chaque fournisseur (BarChart gold) |
| Repartition des prix | `supplier_catalog` | Distribution des prix par tranche, comparee entre fournisseurs (GroupedBarChart) |

Fonctionnalites :
- **Filtres simplifies** : fournisseur optionnel + plage de semaines (pour l'evolution uniquement)
- **Legendes** sous les graphiques multi-series (nom fournisseur + pastille couleur)
- **4 endpoints API** : `/supplier_avg_price`, `/supplier_product_count`, `/supplier_price_distribution`, `/supplier_price_evolution`

Composants concernes : `StatisticsPage`, `StatsFilters`

---

## Mise en forme et export

Traitement des fichiers Excel fournisseurs pour generation de documents prets a l'envoi :

- **Import d'un fichier Excel** fournisseur brut
- **Nettoyage et mise en forme** automatique des donnees
- **Apercu** des donnees traitees avec recherche et filtres
- **Export Excel** du fichier formate
- **Generation HTML** pour apercu navigateur

Composants concernes : `FormattingPage`

---

## Redesign UX admin dashboard (implementee)

Refonte complete de l'interface utilisateur avec un design system coherent sur toutes les pages.

- **Navbar** : logo AJT Pro, liens de navigation style pill (fond dore quand actif) : Produits (1er, page par defaut pour non-clients) puis Moteur de recherche, menu deroulant Parametres anime avec separateur, responsive mobile (icones seules), sticky avec backdrop-blur
- **Design system** : classes `.card` (rounded-lg, backdrop-blur, shadow-xl, padding 15px), `.btn` / `.btn-primary` / `.btn-secondary` (rounded-md), variables CSS pour tous les etats
- **Pages structurees** : header avec icone doree + titre + description, onglets soulignes (border-b-2 doree), toolbar dans une card, contenu dans une card avec divide-y et hover
- **Page connexion** : card centree avec logo AJT Pro, labels, icones dans les inputs (Mail, Lock), toggle visibilite mot de passe (Eye/EyeOff), etat loading
- **Moteur de recherche** : barre de recherche dans une card, resultats dans une card avec header et separateurs, dropdown suggestions avec z-index corrige
- **Page Produits** : onglets TCP/Marges et Referentiel, toolbar regroupee dans une card, pagination compacte avec chevrons
- **Administration** : 4 onglets (Tables reference, Coherence, API fournisseurs, Utilisateurs), suppression du bouton Retour
- **Synchronisation** : accessible via Parametres > Synchro, header avec icone, 2 onglets (Synchronisation, Rapports)
- **Statistiques** : header avec icone, filtres dans une card, chaque graphique dans une card, couleur primaire doree (#B8860B), table anomalies stylisee
- **Calculs et Traitement** : header avec icone, zones d'import dans des cards, boutons design system
- **Mise en Forme** : header avec icone, zone de telechargement dans une card, previsualisation dans une card, boutons homogenes
- **API fournisseurs** : messages d'erreur avec variables CSS, textes muted uniformises, bordure doree `#B8860B/20` sur les conteneurs API (coherence `.card`), suppression des modificateurs d'opacite `/60` sur `border-subtle` (fallback blanc en dark mode)
- **Arrondis reduits** : cards rounded-lg (8px), boutons/inputs rounded-md (6px) pour un rendu plus professionnel
- **Layout centralise** : wrapper `<main>` unique dans `App.tsx` avec `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8`, suppression des wrappers individuels dans chaque page pour garantir un alignement parfait navbar/contenu

Fichiers concernes : `App.tsx`, `LoginPage.tsx`, `SearchPage.tsx`, `SearchControls.tsx`, `ProductsPage.tsx`, `AdminPage.tsx`, `DataImportPage.tsx`, `ReferenceAdmin.tsx`, `TranslationAdmin.tsx`, `UserAdmin.tsx`, `SupplierApiAdmin.tsx`, `StatisticsPage.tsx`, `StatsFilters.tsx`, `FormattingPage.tsx`, `ProcessingPage.tsx`, `index.css`

---

## Theme Dark / Light (implementee)

Systeme de theme sombre et clair avec basculement dynamique.

- **ThemeProvider** : contexte React + hook `useTheme()` pour acceder au theme courant et au toggle
- **Persistance** : choix sauvegarde dans `localStorage` (cle `ajtpro_theme`, defaut : `dark`)
- **Variables CSS** : 22 variables definies dans `index.css` (`:root` = light, `.dark` = dark) couvrant backgrounds, textes, bordures et graphiques
- **Bouton flottant** : icone Soleil/Lune (lucide-react) en bas a droite de l'ecran
- **Anti-flash** : script inline dans `index.html` pour appliquer le theme avant le premier rendu

Composant concerne : `ThemeProvider`

---

## Synchronisation Odoo (implementee)

Synchronisation du referentiel produit avec l'ERP Odoo 17 via API XML-RPC :

- **Configuration** : URL, base de donnees, identifiants Odoo, configurable depuis l'interface. Mot de passe chiffre en base avec Fernet (AES-128-CBC + HMAC)
- **Test de connexion** : verification de la connexion avec affichage version serveur et nombre de produits
- **Mapping complet** : nom, EAN, reference interne, prix, marque, couleur, memoire, RAM, type, norme
- **Extraction du nom de modele** : le nom complet Odoo est conserve dans `description` ; le nom de modele epure (sans marque, couleur, memoire, RAM, norme) est extrait automatiquement dans `model` par suppression avec word boundaries regex (ex: "Apple iPhone 15 128GB Black" → model "iPhone 15")
- **Parsing intelligent des noms** : extraction automatique des champs de reference (marque, couleur, memoire, RAM, norme, type) depuis le nom du produit quand les attributs Odoo sont absents. Utilise le substring matching contre les tables de reference avec priorite au match le plus long. Supporte les synonymes de couleurs via ColorTranslation
- **Creation automatique** des references manquantes (marques, couleurs, etc.)
- **Rapports detailles** : produits crees, mis a jour, inchanges, supprimes, erreurs
- **Suppression des orphelins** : les produits lies a Odoo mais absents de la synchronisation sont supprimes physiquement (references fournisseurs detachees, calculs supprimes). Compteur orange et rapport detaille dans l'historique
- **Synchronisation manuelle** : bouton de declenchement dans l'interface
- **Synchronisation automatique** : planificateur configurable (intervalle minimum 15 min)
- **Historique** : suivi de tous les jobs de synchronisation avec rapports expansibles

Composants concernes : `OdooSyncPanel`, `DataImportPage`

---

## Rapprochement LLM (implementee)

Module de matching intelligent qui utilise Claude Haiku (Anthropic) pour associer les produits fournisseurs non matches au referentiel :

- **Extraction d'attributs par IA** : envoi des libelles fournisseurs par lots de 25 a Claude Haiku, extraction structuree (marque, modele, stockage, couleur, type, region, connectivite, grade, confidence)
- **Normalisation et cache** : chaque libelle est normalise puis mis en cache par fournisseur. Les syncs suivantes reutilisent le cache sans appel LLM
- **Scoring multicritere** : score sur 100 base sur 5 axes ponderes (marque 15, modele 40 avec fuzzy matching, stockage 25, couleur 15, region 5). Brand ou stockage mismatch = disqualification immediate
- **3 niveaux d'action** :
  - Score >= 90 : match automatique (creation `SupplierProductRef` + cache)
  - Score 50-89 : validation manuelle (creation `PendingMatch`)
  - Score < 50 : creation automatique du produit dans le referentiel
- **Table de correspondance** : codes constructeur Samsung (SM-S938B -> Galaxy S25 Ultra, etc.) et 24 traductions de couleurs (Midnight -> Noir, Starlight -> Blanc, etc.)
- **Gestion d'erreurs explicite** : verification de la cle API avant traitement (retour HTTP 400), catches specifiques Anthropic (authentification, rate limit, connexion, erreur API), message d'erreur remonte dans le rapport et affiche dans l'interface (bandeau rouge avec icone d'avertissement)
- **Interface de validation** : onglet "Rapprochement" dans la page Synchro avec declenchement par fournisseur, rapport resume (incluant compteur d'erreurs), liste des matchs en attente avec badges attributs, barres de score et boutons Valider/Creer/Ignorer
- **Statistiques** : taux de cache hit, nombre de matchs en attente, repartition auto/manual par fournisseur
- **Integration TCP/marges** : les produits rapproches par LLM apparaissent automatiquement dans le tableau des calculs de prix. Le moteur de calcul (`recalculate_product_calculations`) consulte le `LabelCache` en fallback apres les matchs EAN et Model. Les identifiants EAN et part_number sont copies dans `SupplierProductRef` lors de la validation ou creation. Les produits sans marque (crees par le LLM) sont inclus grace a des `outerjoin` sur Brand
- **Lotissement (limit)** : parametre `limit` sur `run_matching_job` pour traiter les produits par lots (50, 100, 200 ou tous). Evite les timeouts 504 nginx/gunicorn sur les grands catalogues. Le rapport inclut `remaining` pour que l'utilisateur sache combien de produits restent a traiter. Selecteur de limite visible dans l'interface
- **7 endpoints API** : run, pending, validate, reject, stats, cache, delete cache

Modeles ajoutes : `ModelReference`, `LabelCache`, `PendingMatch`. Colonne `region` ajoutee sur `Product` et `SupplierCatalog` (anciennement `TemporaryImport`).

Pre-requis : cle API Anthropic (`ANTHROPIC_API_KEY` dans `.env`). Cout estime : < 0.30€ par sync de 3000 produits.

Composants concernes : `MatchingPanel`, `DataImportPage`

---

## Corrections de stabilite production (implementee)

Corrections de 3 erreurs en production :

- **Fix 504 matching timeout** : ajout du parametre `limit` pour traiter les produits par lots au lieu de tout traiter d'un coup. Selecteur dans l'interface (50/100/200/Tous) avec affichage du nombre restant
- **Fix 500 `/calculate_products`** : correction du crash `product.memory.memory.upper()` quand `.memory` est None, ajout de `_is_invalid()` pour verifier NaN et Inf sur toutes les valeurs, remplacement de `print()` par `logger.warning()`, enveloppement de chaque produit dans un try-except pour eviter qu'une erreur ne bloque tout le calcul
- **Fix 500 `/product_price_summary`** : ajout de `_safe_float()` pour coercer les NaN/Inf en 0 dans les valeurs de calcul, protection `p is None: continue`, try-except sur la route `/calculate_products` avec retour 500 explicite

Fichiers concernes : `backend/utils/calculations.py`, `backend/routes/products.py`, `backend/routes/matching.py`, `backend/utils/llm_matching.py`, `frontend/src/api.ts`, `frontend/src/components/MatchingPanel.tsx`

---

## Optimisation du deploiement (implementee)

Reduction du temps de deploiement de ~3 minutes a ~1 minute via plusieurs optimisations :

- **Layer caching Docker** : suppression du flag `--no-cache` pour reutiliser les couches de dependances (`pip install`, `npm ci`) quand elles n'ont pas change
- **Suppression du build frontend redondant** : le `npm ci && npm run build` etait execute sur le VPS puis refait dans le Dockerfile. Seul le build Docker est conserve
- **Reduction du downtime** : les images sont buildees AVANT l'arret des containers (downtime reduit a ~5-10s)
- **Polling actif** : remplacement du `sleep 30` par une boucle de polling (curl toutes les 2s, max 30 tentatives) pour les health checks et migrations
- **Pipeline GitHub simplifie** : suppression du job `build` dans `deploy.yml` qui installait et buildait le frontend sur le runner GitHub sans utiliser le resultat
- **Dockerfile frontend simplifie** : suppression des diagnostics (`echo`, `ls`, `find`, `tree`), des retries Rollup et des tentatives de downgrade Vite. Combinaison des `RUN` pour reduire les couches Docker

Fichiers concernes : `deploy-ci.sh`, `.github/workflows/deploy.yml`, `frontend/Dockerfile`

---

## Tests automatises (implementee)

Infrastructure de tests unitaires et d'integration pour le backend et le frontend, integree dans la CI GitHub Actions.

### Backend (pytest)

- **Infrastructure** : SQLite in-memory, fixtures `admin_user`, `client_user`, `admin_headers`
- **Tests unitaires** : `utils/pricing.py` (seuils, TCP, marges, edge cases), `utils/auth.py` (JWT generation, decodage, expiration, decorator)
- **Tests d'integration** : routes `POST /login`, CRUD `/users`, CRUD `/products`, operations en masse (`bulk_update`, `bulk_delete`), routes Odoo (config, test connexion, sync, jobs, auto-sync)
- **Tests LLM matching** : modeles (13 tests), extraction et scoring (33 tests), routes API (24 tests), integration calculs/LabelCache (5 tests)
- **176 tests** dans 12 fichiers
- **Zero warning applicatif** : `datetime.utcnow()` remplace par `datetime.now(timezone.utc)`, `Query.get()` remplace par `db.session.get()`, secret JWT >= 32 octets

### Frontend (Vitest + Testing Library)

- **Tests utils** : `date.ts`, `numbers.ts`, `text.ts`, `processing.ts`, `html.ts` (fonctions pures)
- **Tests composants** : `LoginPage`, `NotificationProvider`, `App` (rendu, formulaires, navigation conditionnelle)
- **Tests composants** : `MatchingPanel` (render, run matching avec limit, validation, rejet, remaining, pagination)
- **127 tests** dans 13 fichiers

### CI/CD

- Jobs `frontend` et `backend` parallelises dans `.github/workflows/ci.yml`
- Tests executes automatiquement sur chaque push et pull request vers `main`
- **Job Summary** : recap des resultats (tests passes/echoues) affiche dans l'onglet Actions de GitHub
- **Deploy** (`.github/workflows/deploy.yml`) : deploiement automatique sur le VPS via SSH apres chaque push sur `main`

---

## Renommage supplier_catalog + refresh a la demande (implementee)

Renommage de la table `temporary_imports` en `supplier_catalog` pour mieux refleter son role de cache des catalogues fournisseurs, et ajout d'un bouton de refresh manuel.

- **Migration Alembic** : renommage table, sequence, PK, index unique, 7 FK et 1 FK referente (`pending_matches`)
- **Modele SQLAlchemy** : `TemporaryImport` → `SupplierCatalog`, backrefs mis a jour
- **Backend** : toutes les references mises a jour dans `routes/products.py`, `routes/matching.py`, `utils/etl.py`, `utils/calculations.py`, `utils/llm_matching.py`
- **Nouvelle route** : `POST /supplier_catalog/refresh` — force le re-fetch de tous les catalogues fournisseurs configures, contourne le check quotidien
- **Frontend** : bouton "Rafraichir les catalogues" sur SearchPage avec spinner et toast de confirmation
- **Tests** : 2 nouveaux tests pour la route refresh, references mises a jour dans 4 fichiers de tests existants
- **Documentation** : ARCHITECTURE.md, api_supplier_sync.md, LLM.md, fonctionnalites_app.md, ROADMAP.md mis a jour

Fichiers concernes : `backend/models.py`, `backend/routes/products.py`, `backend/routes/matching.py`, `backend/utils/etl.py`, `backend/utils/calculations.py`, `backend/utils/llm_matching.py`, `frontend/src/api.ts`, `frontend/src/components/SearchPage.tsx`
