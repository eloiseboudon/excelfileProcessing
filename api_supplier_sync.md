# Processus de synchronisation « Lancer synchronisation donnée »

Ce document décrit techniquement le flux complet déclenché depuis l'interface lorsque l'on clique sur le bouton **« Lancer synchronisation donnée »** pour un fournisseur.

## 1. Déclenchement depuis le front-end

1. La page charge la liste des fournisseurs à partir de `fetchSuppliers()` et mémorise leur nom/id pour l'affichage.
2. Lorsqu'un utilisateur clique sur le bouton, `handleFetch` est exécutée :
   - Indique visuellement l'état de chargement pour le fournisseur sélectionné.
   - Appelle `refreshSupplierCatalog(supplierId)` (dans `api.ts`) qui envoie une requête `POST` authentifiée vers l'endpoint `/supplier_api/<supplierId>` (voir §2).
   - Convertit la réponse en lignes prêtes à être affichées, en regroupant les articles par fournisseur et en mémorisant le mapping utilisé.
   - Affiche une notification « succès » ou « erreur » en fonction du résultat, avec le nombre d'articles importés et la version du mapping appliquée.
3. En cas d'erreur réseau ou serveur, l'utilisateur est notifié immédiatement et l'état revient à la normale sans modifier les données locales.

## 2. Sélection côté backend (route `/supplier_api/<supplier_id>`)

1. Le backend vérifie l'existence du fournisseur et lit les paramètres optionnels (`endpoint_id`, `endpoint_name`, `mapping_version_id`, `query_params`, `body`) fournis par le front-end (vide par défaut).
2. `_select_endpoint` choisit l'endpoint actif : si aucun identifiant n'est donné, l'endpoint API actif configuré pour ce fournisseur est recherché. L'absence d'endpoint renvoie une erreur 400.
3. `_select_mapping` récupère la version de mapping active associée à l'endpoint (ou celle explicitement demandée). Si aucun mapping n'est disponible, la requête est rejetée.
4. Une entrée `ApiFetchJob` est créée avec l'état `running`, reliant le fournisseur, l'endpoint et le mapping sélectionnés. Cela journalise le point de départ de la synchronisation et permettra de conserver l'historique (horodatage, paramètres utilisés, statut final).
5. Les éventuels surcharges de paramètres (`query_params`, `body`) sont fusionnées avec la configuration par défaut de l'endpoint avant l'appel de l'ETL.
6. La fonction `run_fetch_job` est appelée pour exécuter l'ETL complet (cf. §3). Toute exception renvoie une erreur HTTP 502 et marque la tâche comme échouée avec le message correspondant.

## 3. Exécution de l'ETL `run_fetch_job`

La fonction `run_fetch_job` orchestre l'ensemble du processus ETL en déléguant à quatre sous-fonctions :

### 3.1 `_validate_fetch_params(db_session, job_id)`

Charge depuis la base de données la tâche `ApiFetchJob`, l'endpoint associé (avec la configuration de l'API fournisseur), le mapping choisi et le fournisseur. Vérifie la cohérence des données et retourne les objets nécessaires aux étapes suivantes.

### 3.2 `_execute_api_request(db_session, job, endpoint, supplier_api, query_overrides, body_overrides)`

Prépare et exécute la requête HTTP :
- Fusion des paramètres de requête et du corps avec les valeurs par défaut de l'endpoint (template JSON).
- Construction de l'URL finale, ajout des en-têtes et de l'authentification selon `SupplierAPI.auth_type` (clé API, Basic, etc.).
- Exécution de la requête via `requests`. Toute réponse non `2xx` provoque une exception et l'échec de la tâche.
- Le corps JSON de la réponse est conservé dans `raw_ingests` avec le statut HTTP et le type MIME pour audit ultérieur.
- Extraction des items : parcourt le JSON suivant le chemin `items_path` défini sur l'endpoint (ou l'enveloppe par défaut) pour récupérer la liste d'articles. L'absence de données exploitables génère une erreur explicite.

### 3.3 `_parse_and_deduplicate(items, mapping, supplier_id)`

Applique le mapping des champs aux éléments bruts :
- Chaque élément est transformé en dictionnaire normalisé en appliquant la table de correspondance `field_maps` (mapping actif). Les éventuelles transformations déclarées sont exécutées pour ajuster les formats.
- Les données sont normalisées (types numériques, formats de date, etc.).

