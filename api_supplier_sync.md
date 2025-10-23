# Processus de synchronisation « Lancer synchronisation donnée »

Ce document décrit techniquement le flux complet déclenché depuis l'interface lorsque l'on clique sur le bouton **« Lancer synchronisation donnée »** pour un fournisseur.

## 1. Déclenchement depuis le front-end

1. La page charge la liste des fournisseurs à partir de `fetchSuppliers()` et mémorise leur nom/id pour l'affichage.【F:frontend/src/components/SupplierApiSyncPanel.tsx†L35-L52】
2. Lorsqu'un utilisateur clique sur le bouton, `handleFetch` est exécutée :
   - Indique visuellement l'état de chargement pour le fournisseur sélectionné.
   - Appelle `fetchSupplierApiData(supplierId)` qui envoie une requête `POST` authentifiée vers l'endpoint `/supplier_api/<supplierId>` (voir §2).【F:frontend/src/components/SupplierApiSyncPanel.tsx†L68-L100】【F:frontend/src/api.ts†L249-L278】
   - Convertit la réponse en lignes prêtes à être affichées, en regroupant les articles par fournisseur et en mémorisant le mapping utilisé.【F:frontend/src/components/SupplierApiSyncPanel.tsx†L54-L144】
   - Affiche une notification « succès » ou « erreur » en fonction du résultat, avec le nombre d’articles importés et la version du mapping appliquée.【F:frontend/src/components/SupplierApiSyncPanel.tsx†L100-L119】
3. En cas d’erreur réseau ou serveur, l’utilisateur est notifié immédiatement et l’état revient à la normale sans modifier les données locales.【F:frontend/src/components/SupplierApiSyncPanel.tsx†L112-L136】

## 2. Sélection côté backend (route `/supplier_api/<supplier_id>`)

1. Le backend vérifie l’existence du fournisseur et lit les paramètres optionnels (`endpoint_id`, `endpoint_name`, `mapping_version_id`, `query_params`, `body`) fournis par le front-end (vide par défaut).【F:backend/routes/imports.py†L646-L690】
2. `_select_endpoint` choisit l’endpoint actif : si aucun identifiant n’est donné, l’endpoint API actif configuré pour ce fournisseur est recherché. L’absence d’endpoint renvoie une erreur 400.【F:backend/routes/imports.py†L669-L688】
3. `_select_mapping` récupère la version de mapping active associée à l’endpoint (ou celle explicitement demandée). Si aucun mapping n’est disponible, la requête est rejetée.【F:backend/routes/imports.py†L690-L701】
4. Une entrée `ApiFetchJob` est créée avec l’état `running`, reliant le fournisseur, l’endpoint et le mapping sélectionnés. Cela journalise le point de départ de la synchronisation et permettra de conserver l’historique (horodatage, paramètres utilisés, statut final).【F:backend/routes/imports.py†L703-L716】【F:backend/models.py†L72-L118】
5. Les éventuels surcharges de paramètres (`query_params`, `body`) sont fusionnées avec la configuration par défaut de l’endpoint avant l’appel de l’ETL.【F:backend/routes/imports.py†L716-L723】【F:backend/utils/etl.py†L532-L546】
6. La fonction `run_fetch_job` est appelée pour exécuter l’ETL complet (cf. §3). Toute exception renvoie une erreur HTTP 502 et marque la tâche comme échouée avec le message correspondant.【F:backend/routes/imports.py†L723-L735】【F:backend/utils/etl.py†L593-L638】

## 3. Exécution de l’ETL `run_fetch_job`

1. Chargement des métadonnées : la tâche `ApiFetchJob`, l’endpoint (avec la configuration de l’API fournisseur) et le mapping choisi sont rechargés depuis la base.【F:backend/utils/etl.py†L505-L534】
2. Préparation de la requête HTTP :
   - Fusion des paramètres de requête et du corps avec les valeurs par défaut de l’endpoint (template JSON).【F:backend/utils/etl.py†L534-L545】
   - Construction de l’URL finale, ajout des en-têtes et de l’authentification selon `SupplierAPI.auth_type` (clé API, Basic, etc.).【F:backend/utils/etl.py†L190-L222】
   - Exécution de la requête via `requests`. Toute réponse non `2xx` provoque une exception et l’échec de la tâche.【F:backend/utils/etl.py†L222-L229】
