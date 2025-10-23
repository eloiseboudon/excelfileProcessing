# Comportement fonctionnel de l'application

## Vue d'ensemble
L'application coordonne la synchronisation des données produits entre les fournisseurs et le référentiel interne. Depuis l'interface web, un utilisateur authentifié peut déclencher la récupération de prix, quantités et stocks pour chaque fournisseur. Le front regroupe les boutons d'action, affiche les retours de synchronisation et conserve le mapping utilisé pour chaque fournisseur afin de présenter des lignes homogènes dans la table de suivi.【F:frontend/src/components/SupplierApiSyncPanel.tsx†L32-L128】

## Déroulé d'une synchronisation fournisseur
1. L'utilisateur clique sur « Lancer la synchronisation » pour un fournisseur donné. Le front envoie alors une requête `POST` vers `/supplier_api/<supplier_id>` et affiche un indicateur de chargement.【F:frontend/src/components/SupplierApiSyncPanel.tsx†L65-L100】
2. Côté backend, la route valide le fournisseur, sélectionne l'endpoint actif (ou celui demandé) et la version de mapping associée, puis crée un `ApiFetchJob` pour journaliser l'exécution.【F:backend/routes/imports.py†L645-L722】
3. Le moteur ETL `run_fetch_job` assemble les paramètres finaux (query/body), exécute l'appel HTTP vers l'API fournisseur, stocke le flux brut et déclenche l'extraction des articles.【F:backend/utils/etl.py†L712-L789】
4. La réponse normalisée (50 premières lignes, rapport, métadonnées de job) est renvoyée au front qui l'intègre dans la vue et affiche une notification de succès ou d'erreur.【F:backend/utils/etl.py†L911-L925】【F:frontend/src/components/SupplierApiSyncPanel.tsx†L83-L119】

## Collecte des prix, quantités et stock
- Les credentials et en-têtes requis sont injectés automatiquement selon le type d'authentification configuré (clé API, Basic Auth). L'ETL compose l'URL finale, choisit la méthode HTTP adaptée et sérialise le corps si besoin avant d'exécuter la requête via `requests`. Toute réponse non 2xx déclenche un échec de la synchronisation.【F:backend/utils/etl.py†L328-L370】
- Le moteur interprète ensuite la réponse JSON : il suit `items_path` si défini pour isoler la liste d'articles, prépare les mappings de champs et impose la présence d'un identifiant `supplier_sku` pour garantir le rapprochement ultérieur.【F:backend/utils/etl.py†L303-L312】【F:backend/utils/etl.py†L790-L800】

## Normalisation et stockage temporaire
- Chaque item est traduit en dictionnaire standard en appliquant la table de mapping (transformations comprises). Les anciennes entrées `TemporaryImport` du fournisseur sont purgées avant insertion afin que la table reflète l'état le plus récent.【F:backend/utils/etl.py†L803-L820】【F:backend/utils/etl.py†L814-L818】
- Lors du chargement, l'ETL uniformise prix et quantités en acceptant différentes clés possibles (`price`, `selling_price`, `stock`, `availability`, etc.). Les lignes sont dédupliquées sur la combinaison `(EAN, part_number, supplier_sku)` ; un identifiant synthétique est créé si aucun n'est fourni.【F:backend/utils/etl.py†L423-L841】
- Pour chaque ligne retenue, deux tables sont alimentées : `parsed_items` pour conserver l'historique détaillé (valeurs sources, attributs marketing, prix recommandés, horodatage) et `temporary_imports` pour alimenter les écrans de validation internes.【F:backend/utils/etl.py†L843-L886】【F:backend/models.py†L164-L212】【F:backend/models.py†L224-L266】

## Mise à jour du référentiel fournisseur
- Après normalisation, le moteur confronte les lignes importées aux références existantes (`SupplierProductRef`). Il essaye d'associer chaque enregistrement par `supplier_sku`, `EAN`, `part_number` ou `product_id` et met à jour le champ `last_seen_at` des références reconnues.【F:backend/utils/etl.py†L487-L569】【F:backend/models.py†L201-L223】
- Les produits non appariés côté API ou côté base sont remontés dans le rapport : références connues sans donnée fraiche, ou articles API sans correspondance. Ces listes guident les équipes dans la résolution des écarts.【F:backend/utils/etl.py†L570-L709】

## Calculs de prix et marges
- Pour chaque produit identifié, l'algorithme agrège les valeurs de prix (`price`, `selling_price`, `purchase_price`, etc.) et de stock (`quantity`, `stock`, `available`, ...). Seules les valeurs numériques valides et positives déclenchent les mises à jour.【F:backend/utils/etl.py†L536-L568】
- Les calculs appliquent la grille de marges : ajout d'une commission 4,5 %, intégration du coût TCP (issu du produit/mémoire) et application d'un multiplicateur dépendant du seuil de prix afin de déterminer les prix conseillés et la marge maximale.【F:backend/utils/etl.py†L392-L410】【F:backend/utils/etl.py†L647-L700】
- Les résultats (prix TTC optimisé, marge absolue et relative, stock) sont stockés ou mis à jour dans `product_calculations`, constituant l'historique tarifaire par fournisseur.【F:backend/utils/etl.py†L647-L702】【F:backend/models.py†L357-L379】

## Restitution et suivi
- Le backend associe aux lignes importées le nom du produit interne quand il est connu, comptabilise les occurrences et produit un rapport structuré (produits mis à jour, manques base/API). Ces données enrichissent la réponse JSON pour alimenter le tableau de bord et les notifications utilisateur.【F:backend/utils/etl.py†L619-L709】【F:backend/utils/etl.py†L889-L925】
- Le front conserve les lignes par fournisseur, permet de vider la vue manuellement et affiche des notifications contextualisées sur la réussite ou l'échec de chaque synchronisation.【F:frontend/src/components/SupplierApiSyncPanel.tsx†L73-L155】
