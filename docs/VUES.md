# Documentation des vues — AJT Pro

Ce document décrit chaque vue de l'application : ce qui est affiché, comment les données sont sourcées, les actions disponibles et les points de cohérence à surveiller.

---

## Architecture globale des données

```
Odoo 17 (ERP)
    ↓  XML-RPC (odoo_sync)
products (table référentielle Odoo)
    ↑  matching LLM (product-centric)
    ↑  EAN / attributs (calculations.py)
    ↑
supplier_catalog ← ETL (api_fetch_jobs → parsed_items → supplier_catalog)
    ↑
supplier_apis / api_endpoints / mapping_versions / field_maps
```

**Règle fondamentale** : `products` est la **source de vérité**. C'est le référentiel Odoo. Toutes les données de prix et marges (`product_calculations`) en dérivent. Le catalogue fournisseur (`supplier_catalog`) est un cache temporaire.

---

## Source de vérité par table

| Table | Alimentée par | Rôle |
|-------|--------------|------|
| `products` | Sync Odoo (XML-RPC) | Référentiel maître |
| `supplier_catalog` | ETL fournisseur (API) | Cache catalogue fournisseur |
| `product_calculations` | `recalculate_product_calculations()` | Prix + marges calculés |
| `label_cache` | LLM matching | Cache résultats Claude Haiku |
| `pending_matches` | LLM matching | File de validation manuelle |
| `supplier_product_refs` | Validation manuelle d'un match | Lien SKU fournisseur → produit Odoo |

---

## 1. Vue TCP / Marges

**Accès** : Produits > onglet TCP/Marges | Rôles : `admin`, `user`, `client` (vue réduite)

### Ce qui est affiché

Tableau croisé des produits Odoo avec leurs prix d'achat et calculs de marges par fournisseur.

| Colonne | Source | Description |
|---------|--------|-------------|
| ID | `products.id` | Identifiant interne Odoo |
| Modèle | `products.model` | Nom épuré (sans marque/couleur/mémoire) |
| Description | `products.description` | Nom complet Odoo |
| Marque | `brands.brand` | Via `products.brand_id` |
| Mémoire | `memory_options.memory` | Via `products.memory_id` |
| Couleur | `colors.color` | Via `products.color_id` |
| Type | `device_types.type` | Via `products.type_id` |
| RAM | `ram_options.ram` | Via `products.ram_id` |
| Norme | `norme_options.norme` | Via `products.norme_id` |
| PA min | Min(`product_calculations.price`) | Plus bas prix d'achat tous fournisseurs |
| TCP | `memory_options.tcp_value` | Taxe coopérative perçue (liée à la mémoire) |
| Marge € | `product_calculations.marge` | Marge absolue (€) |
| Marge % | `product_calculations.marge_percent` | Marge relative |
| Prix HT max | `product_calculations.prixht_max` | Prix de vente HT maximum calculé |
| PA_{Fournisseur} | `product_calculations.price` | Colonne dynamique par fournisseur actif |

### Endpoint API

`GET /product_price_summary`

Logique : prend le dernier calcul (`MAX(date)`) par triplet `(product_id, supplier_id)`, agrège par `product_id`, calcule `min_buy_price`, `average_price`, et groupe les `latest_calculations` par fournisseur.

### Actions utilisateur

| Action | Endpoint | Effet |
|--------|----------|-------|
| Clic sur une ligne (admin/user) | — | Ouvre `SupplierPriceModal` : détail par fournisseur + édition marge |
| Modifier marge dans modal | `PUT /products/<id>` | Met à jour `marge`, `marge_percent`, `recommended_price` sur le produit |
| Recalculer | `POST /calculate_products` | Relance `recalculate_product_calculations()` |
| Export Excel | — (client-side) | Fichier XLSX stylisé (or/noir, groupé par marque) |
| Export JSON | — (client-side) | Données brutes JSON |
| Générer HTML | — (client-side) | Tarif interactif HTML (recherche, tri, couleurs de marge) |

### Vue client (rôle `client`)
Colonnes réduites : Prix de vente, Modèle, Description. Pas de recalcul, pas d'édition marge. Export XLSX simplifié.

### Points de cohérence