### 3.4 `_persist_temporary_imports(db_session, records, supplier_id, job)`

Déduplique et stocke les résultats :
- Les entrées `temporary_imports` existantes pour ce fournisseur sont supprimées avant d'insérer les nouvelles données, garantissant que la table reflète l'instantané le plus récent.
- Les articles sont dédupliqués sur la paire `(EAN, part_number)` pour éviter les doublons.
- Pour chaque article conservé :
  - Insertion d'une ligne dans `parsed_items` (log détaillé des valeurs extraites).
  - Insertion d'une ligne dans `temporary_imports` utilisée par les écrans de traitement/validation.

### Étapes transversales

8. Calcul des rapports et mises à jour prix :
   - `_update_product_prices_from_records` confronte les articles au référentiel `supplier_product_refs` pour retrouver les produits internes, met à jour le champ `last_seen_at` pour les références trouvées et identifie les articles manquants ou non appariés.
   - Les prix des produits correspondants sont recalculés et enregistrés dans `product_calculations`, en appliquant les règles de marge (TCP, seuils) -- voir §8 pour le détail du module de tarification.
   - Génération de trois listes pour le reporting : produits mis à jour, références présentes en base sans donnée fournisseur, et références fournisseur sans produit associé.
9. Finalisation de la tâche :
   - Mise à jour de `api_fetch_jobs` avec le statut `success`, la date de fin, les paramètres utilisés et les rapports générés.
   - Retour d'une charge utile structurée au front-end comprenant un échantillon (50 premières lignes), le nombre total d'articles insérés, les horodatages de début/fin, ainsi que la synthèse du mapping utilisé.

En cas d'exception, une transaction `rollback` est effectuée, la tâche est marquée `failed` avec le message d'erreur, et le front-end relaie cette information à l'utilisateur.

## 4. Résumé des tables modifiées

| Table | Rôle durant la synchronisation |
|-------|--------------------------------|
| `api_fetch_jobs` | Historique des exécutions, paramètres utilisés, statut final, rapports générés. |
| `raw_ingests` | Journal brut de la réponse HTTP (payload complet + métadonnées). |
| `parsed_items` | Stockage détaillé des données normalisées par article pour audit et rapprochements ultérieurs. |
| `temporary_imports` | Table tampon utilisée par l'interface pour visualiser et valider les articles importés; vidée puis repopulée à chaque synchronisation. |
| `supplier_product_refs` | Mise à jour du champ `last_seen_at` lorsque des références existantes sont rencontrées. |
| `product_calculations` | Recalcul des prix/marges pour les produits internes correspondants au fournisseur synchronisé. |

## 5. Appel à l'API fournisseur

L'appel sortant est réalisé une seule fois par synchronisation (sauf en cas de pagination), via `requests.request` :

1. URL : `base_url` du `SupplierAPI` + `path` de l'`ApiEndpoint` (ex. `/stock/prices`).
2. Méthode HTTP : par défaut `GET`, mais la configuration peut spécifier `POST`, `PUT`, etc.
3. Authentification :
   - Aucun (par défaut),
   - En-tête clé API (valeurs `header`/`value`),
   - Basic Auth (login/mot de passe),
   - OAuth2 non pris en charge (génère une erreur explicite).
4. Paramètres : combinaison des paramètres configurés sur l'endpoint (`query_params`, `body_template`) et des surcharges envoyées par le front-end (si présentes).
5. Pagination : le modèle `ApiEndpoint` supporte les types de pagination suivants via le champ `pagination_type` :
   - `none` -- Pas de pagination (valeur par défaut).
   - `page` -- Pagination par numéro de page.
   - `cursor` -- Pagination par curseur.
   - `link` -- Pagination via l'en-tête `Link` de la réponse HTTP.
   - `offset` -- Pagination par offset/limit.

La réponse doit être du JSON valide ; toute erreur réseau, authentification ou format déclenche un `rollback` complet et un message d'erreur à l'utilisateur.

## 6. Données renvoyées au front-end

Le backend renvoie un objet `SupplierApiSyncResponse` contenant :

