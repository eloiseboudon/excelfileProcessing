# Comportement fonctionnel de l'application

## Vue d'ensemble
L'application coordonne la synchronisation des donnees produits entre les fournisseurs et le referentiel interne, et met a disposition un ensemble d'outils pour gerer le catalogue, les references, les utilisateurs et la recherche de produits. Depuis l'interface web, un utilisateur authentifie peut declencher la recuperation de prix, quantites et stocks pour chaque fournisseur, consulter les rapports de synchronisation, administrer les tables de reference et rechercher des produits dans le catalogue. Le front regroupe les boutons d'action, affiche les retours de synchronisation et conserve le mapping utilise pour chaque fournisseur afin de presenter des lignes homogenes dans la table de suivi.

---

## Synchronisation fournisseur

### Deroule d'une synchronisation
1. L'utilisateur clique sur « Lancer la synchronisation » pour un fournisseur donne. Le front envoie alors une requete `POST` vers `/supplier_api/<supplier_id>` et affiche un indicateur de chargement.
2. Cote backend, la route valide le fournisseur, selectionne l'endpoint actif (ou celui demande) et la version de mapping associee, puis cree un `ApiFetchJob` pour journaliser l'execution.
3. Le moteur ETL `run_fetch_job` orchestre l'ensemble du traitement en quatre etapes :
   - `_validate_fetch_params` : validation et assemblage des parametres finaux (query/body).
   - `_execute_api_request` : execution de l'appel HTTP vers l'API fournisseur et stockage du flux brut.
   - `_parse_and_deduplicate` : extraction, normalisation et deduplication des articles recus.
   - `_persist_supplier_catalog` : persistence des lignes traitees dans le catalogue fournisseur.
4. La reponse normalisee (50 premieres lignes, rapport, metadonnees de job) est renvoyee au front qui l'integre dans la vue et affiche une notification de succes ou d'erreur.

### Collecte des prix, quantites et stock
- Les credentials et en-tetes requis sont injectes automatiquement selon le type d'authentification configure (cle API, Basic Auth). L'ETL compose l'URL finale, choisit la methode HTTP adaptee et serialise le corps si besoin avant d'executer la requete via `requests`. Toute reponse non 2xx declenche un echec de la synchronisation.
- Le moteur interprete ensuite la reponse JSON : il suit `items_path` si defini pour isoler la liste d'articles, prepare les mappings de champs et impose la presence d'un identifiant `supplier_sku` pour garantir le rapprochement ulterieur.

### Normalisation et stockage temporaire
- Chaque item est traduit en dictionnaire standard en appliquant la table de mapping (transformations comprises). Les anciennes entrees `SupplierCatalog` du fournisseur sont purgees avant insertion afin que la table reflete l'etat le plus recent.
- Lors du chargement, l'ETL uniformise prix et quantites en acceptant differentes cles possibles (`price`, `selling_price`, `stock`, `availability`, etc.). Les lignes sont dedupliquees sur la combinaison `(EAN, part_number, supplier_sku)` ; un identifiant synthetique est cree si aucun n'est fourni.
- Pour chaque ligne retenue, deux tables sont alimentees : `parsed_items` pour conserver l'historique detaille (valeurs sources, attributs marketing, prix recommandes, horodatage) et `supplier_catalog` pour alimenter les ecrans de validation internes.

### Mise a jour du referentiel fournisseur
- Apres normalisation, le moteur confronte les lignes importees aux references existantes (`SupplierProductRef`). Il essaye d'associer chaque enregistrement par `supplier_sku`, `EAN`, `part_number` ou `product_id` et met a jour le champ `last_seen_at` des references reconnues.
- Les produits non apparies cote API ou cote base sont remontes dans le rapport : references connues sans donnee fraiche, ou articles API sans correspondance. Ces listes guident les equipes dans la resolution des ecarts.

### Calculs de prix et marges
- Pour chaque produit identifie, l'algorithme agrege les valeurs de prix (`price`, `selling_price`, `purchase_price`, etc.) et de stock (`quantity`, `stock`, `available`, ...). Seules les valeurs numeriques valides et positives declenchent les mises a jour.
- Les calculs appliquent la grille de marges : ajout d'une commission 4,5 %, integration du cout TCP (issu du produit/memoire) et application d'un multiplicateur dependant du seuil de prix afin de determiner les prix conseilles et la marge maximale.
- Les resultats (prix TTC optimise, marge absolue et relative, stock) sont stockes ou mis a jour dans `product_calculations`, constituant l'historique tarifaire par fournisseur.

