# AJT PRO - Système de Tarification avec Panier

Application de gestion des couts par fournisseurs et définition des prix de ventes

## Fonctionnalités

### 🔧 Traitement des données
- Import de fichiers Excel **(validée)**
- Calculs automatiques (TCP, marges) **(validée)**
- Filtrage par marques **(validée)**
- Exclusion configurable de certains produits **(validée)**
- Nettoyage automatique et suppression des doublons **(validée)**
- Export des données traitées **(validée)**
- Rapprochement automatique avec les références **(validée)**

### 🎨 Mise en forme
- A partir de la page produits ajout **(pas fait)**
- Génération de fichiers Excel formatés **(pas fait)**
- Création de pages web de consultation client **(pas fait)**
- Interface moderne avec design professionnel **(en amélioration)**
- Publication en ligne **(pas fait)**

### ⚙️ Administration
- Interface d'administration intuitive **(validée)**
- Mise à jour en masse des produits **(validée)**
- Ajout/modification/suppression de produits **(validée)**
- Authentification par jeton avec rôles admin et client **(nouveau)**

### 📱 Produits
- Affichage des produits **(validée)**
- Vue filtrable et édition en masse du référentiel **(validée)**
- Ajout/modification/suppression de produits **(validée)**

### 📊 Statistiques
- Graphiques dynamiques par semaine avec filtres fournisseur, marque et intervalle de semaines
- Comparaison de l'évolution d'un produit selon les fournisseurs
- Visualisations avancées : évolution relative, distribution des prix, écart-type, min/max, indice, corrélations et détection d'anomalies
- Bouton d'information (i) expliquant chaque graphique
- Filtre pour choisir les graphiques visibles, enregistré en base

## Fichier `.env`

Créez un fichier `.env` à la racine du projet avec vos identifiants Supabase :

```bash
VITE_SUPABASE_URL=<votre_url_supabase>
VITE_SUPABASE_ANON_KEY=<votre_cle_anon>
VITE_API_BASE=http://localhost:5001
JWT_SECRET=change-me
```

Ce fichier est ignoré par Git afin de protéger vos informations sensibles.

## Technologies utilisées

- **React 18** avec TypeScript
- **Tailwind CSS** pour le design
- **Lucide React** pour les icônes
- **XLSX** pour la manipulation Excel
- **Context API** pour la gestion d'état

## Installation

```bash
npm install
npm run dev
```

## Structure du projet

```
src/
├── components/
│   ├── AdminPage.tsx          # Interface d'administration
│   ├── FormattingPage.tsx     # Étape 2 - Mise en forme
│   ├── ProcessingPage.tsx     # Étape 1 - Traitement
│   ├── ProductsPage.tsx       # Visualisation des calculs
│   ├── ProductAdmin.tsx       # Gestion des produits
│   ├── ProductReference.tsx   # Référentiel produit filtrable
│   ├── MultiSelectFilter.tsx  # Filtre multi-sélection
│   ├── ReferenceAdmin.tsx     # Tables de référence
│   ├── SearchControls.tsx     # Outils de recherche
│   ├── TranslationAdmin.tsx   # Cohérence des couleurs
│   ├── StatisticsPage.tsx     # Visualisation des statistiques
│   └── WeekToolbar.tsx        # Outils hebdomadaires
├── utils/
│   ├── date.ts                # Fonctions de date
│   ├── html.ts                # Génération HTML
│   └── processing.ts          # Utilitaires de traitement
├── api.ts                     # Appels API
├── App.tsx                    # Application principale
├── main.tsx                   # Point d'entrée
├── index.css                  # Styles globaux
└── vite-env.d.ts              # Types Vite
```

## Utilisation

1. **Traitement** : Importez votre fichier Excel et lancez le traitement
2. **Mise en forme** : Générez les fichiers formatés et la page client
3. **Panier** : Les clients peuvent sélectionner des produits et passer commande
4. **Administration** : Gérez les produits Hotwav via l'interface dédiée

## Fonctionnalités avancées

- **Responsive design** adapté mobile et desktop
- **Recherche en temps réel** dans les produits
- **Filtres par marque** pour navigation facile
- **Animations fluides** et micro-interactions
- **Gestion d'erreurs** complète
- **Validation des formulaires**
- **Confirmation de commande** automatique

## Backend Python

Un backend minimal en **Python** est fourni dans le dossier `backend`. Il utilise **Flask** et une base **PostgreSQL** pour stocker les produits traités.