3. Journalisation brute :
   - Le corps JSON est conservé dans `raw_ingests` avec le statut HTTP et le type MIME pour audit ultérieur.【F:backend/utils/etl.py†L547-L566】【F:backend/models.py†L119-L139】
4. Extraction des items :
   - `_extract_items` parcourt le JSON suivant le chemin `items_path` défini sur l’endpoint (ou l’enveloppe par défaut) pour récupérer la liste d’articles. L’absence de données exploitables génère une erreur explicite.【F:backend/utils/etl.py†L566-L575】
5. Mapping des champs :
   - Chaque élément est transformé en dictionnaire normalisé en appliquant la table de correspondance `field_maps` (mapping actif). Les éventuelles transformations déclarées sont exécutées pour ajuster les formats.【F:backend/utils/etl.py†L575-L590】【F:backend/models.py†L99-L118】
6. Réinitialisation de la table temporaire :
   - Les entrées `temporary_imports` existantes pour ce fournisseur sont supprimées avant d’insérer les nouvelles données, garantissant que la table reflète l’instantané le plus récent.【F:backend/utils/etl.py†L590-L606】【F:backend/models.py†L167-L212】
7. Déduplication et stockage :
   - Les articles sont dédupliqués sur la paire `(EAN, part_number)` pour éviter les doublons.
   - Pour chaque article conservé :
     - Insertion d’une ligne dans `parsed_items` (log détaillé des valeurs extraites).【F:backend/utils/etl.py†L606-L633】【F:backend/models.py†L141-L166】
     - Insertion d’une ligne dans `temporary_imports` utilisée par les écrans de traitement/validation.【F:backend/utils/etl.py†L623-L633】【F:backend/models.py†L167-L212】
8. Calcul des rapports et mises à jour prix :
   - `_update_product_prices_from_records` confronte les articles au référentiel `supplier_product_refs` pour retrouver les produits internes, met à jour le champ `last_seen_at` pour les références trouvées et identifie les articles manquants ou non appariés.【F:backend/utils/etl.py†L318-L386】【F:backend/models.py†L167-L212】
   - Les prix des produits correspondants sont recalculés et enregistrés dans `product_calculations`, en appliquant les règles de marge (TCP, seuils).【F:backend/utils/etl.py†L386-L477】【F:backend/models.py†L256-L306】
   - Génération de trois listes pour le reporting : produits mis à jour, références présentes en base sans donnée fournisseur, et références fournisseur sans produit associé.【F:backend/utils/etl.py†L318-L383】
9. Finalisation de la tâche :
   - Mise à jour de `api_fetch_jobs` avec le statut `success`, la date de fin, les paramètres utilisés et les rapports générés.【F:backend/utils/etl.py†L545-L566】【F:backend/models.py†L103-L118】
   - Retour d’une charge utile structurée au front-end comprenant un échantillon (50 premières lignes), le nombre total d’articles insérés, les horodatages de début/fin, ainsi que la synthèse du mapping utilisé.【F:backend/utils/etl.py†L566-L638】

En cas d’exception, une transaction `rollback` est effectuée, la tâche est marquée `failed` avec le message d’erreur, et le front-end relaie cette information à l’utilisateur.【F:backend/utils/etl.py†L638-L664】

## 4. Résumé des tables modifiées

| Table | Rôle durant la synchronisation |
|-------|--------------------------------|
| `api_fetch_jobs` | Historique des exécutions, paramètres utilisés, statut final, rapports générés.【F:backend/routes/imports.py†L703-L716】【F:backend/utils/etl.py†L545-L566】 |
| `raw_ingests` | Journal brut de la réponse HTTP (payload complet + métadonnées).【F:backend/utils/etl.py†L547-L566】 |
| `parsed_items` | Stockage détaillé des données normalisées par article pour audit et rapprochements ultérieurs.【F:backend/utils/etl.py†L606-L633】 |
| `temporary_imports` | Table tampon utilisée par l’interface pour visualiser et valider les articles importés; vidée puis repopulée à chaque synchronisation.【F:backend/utils/etl.py†L590-L633】 |
| `supplier_product_refs` | Mise à jour du champ `last_seen_at` lorsque des références existantes sont rencontrées.【F:backend/utils/etl.py†L346-L374】【F:backend/models.py†L141-L166】 |
| `product_calculations` | Recalcul des prix/marges pour les produits internes correspondants au fournisseur synchronisé.【F:backend/utils/etl.py†L386-L477】 |

## 5. Appel à l’API fournisseur

L’appel sortant est réalisé une seule fois par synchronisation, via `requests.request` :