- **TCP = 0 pour les produits sans mémoire** : si `products.memory_id` est NULL, `tcp_value` = 0. Normal pour les accessoires/câbles.
- **Produits absents** : un produit Odoo n'apparaît ici QUE s'il a au moins un `product_calculation`. Si un produit est dans Odoo mais pas dans le tableau, c'est que le calcul ne l'a pas trouvé dans le catalogue fournisseur (ni par EAN, ni par attributs, ni par LabelCache).
- **Marge éditée manuellement** : la colonne `marge` de `products` est la valeur stockée. Le recalcul (`recalculate_product_calculations`) repart de `price` (PA fournisseur) et recalcule la marge par formule — il écrase donc les valeurs éditées manuellement. L'édition dans le modal met à jour `products.marge` mais PAS `product_calculations.marge` directement.

---

## 2. Vue Référentiel produits

**Accès** : Produits > onglet Référentiel | Rôles : `admin`, `user`

### Ce qui est affiché

Tableau en lecture seule de tous les produits de la table `products` (référentiel Odoo).

| Colonne | Source |
|---------|--------|
| ID, EAN, Modèle, Description | `products` |
| Marque, Mémoire, Couleur, Type, RAM, Norme | Tables de référence jointes |

### Endpoint API

`GET /products` + `GET /references/brands` + `GET /references/colors` + `GET /references/memory_options` + `GET /references/device_types` + `GET /references/ram_options` + `GET /references/norme_options`

### Actions utilisateur

- Filtres multi-select sur tous les champs de référence
- Recherche textuelle (modèle, description, ID, EAN)
- Tri sur toutes les colonnes
- Choix des colonnes visibles
- Pagination configurable

**Vue en lecture seule** : aucune édition possible ici. Pour créer/modifier/supprimer des produits → Admin > Référence.

### Points de cohérence

- Ce tableau reflète `products` en temps réel.
- Les produits créés depuis le LLM matching ("Créer produit") apparaissent ici immédiatement.
- Les produits supprimés depuis Odoo sont supprimés lors du prochain sync Odoo (avec suppression en cascade des `product_calculations`).

---

## 3. Moteur de recherche

**Accès** : Nav > Moteur de recherche | Rôles : `admin`, `user`

### Ce qui est affiché

Catalogue fournisseur brut (`supplier_catalog`) avec prix de vente, en temps réel.

| Colonne | Source |
|---------|--------|
| Description / Modèle | `supplier_catalog.description`, `.model` |
| EAN | `supplier_catalog.ean` |
| Part number | `supplier_catalog.part_number` |
| SKU fournisseur | `supplier_catalog.supplier_sku` |
| Quantité | `supplier_catalog.quantity` |
| Prix de vente | `supplier_catalog.selling_price` |
| Fournisseur | `suppliers.name` via `supplier_catalog.supplier_id` |
| Couleur | Traduite via `color_translations` si synonyme |

### Endpoint API

`GET /search_catalog` — déclenche un re-fetch automatique si la dernière synchronisation est > 24h.

### Actions utilisateur

- Recherche full-text (description, marque, couleur, part number, EAN) — côté client
- Filtre fournisseur
- Filtre stock disponible uniquement
- Filtre fourchette de prix
- Tri par prix (asc/desc)
- Bouton "Rafraîchir les catalogues" → `POST /supplier_catalog/refresh`

### Points de cohérence

- `supplier_catalog` est un **cache temporaire** : il est vidé et réalimenté à chaque sync fournisseur.
- Les couleurs affichées peuvent être traduites (ex: "Black" → "Noir") via `color_translations`. La couleur originale reste en base.
- Un article peut ne pas avoir d'EAN (matching possible via `part_number` ou `supplier_sku`).
- **Attention** : les prix ici sont les **prix fournisseurs bruts**. Les prix HT calculés (avec TCP et marges) sont dans TCP/Marges.

---

## 4. Statistiques

**Accès** : Nav > Statistiques | Rôles : `admin`, `user`

### Ce qui est affiché

4 graphiques d'analyse des données catalogue et historique de prix.

| Graphique | Source | Endpoint |
|-----------|--------|----------|
| Prix moyen par fournisseur | `supplier_catalog.selling_price` | `GET /supplier_avg_price` |
| Nombre de produits par fournisseur | `supplier_catalog` COUNT | `GET /supplier_product_count` |
| Répartition des prix | `supplier_catalog.selling_price` par tranche | `GET /supplier_price_distribution` |
| Évolution des prix par fournisseur | `product_calculations.price` AVG par semaine | `GET /supplier_price_evolution` |
| Comparaison produit × fournisseur | `product_calculations.price` (filtre `product_id`) | `GET /supplier_price_evolution?product_id=X` |