### Restitution et suivi
- Le backend associe aux lignes importees le nom du produit interne quand il est connu, comptabilise les occurrences et produit un rapport structure (produits mis a jour, manques base/API). Ces donnees enrichissent la reponse JSON pour alimenter le tableau de bord et les notifications utilisateur.
- Le front conserve les lignes par fournisseur, permet de vider la vue manuellement et affiche des notifications contextualisees sur la reussite ou l'echec de chaque synchronisation.
- Le bouton `refreshSupplierCatalog` sur le panneau de synchronisation permet de relancer la recuperation complete du catalogue d'un fournisseur.

---

## Moteur de recherche

Le moteur de recherche (`SearchPage.tsx`) permet aux utilisateurs de trouver des produits dans l'ensemble du catalogue fournisseur.

### Chargement du catalogue
- Au montage de la page, l'integralite du catalogue fournisseur est chargee via `fetchSearchCatalog()`.
- Les donnees sont stockees cote client pour permettre une recherche instantanee sans appels reseau supplementaires.

### Recherche plein texte cote client
- La recherche s'effectue entierement cote client en utilisant des tokens normalises : les accents sont retires et le texte est converti en minuscules.
- Les champs interroges sont : nom du produit, description, marque, fournisseur, synonymes de couleur, code EAN et reference constructeur (part number).
- La saisie utilisateur est tokenisee de la meme maniere, puis chaque token est compare aux tokens de chaque produit.

### Filtrage par prix
- Un double curseur (dual slider) permet de definir une fourchette de prix minimum et maximum.
- Seuls les produits dont le prix tombe dans la fourchette selectionnee sont affiches.

### Affichage des resultats
- Les resultats sont tries par prix croissant.
- Pour chaque produit, les informations suivantes sont affichees : nom du produit, marque, description, quantite en stock, code EAN, badge du fournisseur et prix.

---

## Administration des tables de reference

L'administration des tables de reference (`ReferenceAdmin.tsx`) permet de gerer les donnees structurelles utilisees dans tout le referentiel produit.

### Tables gerees
Les operations CRUD (creation, lecture, modification, suppression) sont disponibles pour les tables suivantes :
- **Marques** : liste des marques reconnues par le systeme.
- **Couleurs** : palette de couleurs avec gestion des synonymes.
- **Options memoire** : capacites de stockage disponibles, incluant les valeurs TCP (cout technique) associees.
- **Options RAM** : capacites de memoire vive disponibles.
- **Normes** : normes et certifications applicables aux produits.
- **Types d'appareil** : categories d'equipements (telephone, tablette, ordinateur, etc.).

### Interface
- Chaque table dispose de sa propre interface de gestion avec formulaire de creation/edition et liste des enregistrements existants.
- Les modifications sont immediatement repercutees dans les listes deroulantes du referentiel produit.

### Traduction des couleurs
- Le composant `TranslationAdmin.tsx` gere les traductions et synonymes de couleurs.
- Ces synonymes sont utilises par le moteur de recherche pour permettre la correspondance entre les termes saisis par l'utilisateur et les couleurs referencees (par exemple, "noir" correspond a "black", "schwarz", etc.).

---

## Referentiel produit

Le referentiel produit (`ProductReferenceForm.tsx` et `ProductReferenceTable.tsx`) constitue la base de donnees centrale des produits connus du systeme.

### Gestion des references
- Operations CRUD completes sur les references produit.
- Chaque reference est liee aux tables de reference (marques, couleurs, memoire, RAM, normes, types d'appareil).
- La creation d'une nouvelle reference s'effectue via un formulaire accessible depuis la barre d'outils.

### Table de consultation
- La table de references est filtrable et permet la recherche textuelle.
- Un systeme de pagination gere l'affichage lorsque le nombre de references est eleve.
- Les colonnes affichent les attributs principaux du produit ainsi que les liens vers les tables de reference associees.

---

## Rapports de synchronisation

La page des rapports de synchronisation (`SupplierApiReports.tsx`) offre une vue historique des executions de synchronisation.

### Contenu des rapports
- Chaque rapport correspond a un job de synchronisation (`ApiFetchJob`) et contient :
  - Le nombre de produits mis a jour.
  - La liste des produits manquants dans la base (presents dans l'API mais sans correspondance interne).
  - La liste des produits manquants dans l'API (references internes sans donnee fraiche).

### Details du job
- Horodatage de l'execution.
- Statut du job (succes, echec, en cours).
- Parametres utilises pour l'appel API.
- Version du mapping appliquee lors du traitement.

---

## Gestion des utilisateurs

La gestion des utilisateurs (`UserAdmin.tsx`) est reservee aux administrateurs.

### Fonctionnalites
- Creation, modification et suppression de comptes utilisateurs.
- Attribution des roles : **admin** (acces complet a toutes les fonctionnalites d'administration) ou **user** (acces aux fonctionnalites de consultation et de synchronisation).
- Gestion des mots de passe (creation et reinitialisation).