1. URL : `base_url` du `SupplierAPI` + `path` de l’`ApiEndpoint` (ex. `/stock/prices`).
2. Méthode HTTP : par défaut `GET`, mais la configuration peut spécifier `POST`, `PUT`, etc.【F:backend/models.py†L46-L75】
3. Authentification :
   - Aucun (par défaut),
   - En-tête clé API (valeurs `header`/`value`),
   - Basic Auth (login/mot de passe),
   - OAuth2 non pris en charge (génère une erreur explicite).【F:backend/utils/etl.py†L190-L222】
4. Paramètres : combinaison des paramètres configurés sur l’endpoint (`query_params`, `body_template`) et des surcharges envoyées par le front-end (si présentes).【F:backend/utils/etl.py†L534-L545】

La réponse doit être du JSON valide ; toute erreur réseau, authentification ou format déclenche un `rollback` complet et un message d’erreur à l’utilisateur.【F:backend/utils/etl.py†L222-L229】【F:backend/utils/etl.py†L547-L575】【F:backend/utils/etl.py†L638-L664】

## 6. Données renvoyées au front-end

Le backend renvoie un objet `SupplierApiSyncResponse` contenant :

- Métadonnées de la tâche (`job_id`, statut, timestamps),
- Compteurs (`parsed_count`, `temporary_import_count`),
- Échantillon des lignes insérées (`items`/`rows` limitées à 50),
- Rapport analytique (`report` avec les trois listes),
- Synthèse du mapping utilisé (`mapping`).【F:backend/utils/etl.py†L566-L638】

Le front-end stocke ces lignes en mémoire pour affichage, conserve la version du mapping associée et affiche les notifications adéquates.【F:frontend/src/components/SupplierApiSyncPanel.tsx†L78-L144】

## 7. Champs attendus dans les mappings

Chaque `FieldMap` associe un champ de la réponse fournisseur (`source_path`) à un champ cible consommé par l’ETL (`target_field`). Les cibles suivantes sont interprétées par le traitement :

| Champ cible | Statut | Utilisation dans l’ETL |
|-------------|--------|-------------------------|
| `ean`, `part_number` | Au moins l’un des deux est indispensable pour éviter la déduplication sur `(None, None)` et pour retrouver les références fournisseurs existantes.【F:backend/utils/etl.py†L592-L605】【F:backend/utils/etl.py†L339-L356】 |
| `supplier_sku` / `sku` / `reference` | Optionnel mais recommandé ; fournit une clé supplémentaire pour faire correspondre les références existantes avant de mettre à jour les prix.【F:backend/utils/etl.py†L339-L385】 |
| `description`, `model` | Optionnel ; alimente les colonnes d’affichage et les rapports si l’API ne fournit pas directement un modèle distinct.【F:backend/utils/etl.py†L293-L304】【F:backend/utils/etl.py†L397-L404】 |
| `quantity` | Optionnel ; valeur numérique normalisée pour les stocks temporaires et l’historique des imports.【F:backend/utils/etl.py†L279-L304】【F:backend/utils/etl.py†L601-L618】 |
| `price`, `selling_price`, `purchase_price`, `recommended_price` | Au moins un de ces champs doit être renseigné pour calculer `selling_price` et déclencher les recalculs tarifaires.【F:backend/utils/etl.py†L279-L304】【F:backend/utils/etl.py†L368-L386】 |
| `brand`, `color`, `memory`, `ram`, `norme`, `device_type` | Optionnel ; enrichit les lignes analysées et facilite les règles métier (cohérences, rapprochements).【F:backend/utils/etl.py†L601-L618】 |
| `currency`, `updated_at` | Optionnel ; journalise la devise de l’offre et l’horodatage de mise à jour pour audit.【F:backend/utils/etl.py†L601-L618】 |
| `product_id` | Optionnel ; permet un rattachement direct à un produit interne sans passer par la recherche sur EAN/SKU.【F:backend/utils/etl.py†L339-L360】 |

En pratique, un mapping minimal doit fournir **au moins un identifiant article** (`ean` ou `part_number`) et **une information de prix** pour produire des lignes exploitables et déclencher les mises à jour de marge. Les autres champs améliorent la qualité des rapports et des rapprochements mais restent facultatifs tant qu’ils ne sont pas utilisés par les règles métier associées.【F:backend/utils/etl.py†L279-L386】【F:backend/utils/etl.py†L592-L639】