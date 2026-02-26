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

Composants concernes : `SyncPage`, `SupplierApiSyncPanel`, `SupplierApiReports`, `ImportPreviewModal`

---

## Statistiques fournisseurs (v2 — implementee)

Module d'analyse graphique recentre sur les donnees brutes du catalogue fournisseur (`supplier_catalog`) avec 4 visualisations claires :

| Graphique | Source | Description |
|-----------|--------|-------------|
| Prix moyen par fournisseur | `supplier_catalog` | Prix de vente moyen de chaque fournisseur (BarChart gold) |
| Evolution des prix par fournisseur | `product_calculations` | Prix moyen par fournisseur par semaine avec legendes couleur (MultiLineChart) |
| Nombre de produits par fournisseur | `supplier_catalog` | Nombre de references dans le catalogue de chaque fournisseur (BarChart gold) |
| Repartition des prix | `supplier_catalog` | Distribution des prix par tranche, comparee entre fournisseurs (GroupedBarChart) |
| Comparaison prix produit par fournisseur | `product_calculations` | Prix moyen d'un produit specifique compare entre fournisseurs au fil des semaines (MultiLineChart, visible quand un produit est selectionne) |

Fonctionnalites :
- **Filtres** : fournisseur optionnel, produit optionnel + plage de semaines (pour l'evolution uniquement)
- **Legendes** sous les graphiques multi-series (nom fournisseur + pastille couleur)
- **4 endpoints API** : `/supplier_avg_price`, `/supplier_product_count`, `/supplier_price_distribution`, `/supplier_price_evolution` (supporte filtre `product_id`)

Composants concernes : `StatisticsPage`, `StatsFilters`

---

## Mise en forme et export

Traitement des fichiers Excel fournisseurs pour generation de documents prets a l'envoi :

- **Import d'un fichier Excel** fournisseur brut
- **Nettoyage et mise en forme** automatique des donnees
- **Apercu** des donnees traitees avec recherche et filtres
- **Export Excel** du fichier formate
- **Generation HTML** pour apercu navigateur

Composants concernes : `ProductsPage` (export integre)

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

Fichiers concernes : `App.tsx`, `LoginPage.tsx`, `SearchPage.tsx`, `SearchControls.tsx`, `ProductsPage.tsx`, `AdminPage.tsx`, `SyncPage.tsx`, `ReferenceAdmin.tsx`, `TranslationAdmin.tsx`, `UserAdmin.tsx`, `SupplierApiAdmin.tsx`, `StatisticsPage.tsx`, `StatsFilters.tsx`, `index.css`

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

Composants concernes : `OdooSyncPanel`, `SyncPage`

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

Modeles ajoutes : `ModelReference`, `LabelCache`, `PendingMatch`, `ProductEanHistory`. Colonne `region` ajoutee sur `Product` et `SupplierCatalog` (anciennement `TemporaryImport`).

- **Historique EAN par produit** : table `product_ean_history` pour tracker les associations EAN→produit au fil du temps. Chaque run de matching (auto ou manuel) log l'EAN associe avec le fournisseur, le run et la source (`auto_match`, `manual_validation`, `manual_reject_create`). Pas d'unicite : les doublons sont voulus pour tracer l'evolution. Index sur `(product_id, ean)` pour les requetes rapides. Affichage UI a venir.

Pre-requis : cle API Anthropic (`ANTHROPIC_API_KEY` dans `.env`). Cout estime : < 0.30€ par sync de 3000 produits.

Composants concernes : `MatchingPanel`, `SyncPage`

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
- **319 tests** dans 16 fichiers
- **Zero warning applicatif** : `datetime.utcnow()` remplace par `datetime.now(timezone.utc)`, `Query.get()` remplace par `db.session.get()`, secret JWT >= 32 octets

### Frontend (Vitest + Testing Library)

- **Tests utils** : `date.ts`, `numbers.ts`, `text.ts`, `processing.ts`, `html.ts` (fonctions pures)
- **Tests composants** : `LoginPage`, `NotificationProvider`, `App` (rendu, formulaires, navigation conditionnelle)
- **Tests composants** : `MatchingPanel` (render, run matching avec limit, validation, rejet, remaining, pagination)
- **186 tests** dans 18 fichiers

### CI/CD

- Jobs `frontend` et `backend` parallelises dans `.github/workflows/ci.yml`
- Tests executes automatiquement sur chaque push et pull request vers `main`
- **Job Summary** : recap des resultats (tests passes/echoues) affiche dans l'onglet Actions de GitHub
- **Deploy** (`.github/workflows/deploy.yml`) : deploiement automatique sur le VPS via SSH apres chaque push sur `main`

---

## Systeme de logs centralise (implementee)

Systeme de logging structure et tracabilite des operations metier, consultable depuis l'interface admin sans SSH.

- **Logging applicatif** : `RotatingFileHandler` JSON (10 Mo, 5 backups) + console handler lisible, niveau configurable via `LOG_LEVEL`
- **Table activity_logs** : enregistrement des operations metier (login, matching, import, calculs, sync Odoo, suppression) avec action, categorie, utilisateur, details JSON et adresse IP
- **Helper log_activity** : fonction centralisee appelee dans les routes (auth, matching, products, odoo, imports), categorie derivee automatiquement du prefixe d'action
- **API logs** : `GET /logs/activity` (pagine, filtrable par categorie/action) + `GET /logs/app` (dernières N lignes du fichier de log)
- **Interface admin** : 5e onglet "Logs" dans Administration, 2 sous-onglets :
  - Historique d'activite : tableau pagine avec badges colores par categorie, filtre par categorie, bouton rafraichir
  - Logs application : affichage monospace avec coloration par niveau (ERROR rouge, WARNING jaune, DEBUG gris)
- **Nettoyage ETL** : suppression du systeme de log maison (`_TEMP_IMPORT_LOG_FILENAME`, `_resolve_temp_import_log_path`, `_append_temp_import_log_entry`) remplace par `logger.info`
- **Docker prod** : volume `ajtpro_backend_logs` pour persister les logs entre redemarrages
- **Tests** : 11 tests backend (routes logs) + 9 tests frontend (LogsPanel)

Fichiers concernes : `backend/utils/logging_config.py`, `backend/utils/activity.py`, `backend/routes/logs.py`, `backend/models.py`, `backend/app.py`, `backend/routes/auth.py`, `backend/routes/matching.py`, `backend/routes/products.py`, `backend/routes/odoo.py`, `backend/routes/imports.py`, `backend/utils/etl.py`, `frontend/src/api.ts`, `frontend/src/components/LogsPanel.tsx`, `frontend/src/components/AdminPage.tsx`

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

---

## Affinement du matching LLM — regles de disqualification et coherence (implementee)

Serie d'ameliorations du moteur de matching LLM pour augmenter la couverture et reduire les faux positifs :

- **Direction product-centric** : inversion du sens de matching. Le moteur itere sur les **produits Odoo** non matches (plutot que sur les labels catalogue), ce qui garantit que chaque produit est traite une fois et permet une couverture exhaustive du referentiel
- **Suppression de la contrainte 1:1 cache→produit** : un meme label catalogue peut maintenant matcher plusieurs produits Odoo distincts (ex: meme iPhone 15 chez deux fournisseurs differents)
- **Auto-rejet sur hard disqualifiers** : quand tous les candidats d'un produit declenchent un disqualificateur (marque, couleur, stockage, region), un `PendingMatch(status='rejected')` est cree automatiquement pour traçabilite, sans laisser le produit silencieusement non traite
- **Regle both-sides-non-null pour le stockage** : le stockage disqualifie uniquement quand les deux cotes ont une valeur identifiable — champ `memory` officiel Odoo OU stockage lisible dans le nom du modele. Un seul cote avec stockage = 0 pts, pas de disqualification
- **Bouton valider dans la vue Rejetes** : un admin peut corriger un auto-rejet en validant manuellement le match depuis la vue statut=rejected. Le backend accepte `status in ('pending', 'rejected')` dans la route validate
- **Arret automatique du polling** : le suivi de progression s'arrete automatiquement quand `total_processed` reste stable 2 polls consecutifs (~10s apres la fin du job), plutot que d'attendre 10 minutes dans tous les cas
- **Coherence stat total_odoo_matched** : le compteur "produits Odoo matches" utilise desormais `COUNT(DISTINCT ProductCalculation.product_id)` — coherent avec ce qu'affiche TCP/Marges (80 produits) plutot que `SupplierProductRef.product_id` (uniquement les validations LLM manuelles)

Fichiers concernes : `backend/utils/llm_matching.py`, `backend/tests/test_llm_matching.py`, `backend/routes/matching.py`, `frontend/src/components/MatchingPanel.tsx`

---

## Restauration clic sur lignes TCP/Marges (implementee)

Le clic sur une ligne du tableau TCP/Marges (role admin/user) rouvre la modale `SupplierPriceModal` avec le detail des prix par fournisseur et la possibilite d'editer la marge. Fonctionnalite supprimee par erreur lors du refactor read-only, restauree avec `onRowClick` prop sur `ProductTable`.

Fichiers concernes : `frontend/src/components/ProductTable.tsx`, `frontend/src/components/ProductsPage.tsx`

---

## Documentation des vues (implementee)

Ajout de `docs/VUES.md` : documentation exhaustive de chaque vue de l'application (source de donnees, endpoints utilises, actions disponibles, points de coherence et risques).

Fichier cree : `docs/VUES.md`

---

# Prochaines etapes

## ~~1. Ameliorations vue Rapprochement LLM~~ (implementee)
- ~~ajouter pagination en bas de page~~
- ~~ajouter un filtre par statut (pending, validated, rejected, created)~~
- ~~quand on valide un produit, pas remonter en haut de page mais rester sur la meme endroit de la page~~
- ~~quand on rejette un produit, pas remonter en haut de page mais rester sur la meme endroit de la page~~
- ~~ajouter un filtre par modele de produit~~

## ~~2. Ajouter un systeme de logs pour le backend~~ (implementee)
## ~~3. Meilleures gestions de toutes les filtres des tableaux~~ (implementee)
- ~~Filtre ascendant/descendant~~
- ~~choix case a cocher par colonne~~
- ~~pouvoir taper dans les filtres pour choisis (comme dans excel)~~

## Filtres Excel pour tableaux (implementee)

Ajout de fonctionnalites de filtrage et tri avances type Excel sur les tableaux Produits et Referentiel :

- **Tri ascendant/descendant** par colonne : clic sur l'en-tete pour trier (cycle : aucun → ascendant → descendant → aucun). Icone doree quand un tri est actif, icone grisee par defaut
- **Recherche textuelle dans les filtres multi-selection** : champ de recherche en haut du dropdown pour filtrer rapidement les options (case-insensitive, reset a la fermeture)
- **Tri intelligent** : tri numerique pour les colonnes de prix/marges, tri alphabetique locale (`fr`) pour les colonnes texte, valeurs null toujours en fin de liste

Composants concernes : `SortableColumnHeader` (nouveau), `MultiSelectFilter` (recherche ajoutee), `ProductsPage`, `ProductTable`, `ProductReference`, `ProductReferenceTable`

---

## Normalisation memoire/RAM (implementee)

Correction des doublons dans le referentiel produit via normalisation centralisee des valeurs de stockage et RAM :

- **Probleme** : valeurs heterogenes ("512 Go" vs "512GB", "4" vs "4Go") provenant de sources differentes (API fournisseurs, Odoo, LLM matching) → doublons dans les filtres
- **Solution** : fonctions `normalize_storage()` et `normalize_ram()` dans `backend/utils/normalize.py` — format canonique `"X Go"` / `"X To"`
- **Points d'entree normalises** : ETL (`etl.py`), sync Odoo (`odoo_sync.py`), matching LLM (`llm_matching.py`)
- **Migration** : `k1_normalize_memory_ram` — fusion des doublons existants avec reassignation des FK (products, supplier_catalog)
- **Tests** : 26 cas dans `backend/tests/test_normalize.py`

---

## Corrections de stabilite ETL (implementee)

Correction d'une violation de contrainte FK bloquant la synchronisation quotidienne des fournisseurs en production.

- **Probleme** : la sync quotidienne echouait avec une `ForeignKeyViolation` — le bulk DELETE de `supplier_catalog` supprimait des lignes encore referencees par des `pending_matches.temporary_import_id` non resolus
- **Fix** : avant le bulk DELETE, nullification de `pending_matches.temporary_import_id` pour les entrees qui referencent le catalogue du fournisseur concerne. Le code de resolution de matchs gere deja le cas `temporary_import_id = None`
- **Tests** : 2 cas dans `backend/tests/test_etl_persist.py` (securite FK + cas nominal sans pending_matches)

Fichiers concernes : `backend/utils/etl.py`, `backend/tests/test_etl_persist.py`

---

## Pipeline nightly automatise (implementee)

Automatisation complete du cycle nocturne : sync Odoo + fournisseurs + re-matching LLM + rapport email.

- **Orchestrateur** (`utils/nightly_pipeline.py`) : enchaine les 4 etapes et cree un `NightlyJob` en DB pour tracer chaque execution
- **Re-matching incremental** : chaque nuit, seuls les nouveaux labels fournisseurs sont evalues
  - Le `LabelCache` accumule les extractions LLM (bibliotheque historique) — labels deja vus = 0 appel API
  - `last_seen_run_id` sur `LabelCache` : marque chaque label vu lors du run Phase 1
  - Nettoyage selectif : labels disparus du catalogue fournisseur → product_id reset, PendingMatch supprimes
  - Matchs existants (auto, pending, rejected) preserves si le label est toujours present
  - Seuls les produits non encore resolus sont re-evalues (reduction de ~95% du scoring)
- **Planificateur** (`utils/nightly_scheduler.py`) : `threading.Timer` verifiant chaque minute si l'heure UTC configuree est atteinte. Variable `_last_run_date` pour eviter de relancer plusieurs fois la meme nuit
- **Rapport email** : webhook n8n (stdlib `urllib`, zero dependance externe). Payload JSON avec statut, compteurs, duree, lien de validation et corps HTML. Workflow n8n importable dans `n8n_nightly_workflow.json`
- **8 endpoints REST** (`routes/nightly.py`, prefix `/nightly`) : GET/PUT config, POST trigger, GET jobs, GET jobs/<id>, GET/POST/DELETE recipients
- **3 nouveaux modeles** : `NightlyConfig`, `NightlyJob`, `NightlyEmailRecipient`
- **Resilience** : cleanup automatique au demarrage (`_cleanup_orphaned_jobs`) des jobs laisses en "running" par un crash ou hot-reload
- **UI admin** : onglet "Automatisation" dans AdminPage — toggle enable, selecteur heure, bouton trigger, tableau historique, CRUD destinataires
- **34 tests** : `tests/test_routes_nightly.py` (22 tests) + `tests/test_nightly_pipeline.py` (12 tests)

Variables d'environnement : `NIGHTLY_WEBHOOK_URL`, `ENABLE_NIGHTLY_SCHEDULER` (false par defaut), `FRONTEND_URL` (lien validation email).

Fichiers concernes : `backend/utils/nightly_pipeline.py`, `backend/utils/nightly_scheduler.py`, `backend/routes/nightly.py`, `backend/utils/llm_matching.py`, `backend/app.py`, `backend/models.py`, `frontend/src/components/NightlyPipelinePanel.tsx`, `frontend/src/components/AdminPage.tsx`, `n8n_nightly_workflow.json`

---

## Optimisation CI — annulation des runs obsoletes (implementee)

Ajout d'un groupe de concurrence (`concurrency`) dans le pipeline CI GitHub Actions.

- **Probleme** : plusieurs pushs rapides sur la meme branche generaient une file de jobs CI, tous executes en serie meme quand les precedents etaient devenus obsoletes
- **Fix** : le champ `concurrency` annule automatiquement le run en cours sur la branche lorsqu'un nouveau push arrive, conservant uniquement le run le plus recent
- **Impact** : reduction des minutes CI consommees et des attentes inutiles en cas de pushs frequents

Fichiers concernes : `.github/workflows/ci.yml`

---

# Dette technique et ameliorations identifiees

## ~~Securite (priorite critique)~~ (corrigee)

### ~~JWT_SECRET avec fallback faible~~ ✅

- **Corrige** : `RuntimeError` levee au demarrage si `JWT_SECRET` est absent ou < 32 caracteres (`backend/utils/auth.py`)

### ~~Refresh token stocke dans localStorage~~ ✅

- **Corrige** : le refresh token est desormais un cookie HTTPOnly secure avec `SameSite=Lax` (`backend/routes/auth.py`)

### ~~PostgreSQL expose en production~~ ✅

- **Corrige** : port PostgreSQL lie a `127.0.0.1` dans `docker-compose.yml`. Pas de port expose dans `docker-compose.prod.yml`

### ~~Credentials base hardcodes dans docker-compose~~ ✅

- **Corrige** : les fallback defaults ont ete remplaces par `${VAR:?message}` dans `docker-compose.yml` — le demarrage echoue avec un message explicite si une variable manque

### ~~CORS wildcard par defaut~~ ✅

- **Corrige** : `FRONTEND_URL` est obligatoire au demarrage, CORS refuse `*` (`backend/app.py`)

---

## ~~Securite (priorite haute)~~ (corrigee)

### ~~Nginx CORS trop permissif~~ ✅

- **Corrige** : `Access-Control-Allow-Origin` dans `nginx.conf` est hardcode a `https://ajtpro.tulip-saas.fr`

### ~~Pas de protection CSRF~~ ✅

- **Corrige** : validation du header `Origin` sur les endpoints POST sensibles (`/login`, `/refresh`, `/logout`) dans `backend/routes/auth.py`. Les cookies sont `SameSite=Lax` + `HttpOnly` + `Secure` (defense-in-depth)

---

## Performance backend

### ~~N+1 queries dans `matching_stats`~~ ✅

Corrige : requetes agregees `GROUP BY supplier_id` avec `func.count()` + `case()` — 2 requetes au lieu de 1+4N.

### ~~Export sans pagination~~ ✅

Corrige : `LIMIT 10 000` sur `export_calculates`.

### ~~Timeout XML-RPC manquant~~ ✅

Corrige : transport custom avec timeout 60s sur les `ServerProxy` (HTTP et HTTPS).

### ~~Lecture du fichier de log en entier~~ ✅

Corrige : `_tail_lines()` lit par chunks depuis la fin du fichier + `_count_lines()` pour le comptage.

### ~~Limites non bornees sur certaines routes~~ ✅

Corrige : `min(limit, 100)` sur le dernier endpoint non borne (`odoo.py` sync jobs).

---

## Performance frontend

### Pas de lazy loading pour les composants lourds

- **Fichiers** : `StatisticsPage.tsx`, `MatchingPanel.tsx`, `ProductsPage.tsx`
- **Probleme** : composants de 500-1000 lignes charges de maniere synchrone
- **Correction** : utiliser `React.lazy()` + `Suspense` pour le code splitting

### useCallback/useMemo manquants sur les handlers

- **Fichier** : `ProductsPage.tsx` (23 useState + 7 useEffect)
- **Probleme** : handlers recrees a chaque render, provoquant des re-renders en cascade des enfants
- **Correction** : wrapper les handlers dans `useCallback`, les calculs derivatifs dans `useMemo`

### ~~Extraction d'options inefficace~~ (implementee)

~~`ProductsPage.tsx:197-239` : 6 iterations pour extraire les options uniques.~~

Correction appliquee : supprime lors de l'extraction du hook `useProductAttributeOptions`.

### ~~Cache pip manquant dans la CI~~ ✅

Corrige : `actions/cache@v4` sur `~/.cache/pip` avec cle basee sur `requirements.txt`.

---

## Robustesse et qualite du code — Backend

### ~~Rollback manquant dans les handlers d'exception~~ ✅

- **Corrige** : `db.session.rollback()` ajoute dans `nightly_pipeline.py` (3 handlers), `odoo_sync.py` (1 handler), `calculations.py` (1 handler)

### Erreurs silencieuses

- **Fichier** : `frontend/src/api.ts:66`
- **Probleme** : `.catch(() => ({}))` sur le parsing JSON masque les erreurs reseau
- **Correction** : logger l'erreur et retourner un objet d'erreur explicite

### ~~Masquage de mot de passe fragile~~ ✅

Corrige : sentinelle `__UNCHANGED__` non ambigu remplace `"********"` dans `backend/routes/odoo.py`.

### ~~Magic numbers eparpilles~~ ✅

Corrige : constantes extraites (`DEFAULT_LOG_LINES`, `MAX_LOG_LINES`, `DEFAULT_FETCH_JOBS_LIMIT`, `MAX_FETCH_JOBS_LIMIT`).

---

## Robustesse et qualite du code — Frontend

### TypeScript `any` repandu

- **Fichiers** : `ProductsPage.tsx`, `ProductReference.tsx`, `OdooSyncPanel.tsx`, `api.ts`
- **Probleme** : l'usage de `any` annule les garanties de typage et rend le refactoring risque
- **Correction** : typer les reponses API (`ApiResponse<T>`) et remplacer les `any` par des types explicites

### ~~console.error oublies en production~~ ✅

- **Clos** : audit revele que tous les `console.error` restants sont dans des error handlers legitimes (pas du debug oublie)

### Pas d'Error Boundary

- **Fichier** : app entiere
- **Probleme** : une erreur runtime dans un composant crashe toute l'application
- **Correction** : creer un composant `ErrorBoundary` et wrapper les pages principales

### ~~Race condition sur le refresh token~~ ✅

- **Corrige** : pattern `isRefreshing` + file d'attente dans `api.ts` — un seul appel `/refresh` a la fois, les requetes concurrentes attendent le resultat

### Pas d'AbortController

- **Fichiers** : `SearchPage.tsx`, `MatchingPanel.tsx`, `ProductsPage.tsx`
- **Probleme** : si l'utilisateur quitte la page pendant un fetch, la requete continue en memoire
- **Correction** : utiliser `AbortController` dans le cleanup des `useEffect`

---

## UX et accessibilite

### Etats de chargement manquants

- **Fichiers** : `ProductsPage.tsx`, `SearchPage.tsx`
- **Probleme** : pas de spinner/skeleton pendant le chargement initial — la page parait vide
- **Correction** : ajouter un etat `loading` avec indicateur visuel

### Etats vides manquants

- **Fichiers** : `ProductsPage.tsx`, `SearchPage.tsx`, `MatchingPanel.tsx`, `StatisticsPage.tsx`
- **Probleme** : quand il n'y a pas de donnees, les tableaux affichent un vide sans explication
- **Correction** : afficher un message "Aucun resultat" avec bouton de reinitialisation des filtres

### Accessibilite insuffisante

- **Probleme** : seulement 9 `aria-label` sur 34+ composants. Pas de `role` sur les dropdowns custom, pas de `aria-live` sur les mises a jour asynchrones, pas de navigation clavier dans les modales
- **Correction** : audit ARIA complet, ajout de `onKeyDown` pour Escape/Tab dans les modales et dropdowns

### ~~Modale ImportPreviewModal non fermable au clic exterieur~~ ✅

Corrige : `onClick` sur l'overlay + `stopPropagation` sur le contenu.

---

## Infrastructure et deploiement

### ~~Backend Docker tourne en root~~ ✅

- **Corrige** : utilisateur `appuser` cree dans `backend/Dockerfile`, le conteneur tourne en non-root

### ~~Pas de .dockerignore backend~~ ✅

Corrige : `backend/.dockerignore` cree (exclut `__pycache__`, `tests/`, `.env`, `logs/`, `.git`).

### Pas de rollback en cas d'echec deploy

- **Fichier** : `deploy-ci.sh`
- **Probleme** : si les health checks echouent apres un deploy, le script affiche un warning mais ne fait rien — l'application reste cassee
- **Correction** : implementer un rollback automatique (`git reset --hard HEAD~1` + restart) quand les health checks echouent

### deploy-ci.sh fait un git reset --hard sans sauvegarde

- **Fichier** : `deploy-ci.sh:34`
- **Probleme** : `git reset --hard origin/main` supprime tout changement local sans avertissement
- **Correction** : ajouter un `git stash` automatique avant le reset si des changements locaux existent

### Pas de limites de ressources Docker

- **Fichier** : `docker-compose.prod.yml`
- **Probleme** : aucune limite CPU/memoire — un matching LLM lourd peut saturer le VPS
- **Correction** : ajouter `deploy.resources.limits` (ex: 2 CPU, 2 Go RAM pour le backend)

### Connection pooling SQLAlchemy non configure

- **Probleme** : Gunicorn 4 workers × connexions non poolees peut epuiser `max_connections` PostgreSQL
- **Correction** : configurer `pool_size=10, max_overflow=20, pool_pre_ping=True` dans `create_engine()`

### ~~Endpoint /health superficiel~~ ✅

Corrige : `GET /health` execute `SELECT 1` et retourne l'etat DB + timestamp. Health check Docker pointe vers `/health`.

### ~~Pas de centralisation des logs Docker~~ ✅

Corrige : `logging: json-file` avec `max-size: 10m` et `max-file: 3` sur les 3 services dans `docker-compose.prod.yml`.

### Timeout Nginx potentiellement insuffisant

- **Fichier** : `frontend/nginx.conf:150`
- **Probleme** : `proxy_read_timeout 300s` (5 min) peut etre court pour les jobs de matching LLM
- **Correction** : augmenter a 600s

---

## ~~Refactorisation backend — DRY violations~~ (implementee)

### ~~Serialisation produit dupliquee~~ (priorite haute)

~~Le bloc de serialisation des attributs produit (`brand`, `memory`, `color`, `type`, `ram`, `norme`) avec gestion du null etait copie-colle **5 fois** dans `backend/routes/products.py`.~~

Correction appliquee : fonction `_serialize_product_attrs(product)` extraite, utilisee dans les 5 call sites (`list_product_calculations`, `internal_products`, `product_price_summary`, `list_products`, `export_calculates`).

### ~~Selection du mapping fournisseur dupliquee~~ (priorite haute)

~~La logique de selection du meilleur mapping actif (sinon le plus recent) etait recopiee **2 fois** dans `backend/routes/products.py`.~~

Correction appliquee : fonction `_select_best_mapping(supplier_api_id)` extraite, utilisee dans `_ensure_daily_supplier_cache` et `refresh_supplier_catalog`.

### Nettoyage numerique dans `etl.py` (priorite basse)

`_coerce_int` et `_coerce_float` dans `backend/utils/etl.py` partagent le meme bloc de nettoyage de chaine (strip, remplacement espace insecable, normalisation virgule/point). A extraire en `_normalize_numeric_string(value: str) -> str`.

---

## ~~Refactorisation frontend — DRY violations~~ (implementee)

### ~~Hook `useProductAttributeOptions` manquant~~ (priorite haute)

~~Le bloc `Promise.all([fetchBrands(), ...])` suivi des setState correspondants etait copie **3 fois** dans `ProductsPage.tsx`, `ProductAdmin.tsx` et `ProductReference.tsx`.~~

Correction appliquee : hook `useProductAttributeOptions()` cree dans `frontend/src/hooks/useProductAttributeOptions.ts`. Retourne les objets bruts (`brands`, `colors`, etc.) et les noms (`brandNames`, `colorNames`, etc.). Le bloc `mergeUsedOptions` (42 lignes) dans `ProductsPage` a ete supprime — le hook charge les options de reference directement.

### Calcul de marge duplique dans `ProductsPage.tsx` (priorite basse)

La logique `tcp + baseBuyPrice + normalizedMargin` et derivation du `margePercent` est dupliquee dans `applyBulkMargin` et `handleProductMarginUpdate`. A extraire en fonction utilitaire.

### ~~Merging d'options duplique dans `ProductsPage.tsx`~~ (implementee)

~~Le pattern `Array.from(new Set([...prev, ...usedXxx]))` etait repete 6 fois dans `ProductsPage.tsx`.~~

Correction appliquee : le bloc `mergeUsedOptions` entier a ete supprime lors de l'extraction du hook `useProductAttributeOptions` — le hook charge les options de reference, les donnees produit n'ont plus besoin d'enrichir les filtres.

---

## Composants trop volumineux (existant + enrichi)

| Fichier | Lignes | Probleme | Refactoring propose |
|---------|--------|---------|---------------------|
| `SupplierApiAdmin.tsx` | ~1014 | APIs + endpoints + mappings + fields + formulaires | Extraire `EndpointForm`, `MappingEditor`, `FieldList` |
| `ProductsPage.tsx` | ~927 | Tri + export + marge + pagination + modale | Extraire `useProductsFiltering` (hook), `ProductsExport` (logique export) |
| `MatchingPanel.tsx` | ~797 | Run + polling + stats + validation + rejection | Extraire `useMatchingPolling` (hook), `MatchingStats`, `PendingMatchList` |
| `backend/utils/etl.py` | ~232 (fn) | Matching + mise a jour prix + rapport | Decouper en 3 fonctions distinctes |
| `backend/utils/llm_matching.py` | ~756 | Normalisation + extraction LLM + scoring + persistance | Separer `extraction.py`, `scoring.py`, `persistence.py` |

---

## Tests manquants — Backend (existant)

### Routes sans aucune couverture

- `backend/routes/references.py` : 4 endpoints CRUD generiques pour 9 types de donnees — zero test
- `backend/routes/imports.py` : endpoints REST ETL (`fetch_supplier_api`, `list_supplier_api_config`, `verify_import`, `last_import`, `list_supplier_api_reports`) — zero test
- `backend/routes/settings.py` : `list_graph_settings` et `update_graph_setting` — zero test

### Routes partiellement couvertes

- `backend/routes/products.py` : `export_calculates`, `refresh_week`, `list_product_calculations`, `internal_products` sans tests

---

## Tests manquants — Frontend (existant)

Composants sans aucun test dans `frontend/src/components/` :

- `AdminPage.tsx`
- `SyncPage.tsx`
- `ImportPreviewModal.tsx`
- `ProductAdmin.tsx`
- `ProductEditModal.tsx`
- `ProductFilters.tsx`
- `ProductsPage.tsx` (composant central, ~927 lignes — priorite haute)
- `ProductTable.tsx`
- `SearchControls.tsx`
- `SearchPage.tsx`
- `SupplierApiAdmin.tsx` (~1014 lignes — priorite haute)
- `SupplierApiReports.tsx`
- `SupplierApiSyncPanel.tsx`
- `SupplierPriceModal.tsx`
- `TranslationAdmin.tsx`
- `UserAdmin.tsx`
- `WeekToolbar.tsx`

Composants avec tests existants : `App`, `LoginPage`, `LogsPanel`, `MatchingPanel`, `MultiSelectFilter`, `NotificationProvider`, `OdooSyncPanel`, `ProductReference`, `ProductReferenceForm`, `ProductReferenceTable`, `SortableColumnHeader`, `StatisticsPage`.