### Installation et lancement

```bash
# Créer la base de données (PostgreSQL local)
make db-create    # crée la base `ajtpro` si besoin

make venv         # crée l'environnement virtuel et installe les dépendances
# Créez un fichier `.env` contenant vos variables :
# DATABASE_URL=postgresql://user:password@host:5432/ajtpro
# FRONTEND_URL=http://votre-site.com
# VITE_API_BASE=http://votre-backend:5001
# FLASK_HOST=0.0.0.0
# PORT=5001
# Un fichier `.env.example` est fourni à titre d'exemple.
make run          # démarre l'API Flask
```

### Identifiants par défaut

Le script `backend/implement_tables.py` crée automatiquement un utilisateur
**admin** pour faciliter le développement local.

- **Nom d'utilisateur** : `admin`
- **Mot de passe** : `admin`

Une documentation interactive est générée grâce à **Flasgger**. Une fois
l'application lancée, ouvrez `http://localhost:5001/apidocs` pour consulter les
endpoints disponibles. Le fichier `backend/swagger_template.yml` contient le
gabarit OpenAPI utilisé pour initialiser Swagger UI.

La variable `FRONTEND_URL` doit correspondre exactement à l'origine (schéma et
domaine) de votre site frontend afin que la politique CORS fonctionne.

L'application expose notamment les routes :

- `GET /products` : liste l'ensemble des produits en base.
- `POST /products` : ajout d'un produit au format JSON.
- `POST /upload` : envoi d'un fichier Excel pour importer plusieurs produits.
- `POST /import` : importe un fichier Excel dans `temp_imports` et crée les références
  correspondantes.
- `POST /import_preview` : renvoie un aperçu des 5 premières lignes valides avant import.
- `GET /product_calculations/count` : renvoie le nombre de résultats de calcul disponibles.

Dans l'application React, le fichier traité est automatiquement transmis au backend via l'endpoint `/upload`. L'import du référentiel utilise quant à lui l'endpoint `/import`.

### Importer un référentiel produit depuis un CSV

Un script dédié permet d'insérer ou de mettre à jour massivement les produits de
référence à partir d'un fichier CSV (par exemple le format `Nom;Modèle;Marque;…`
fourni par vos partenaires).

```bash
python backend/scripts/database/import_reference_products.py \
    /chemin/vers/produits.csv \
    --default-tcp 0
```

- Le délimiteur utilisé est `;` par défaut (modifiable avec `--delimiter`).
- La valeur `--default-tcp` définit la valeur TCP attribuée aux nouvelles
  capacités mémoire qui n'existent pas encore dans la table `memory_options`.
- Le script crée automatiquement les entrées manquantes dans les tables de
  référence (marques, couleurs, capacités, RAM, normes, types d'appareil).

Les lignes comportant un EAN existant sont mises à jour ; sinon, la correspondance
se fait sur le couple Modèle/Marque. Un résumé des opérations est affiché en fin
d'exécution.

## Vérifications locales

Le projet fournit quelques commandes pour garder une base de code cohérente.

### Lint

Exécutez `npm run lint` après avoir installé les dépendances de développement (`npm install`). Sans ces packages, la commande peut échouer.

### Tests Python

Il n'existe pas encore de tests automatisés mais `pytest` est configuré pour unifier la procédure. Lancez simplement `pytest` pour vérifier qu'aucune erreur n'est remontée.

### Docker

Une configuration Docker est fournie pour lancer rapidement l'API Flask et la base PostgreSQL.

```bash
# Construire les images pour tous les services
make docker-build
# ou seulement pour le frontend
make docker-build SERVICE=frontend

# Démarrer l'environnement en arrière-plan
make docker-up
# ou uniquement le frontend
make docker-up SERVICE=frontend

# Consulter les logs
make docker-logs SERVICE=frontend

# Arrêter les conteneurs
make docker-down
# ou uniquement le frontend
make docker-down SERVICE=frontend
```

Par défaut l'image utilise **Python 3.12** et **PostgreSQL 16**. La base de données est accessible sur `localhost:5432` et l'API Flask sur `localhost:5001`.
Le fichier `docker-compose.yml` définit également la variable `FRONTEND_URL` sur `http://localhost:5173`. Modifiez-la si votre application frontend tourne sur une autre URL afin que la politique CORS fonctionne correctement.