### Actions utilisateur

- Filtres : fournisseur optionnel, produit optionnel, plage de semaines
- Paramètre `product_id` active le graphique de comparaison par produit

### Points de cohérence

- Les 3 premiers graphiques utilisent `supplier_catalog` (données actuelles brutes).
- Le graphique d'évolution utilise `product_calculations` (données historiques calculées).
- Si `product_calculations` est vide (pas de recalcul lancé), l'évolution sera vide.
- La granularité temporelle est la **semaine** (`ProductCalculation.date` tronqué à la semaine de lundi).

---

## 5. Admin > Tables référence

**Accès** : Admin > Tables référence | Rôles : `admin` uniquement

### Ce qui est affiché

Deux sous-sections :

#### 5a. CRUD Produits (ProductAdmin)
Édition complète des produits de la table `products`.

Endpoint : `GET/POST /products` + `PUT/DELETE /products/<id>`

Actions : créer, modifier, supprimer un produit. Sélection des attributs via dropdowns (marques, couleurs, mémoire, types, RAM, norme).

#### 5b. Tables de référence (ReferenceAdmin)
Gestion des tables de classification : `brands`, `colors`, `memory_options`, `ram_options`, `device_types`, `norme_options`, `exclusions`, `suppliers`.

Endpoint : `GET/POST /references/<table>` + `PUT/DELETE /references/<table>/<id>`

### Points de cohérence CRITIQUES

- **Modifier le TCP d'une `memory_option`** déclenche automatiquement `update_product_calculations_for_memory_option()` → recalcule tous les `product_calculations` des produits ayant cette mémoire. Effet immédiat sur TCP/Marges.
- **Supprimer une marque** peut laisser des produits avec `brand_id=NULL` → apparaissent sans marque dans les filtres.
- **Supprimer une `device_type`** peut empêcher le type classifier de fonctionner correctement.
- **Modifier ou supprimer un fournisseur** peut casser les jointures dans `product_calculations` et `supplier_catalog`.

---

## 6. Admin > Cohérence des tables

**Accès** : Admin > Cohérence | Rôles : `admin` uniquement

### Ce qui est affiché

Gestion des **synonymes de couleurs** (`color_translations`).

Exemple : `"Black"` → `"Noir"`, `"Midnight"` → `"Noir"`, `"Starlight"` → `"Blanc"`

Endpoint : `GET/POST /references/color_translations` + `PUT/DELETE /references/color_translations/<id>`

### Points de cohérence

- Les traductions sont appliquées lors de la **sync Odoo** (parsing du nom produit) et dans le **moteur de recherche** (affichage).
- Si une traduction est manquante, les couleurs fournisseurs resteront en anglais/langue d'origine et ne seront pas trouvées par les filtres couleur.
- Modifier une traduction existante ne déclenche PAS de recalcul automatique des produits déjà parsés — un nouveau sync Odoo sera nécessaire.

---

## 7. Admin > API Fournisseurs

**Accès** : Admin > API fournisseurs | Rôles : `admin` uniquement

### Ce qui est affiché

Configuration CRUD des intégrations API par fournisseur.

Structure hiérarchique : `Supplier` → `SupplierApi` → `ApiEndpoints` + `MappingVersion` → `FieldMaps`

Endpoints : `GET /supplier_api/config` + CRUD complet sur `/supplier_api/*`

### Actions utilisateur

- Configurer l'URL de base, le type d'auth (None/API Key/Basic/OAuth2), les headers, le rate limit
- Définir les endpoints (méthode HTTP, path, path JSON vers les items)
- Mapper les champs JSON de la réponse vers les champs standardisés (`price`, `quantity`, `ean`, `part_number`, etc.)
- Versionner les mappings (rollback possible)

### Points de cohérence

- Un seul mapping peut être **actif** par `supplier_api`. Les autres versions sont inactives.
- Le champ `items_path` doit pointer vers le tableau d'items dans la réponse JSON (ex: `"data.items"` ou `"products"`). Si incorrect, l'ETL ne trouvera aucun article.
- Les champs requis pour le calcul TCP/Marges : `price` (ou `selling_price`) et `quantity`.
- `ean` et `part_number` sont optionnels mais améliorent la précision du matching.

---