- Métadonnées de la tâche (`job_id`, statut, timestamps),
- Compteurs (`parsed_count`, `temporary_import_count`),
- Échantillon des lignes insérées (`items`/`rows` limitées à 50),
- Rapport analytique (`report` avec les trois listes : produits mis à jour, références manquantes en base, références manquantes dans l'API),
- Synthèse du mapping utilisé (`mapping`).

Le front-end stocke ces lignes en mémoire pour affichage, conserve la version du mapping associée et affiche les notifications adéquates.

### Rapports de synchronisation

Après la synchronisation, les données de rapport sont accessibles de deux manières :

- **Dans la réponse de synchronisation elle-même** : le champ `report` contient les trois listes (produits mis à jour, références présentes en base mais absentes de l'API, références fournisseur sans produit interne associé).
- **Via le composant `SupplierApiReports.tsx`** : ce composant affiche l'historique des synchronisations et le détail de chaque tâche (job), permettant de consulter les rapports a posteriori.

## 7. Champs attendus dans les mappings

Chaque `FieldMap` associe un champ de la réponse fournisseur (`source_path`) à un champ cible consommé par l'ETL (`target_field`). Les cibles suivantes sont interprétées par le traitement :

| Champ cible | Statut | Utilisation dans l'ETL |
|-------------|--------|-------------------------|
| `ean`, `part_number` | Au moins l'un des deux est indispensable pour éviter la déduplication sur `(None, None)` et pour retrouver les références fournisseurs existantes. |
| `supplier_sku` / `sku` / `reference` | Optionnel mais recommandé ; fournit une clé supplémentaire pour faire correspondre les références existantes avant de mettre à jour les prix. |
| `description`, `model` | Optionnel ; alimente les colonnes d'affichage et les rapports si l'API ne fournit pas directement un modèle distinct. |
| `quantity` | Optionnel ; valeur numérique normalisée pour les stocks temporaires et l'historique des imports. |
| `price`, `selling_price`, `purchase_price`, `recommended_price` | Au moins un de ces champs doit être renseigné pour calculer `selling_price` et déclencher les recalculs tarifaires. |
| `brand`, `color`, `memory`, `ram`, `norme`, `device_type` | Optionnel ; enrichit les lignes analysées et facilite les règles métier (cohérences, rapprochements). |
| `currency`, `updated_at` | Optionnel ; journalise la devise de l'offre et l'horodatage de mise à jour pour audit. |
| `product_id` | Optionnel ; permet un rattachement direct à un produit interne sans passer par la recherche sur EAN/SKU. |

En pratique, un mapping minimal doit fournir **au moins un identifiant article** (`ean` ou `part_number`) et **une information de prix** pour produire des lignes exploitables et déclencher les mises à jour de marge. Les autres champs améliorent la qualité des rapports et des rapprochements mais restent facultatifs tant qu'ils ne sont pas utilisés par les règles métier associées.

## 8. Module de tarification (`backend/utils/pricing.py`)

Les constantes et la logique de calcul de marge sont centralisées dans `backend/utils/pricing.py` :

```python
PRICE_THRESHOLDS = [15, 29, 49, 79, 99, 129, 149, 179, 209, 299, 499, 799, 999]
PRICE_MULTIPLIERS = [1.25, 1.22, 1.20, 1.18, 1.15, 1.11, 1.10, 1.09, 1.09, 1.08, 1.08, 1.07, 1.07, 1.06]
COMMISSION_RATE = 0.045
```

- **`PRICE_THRESHOLDS`** : seuils de prix d'achat (en euros). Chaque seuil est associé au multiplicateur de même index dans `PRICE_MULTIPLIERS`.
- **`PRICE_MULTIPLIERS`** : coefficients multiplicateurs appliqués au prix d'achat selon la tranche correspondante. Plus le prix d'achat est élevé, plus le coefficient est faible.
- **`COMMISSION_RATE`** : taux de commission plateforme (4.5 %).

La fonction principale est :

```
compute_margin_prices(price, tcp) -> (margin45, price_with_tcp, price_with_margin, max_price, marge, marge_percent)
```

Elle prend en entrée le prix d'achat (`price`) et le coût TCP, et retourne :
- `margin45` : prix majoré de la commission plateforme (4.5 %),
- `price_with_tcp` : prix d'achat augmenté du TCP,
- `price_with_margin` : prix final après application du multiplicateur de marge correspondant au seuil,
- `max_price` : prix de vente maximum recommandé,
- `marge` : montant de la marge en euros,
- `marge_percent` : pourcentage de marge.

Ce module est utilisé par l'ETL lors de l'étape de calcul des rapports et mises à jour prix (cf. §3, étape 8).
