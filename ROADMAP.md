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

## Optimisation CI — annulation des runs obsoletes (implementee)

Ajout d'un groupe de concurrence (`concurrency`) dans le pipeline CI GitHub Actions.

- **Probleme** : plusieurs pushs rapides sur la meme branche generaient une file de jobs CI, tous executes en serie meme quand les precedents etaient devenus obsoletes
- **Fix** : le champ `concurrency` annule automatiquement le run en cours sur la branche lorsqu'un nouveau push arrive, conservant uniquement le run le plus recent
- **Impact** : reduction des minutes CI consommees et des attentes inutiles en cas de pushs frequents

Fichiers concernes : `.github/workflows/ci.yml`

---

# Dette technique et ameliorations identifiees

## Refactorisation backend — DRY violations

### Serialisation produit dupliquee (priorite haute)

Le bloc de serialisation des attributs produit (`brand`, `memory`, `color`, `type`, `ram`, `norme`) avec gestion du null est copie-colle **4 fois** dans `backend/routes/products.py` :

- lignes ~360 (`list_product_calculations`)
- lignes ~563 (`list_products`)
- lignes ~627 (`export_calculates`)
- lignes ~434 (`internal_products`)

Correction : extraire une fonction `_serialize_product(p: Product) -> dict`.

### Selection du mapping fournisseur dupliquee (priorite haute)

La logique de selection du meilleur mapping actif (sinon le plus recent) existe dans `backend/routes/imports.py` sous `_select_mapping()`, mais est recopiee **2 fois** dans `backend/routes/products.py` (fonctions `_ensure_daily_supplier_cache` et `refresh_supplier_catalog`).

Correction : importer et appeler `_select_mapping` depuis `imports.py` dans `products.py`.

### Nettoyage numerique dans `etl.py` (priorite basse)

`_coerce_int` et `_coerce_float` dans `backend/utils/etl.py` partagent le meme bloc de nettoyage de chaine (strip, remplacement espace insecable, normalisation virgule/point). A extraire en `_normalize_numeric_string(value: str) -> str`.

---

## Performance backend — N+1 queries dans `matching_stats`

`matching_stats()` dans `backend/routes/matching.py` effectue **4 requetes COUNT separees par fournisseur** (total cached, pending, matched, manual). Avec N fournisseurs = 1 + 4N requetes SQL.

Correction : remplacer par des requetes agregees `GROUP BY supplier_id` via `func.count()`.

---

## Refactorisation frontend — DRY violations

### Hook `useProductAttributeOptions` manquant (priorite haute)

Le bloc `Promise.all([fetchBrands(), fetchColors(), fetchMemoryOptions(), fetchDeviceTypes(), fetchRAMOptions(), fetchNormeOptions()])` suivi des setState correspondants est copie **3 fois** :

- `frontend/src/components/ProductsPage.tsx`
- `frontend/src/components/ProductAdmin.tsx`
- `frontend/src/components/ProductReference.tsx`

Correction : extraire un hook `useProductAttributeOptions()` retournant `{ brands, colors, memories, types, rams, normes }`.

### Calcul de marge duplique dans `ProductsPage.tsx` (priorite basse)

La logique `tcp + baseBuyPrice + normalizedMargin` et derivation du `margePercent` est dupliquee dans `applyBulkMargin` et `handleProductMarginUpdate`. A extraire en fonction utilitaire.

### Merging d'options duplique dans `ProductsPage.tsx` (priorite basse)

Le pattern `Array.from(new Set([...prev, ...usedXxx]))` est repete 6 fois de suite (pour brand, color, memory, type, ram, norme) dans le meme `useEffect`. A extraire en fonction commune `mergeOptions(data, key, setter)`.

---

## Composants trop volumineux (refactorisation a planifier)

| Fichier | Lignes | Probleme |
|---------|--------|---------|
| `frontend/src/components/SupplierApiAdmin.tsx` | ~1014 | Gestion APIs + endpoints + mappings + fields + formulaires dans un seul composant |
| `frontend/src/components/ProductsPage.tsx` | ~878 | Tri + export + marge + pagination + orchestration dans un seul composant |
| `backend/utils/etl.py` fonction `_update_product_prices_from_records` | ~232 | Matching + mise a jour prix + construction rapport dans la meme fonction |
| `backend/utils/llm_matching.py` | ~756 (fichier entier) | Normalisation + contexte + extraction LLM + scoring + persistance melangees |

---

## Tests manquants — Backend

### Routes sans aucune couverture

- `backend/routes/references.py` : 4 endpoints CRUD generiques pour 9 types de donnees (marques, couleurs, memoire, types, RAM, normes, exclusions, fournisseurs, formats import) — zero test
- `backend/routes/imports.py` : endpoints REST ETL (`fetch_supplier_api`, `list_supplier_api_config`, `verify_import`, `last_import`, `list_supplier_api_reports`) — zero test
- `backend/routes/settings.py` : `list_graph_settings` et `update_graph_setting` — zero test

### Routes partiellement couvertes

- `backend/routes/products.py` : `export_calculates`, `refresh_week`, `list_product_calculations`, `internal_products` sans tests (seuls `list_products`, CRUD, `product_price_summary` et `supplier_catalog/refresh` ont des tests)

---

## Tests manquants — Frontend

Composants sans aucun test dans `frontend/src/components/` :

- `AdminPage.tsx`
- `DataImportPage.tsx`
- `FormattingPage.tsx`
- `ImportPreviewModal.tsx`
- `ProcessingPage.tsx`
- `ProductAdmin.tsx`
- `ProductEditModal.tsx`
- `ProductFilters.tsx`
- `ProductsPage.tsx` (composant central, ~878 lignes — priorite haute)
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