## 8. Admin > Utilisateurs

**Accès** : Admin > Utilisateurs | Rôles : `admin` uniquement

### Ce qui est affiché

Liste des comptes utilisateurs (`users` table).

Endpoint : `GET/POST /users` + `PUT/DELETE /users/<id>`

### Rôles disponibles

| Rôle | Accès |
|------|-------|
| `admin` | Toutes les vues + actions d'administration |
| `user` | Produits, Recherche, Statistiques (lecture + édition marge) |
| `client` | Produits (vue réduite : 3 colonnes, export XLSX uniquement) |

### Points de cohérence

- Le mot de passe initial à la création est `"changeme"` — à communiquer à l'utilisateur pour qu'il le change.
- Les tokens JWT expirent après **30 minutes** (access) et **7 jours** (refresh). Un utilisateur supprimé peut utiliser son access token jusqu'à expiration.
- Seul un `admin` peut créer/modifier/supprimer des comptes. Il n'y a pas de self-registration.

---

## 9. Admin > Logs

**Accès** : Admin > Logs | Rôles : `admin` uniquement

### Ce qui est affiché

Deux sous-onglets :

#### 9a. Historique d'activité

Journal de toutes les actions métier enregistrées dans `activity_logs`.

Endpoint : `GET /logs/activity?category=X&page=Y`

Colonnes : Timestamp, Catégorie (badge coloré), Action, Utilisateur, Détails JSON, IP

#### 9b. Logs application

Dernières N lignes du fichier de log backend (`logs/app.log`).

Endpoint : `GET /logs/app?lines=100`

Niveaux colorés : ERROR (rouge), WARNING (jaune), DEBUG (gris), INFO (blanc).

### Points de cohérence

- `activity_logs` ne contient que les actions **déclenchées par des routes instrumentées** (login, matching, import, calculs, sync Odoo). Les opérations directes en base ne sont pas loggées.
- Le fichier de log est un `RotatingFileHandler` : max 10 Mo, 5 backups. Au-delà, les plus anciens logs sont perdus.
- En production Docker, les logs sont persistés via le volume `ajtpro_backend_logs`.

---

## 10. Synchro > Odoo

**Accès** : Paramètres > Synchro > onglet Odoo | Rôles : `admin` uniquement

### Ce qui est affiché

Interface de synchronisation avec Odoo 17 via XML-RPC.

#### Configuration
Formulaire de connexion : URL Odoo, base de données, login, mot de passe (chiffré Fernet en base).

Endpoint : `GET/PUT /odoo/config`

#### Test de connexion
Vérifie la connectivité XML-RPC et affiche la version serveur Odoo.

Endpoint : `POST /odoo/test`

#### Déclenchement sync
Lance un `OdooSyncJob` en arrière-plan.

Endpoint : `POST /odoo/sync`

#### Historique des jobs
Liste des 20 derniers sync jobs avec statut et rapport détaillé (créés/mis à jour/inchangés/supprimés/erreurs).

Endpoint : `GET /odoo/jobs` + `GET /odoo/jobs/<id>`

#### Sync automatique
Active/désactive et configure l'intervalle de sync automatique (minimum 15 min).

Endpoint : `PUT /odoo/auto-sync`

### Ce que fait le sync Odoo

1. Récupère tous les produits via `product.product` XML-RPC
2. Pour chaque produit : extrait nom, EAN, ref interne, prix, et **parse les attributs** depuis le nom (marque, couleur, mémoire, RAM, norme, type) via substring matching contre les tables de référence
3. Crée ou met à jour le produit dans `products` (avec extraction du `model` épuré)
4. Supprime les produits Odoo absents du dernier sync (orphelins)

### Points de cohérence CRITIQUES

- **La sync Odoo est la source de vérité pour `products`**. Toute modification manuelle d'un produit dans AJT Pro peut être écrasée par un prochain sync Odoo.
- **Suppression en cascade** : quand un produit est supprimé (orphelin Odoo), ses `product_calculations`, `pending_matches` et `supplier_product_refs` associés sont également supprimés.
- **Parsing des attributs** : si le nom Odoo est mal formaté, les champs `brand_id`, `color_id`, `memory_id` peuvent rester NULL, ce qui impacte le matching et les calculs TCP.
- Après un sync Odoo, il est recommandé de **relancer le calcul** (`POST /calculate_products`) pour mettre à jour les prix.

---

## 11. Synchro > Rapprochement LLM

**Accès** : Paramètres > Synchro > onglet Rapprochement | Rôles : `admin` uniquement

### Ce qui est affiché

Interface de matching intelligent des produits Odoo contre le catalogue fournisseur.

#### Statistiques de couverture

| Métrique | Source | Calcul |
|----------|--------|--------|
| Produits Odoo matchés | `product_calculations` | `COUNT(DISTINCT product_id)` |
| Total produits Odoo | `products` | `COUNT(*)` |
| Couverture % | Calculé | matchés / total × 100 |
| En attente | `pending_matches` | `COUNT WHERE status='pending'` |
| Validés | `pending_matches` | `COUNT WHERE status='validated'` |
| Rejetés | `pending_matches` | `COUNT WHERE status='rejected'` |
| Créés | `pending_matches` | `COUNT WHERE status='created'` |

**Attention** : "Produits Odoo matchés" = produits ayant au moins un `product_calculation`, **pas** uniquement les matchs LLM validés. C'est la vraie couverture (ETL + LLM).

#### Liste des matchs

Paginated, 10 par page, filtrable par statut / fournisseur / modèle.

Pour chaque match :
- Label source (libellé fournisseur brut)
- Attributs extraits (badges : marque, modèle, stockage, couleur, région)
- Candidats scorés (barre 0-100% + détail par critère)
- Actions selon le statut

### Direction du matching

Le matching est **product-centric** : on itère sur les produits Odoo non encore matchés, et on cherche dans le catalogue fournisseur quel label correspond.

### Algorithme de scoring (score sur 100 pts)

| Critère | Pts max | Hard disqualify si mismatch |
|---------|---------|----------------------------|
| Marque | 15 | Oui (les deux côtés non-null) |
| Couleur | 15 | Oui (les deux côtés non-null) |
| Stockage | 25 | Oui (les deux côtés ont une valeur identifiable) |
| Famille modèle | 40 | Non (fuzzy matching) |
| Région | 5 | Non |
| Similarité libellé | variable | Non |

**Règle disqualification stockage** : hard disqualify uniquement si les deux côtés ont un stockage identifiable (champ `memory` officiel OU stockage lisible dans le nom du modèle). Si un seul côté a le stockage → 0 pts, pas de disqualification.

### Auto-rejet

Si **tous** les candidats d'un produit déclenchent un hard disqualifier → `PendingMatch(status='rejected')` créé automatiquement (avec le meilleur candidat disqualifié pour traçabilité).

### Actions utilisateur

| Action | Statut source | Effet |
|--------|--------------|-------|
| Valider | `pending` ou `rejected` | Crée `SupplierProductRef`, met à jour `LabelCache`, `status='validated'` |
| Créer produit | `pending` | Crée un nouveau produit dans `products`, `status='created'` |
| Ignorer | `pending` | `status='rejected'` |

### Points de cohérence

- Valider un match **ne déclenche pas automatiquement le recalcul des prix**. Il faut relancer "Recalculer" dans TCP/Marges pour que le produit apparaisse dans les calculs.
- Un produit déjà présent dans `product_calculations` (via ETL) n'apparaît pas dans la queue de matching LLM (il a déjà un `SupplierProductRef`... **sauf** si le matching ETL l'a trouvé via attributs sans créer de `SupplierProductRef`). Il peut donc être soumis au LLM en double — ce n'est pas bloquant mais c'est redondant.
- Le **LabelCache** évite les double appels LLM pour le même libellé normalisé par fournisseur. Un libellé mis en cache ne consomme plus de crédits Anthropic lors des runs suivants.
- Coût estimé : < 0.30€ pour 3000 produits (Claude Haiku 4.5).

---

## 12. Synchro > Sync fournisseurs

**Accès** : Paramètres > Synchro > onglet Synchronisation | Rôles : `admin` uniquement

### Ce qui est affiché

Panel de déclenchement des fetches API fournisseurs + preview des données récupérées.

Endpoint : `POST /supplier_api/<supplier_id>` (déclenche le job ETL)

### Ce que fait le job ETL

1. **Fetch** : appel HTTP vers l'API fournisseur (auth, rate limiting, pagination)
2. **Parse** : extraction des champs via le `FieldMap` actif (JSON path → champs standardisés)
3. **Transform** : transformations configurées (ex: conversion devise, normalisation)
4. **Deduplicate** : unicité sur `(supplier_id, ean, part_number, job_id)`
5. **Persist** : insert dans `parsed_items` → vidage + réalimentation de `supplier_catalog`
6. **Recalculate** : appel automatique de `recalculate_product_calculations()`

### Actions utilisateur

- Bouton "Lancer synchronisation donnée {fournisseur}" par fournisseur
- Preview des données : articles récupérés avec description, EAN, prix, quantité, mapping utilisé
- Bouton "Vider la table" : vide `supplier_catalog`

### Points de cohérence

- La synchronisation **vide et remplace** `supplier_catalog` pour le fournisseur concerné. Les données précédentes sont perdues.
- Si l'API fournisseur est indisponible, `supplier_catalog` conserve les données de la dernière sync réussie.
- Le recalcul automatique post-sync signifie que les nouvelles données apparaissent dans TCP/Marges **après le retour de l'API** (peut être long sur les gros catalogues).
- Si le mapping est incorrect (mauvais `items_path` ou champs mal mappés), le catalogue sera vide ou mal parsé.

---

## 13. Synchro > Rapports

**Accès** : Paramètres > Synchro > onglet Rapports | Rôles : `admin` uniquement

### Ce qui est affiché

Historique des jobs de sync fournisseur (`api_fetch_jobs`).

Endpoint : `GET /supplier_api/reports`

### Contenu d'un rapport

| Section | Contenu |
|---------|---------|
| Résumé | Fournisseur, dates début/fin, mapping utilisé |
| Produits mis à jour | Liste avec ID, nom, prix, EAN, part number |
| Manquants en base | Articles présents dans l'API mais sans produit Odoo correspondant |
| Manquants dans l'API | Articles attendus (en base) mais absents de la réponse API |
| Données brutes | Extrait JSON des premiers items de la réponse API |

### Points de cohérence

- "Manquants en base" = articles fournisseurs sans produit Odoo correspondant. Candidats pour le matching LLM.
- "Manquants dans l'API" = articles qui étaient dans la base mais que l'API ne retourne plus (rupture de stock totale, référence discontinuée).
- Les rapports sont conservés indéfiniment en base dans `api_fetch_jobs`.

---

## Matrice de cohérence des données

### Flux de données principal

```
Sync Odoo → products
    ↓
Sync fournisseur → supplier_catalog
    ↓ (recalculate automatique)
product_calculations ← TCP/Marges
    ↓
LLM Matching → pending_matches → (validation) → supplier_product_refs + label_cache
```

### Quand les données sont-elles mises à jour ?

| Table | Mise à jour lors de |
|-------|-------------------|
| `products` | Sync Odoo |
| `supplier_catalog` | Sync fournisseur (ETL) |
| `product_calculations` | Sync fournisseur (auto) OU clic "Recalculer" OU validation match LLM |
| `label_cache` | Run matching LLM OU validation manuelle |
| `pending_matches` | Run matching LLM / validation / rejet |
| `supplier_product_refs` | Validation manuelle d'un match LLM |

### Points de vigilance

1. **Recalcul après sync Odoo** : après un sync Odoo, les prix ne sont PAS automatiquement recalculés. Il faut lancer "Recalculer" dans TCP/Marges pour rafraîchir `product_calculations`.

2. **Recalcul après validation LLM** : valider un match crée le `SupplierProductRef` et met à jour le `LabelCache`, mais ne relance pas le calcul. Le produit n'apparaîtra dans TCP/Marges qu'au prochain recalcul.

3. **Écrasement marge manuelle** : éditer la marge d'un produit via le modal met à jour `products.marge`. Mais un recalcul complet repart des formules de prix et peut recalculer une marge différente.

4. **SupplierProductRef vs ProductCalculation** : ces deux tables ont des rôles distincts.
   - `product_calculations` : présence d'un prix calculé (source ETL + LLM)
   - `supplier_product_refs` : lien explicite SKU fournisseur → produit Odoo (créé uniquement par validation LLM)

5. **Produits sans type** : si `device_type_id` est NULL, le produit n'est pas filtrable par type. Utiliser "Assigner les types" dans le matching pour classifier automatiquement.

6. **Doublon de processing LLM** : un produit déjà dans `product_calculations` (via ETL EAN/attributs) peut être soumis au LLM car il n'a pas forcément de `SupplierProductRef`. Ce n'est pas bloquant mais consomme des crédits inutilement.
