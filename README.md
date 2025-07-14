# AJT PRO - Système de Tarification avec Panier

Application complète de gestion de tarifs avec système de panier et commande par email.

## Fonctionnalités

### 🔧 Étape 1 - Traitement des données
- Import de fichiers Excel **(validée)**
- Calculs automatiques (TCP, marges) **(validée)**
- Filtrage par marques **(validée)**
- Exclusion configurable de certains produits **(validée)**
- Nettoyage automatique et suppression des doublons **(validée)**
- Export des données traitées **(validée)**
- Rapprochement automatique avec les références **(validée)**

### 🎨 Étape 2 - Mise en forme
- Génération de fichiers Excel formatés **(pas fait)**
- Création de pages web de consultation client **(pas fait)**
- Interface moderne avec design professionnel **(pas fait)**
- Publication en ligne **(pas fait)**

### 🛒 Système de panier
- Sélection de produits avec quantités **(pas fait)**
- Gestion complète du panier **(pas fait)**
- Formulaire de commande client **(pas fait)**
- Envoi automatique par email **(pas fait)**

### ⚙️ Administration
- Interface d'administration intuitive **(validée)**
- Mise à jour en masse des produits **(validée)**
- Ajout/modification/suppression de produits **(validée)**

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

## Configuration EmailJS

Pour activer l'envoi d'emails, configurez EmailJS :

1. Créez un compte sur [EmailJS](https://www.emailjs.com/)
2. Créez un service email
3. Créez un template avec les variables suivantes :
   - `{{customer_name}}`
   - `{{customer_email}}`
   - `{{customer_phone}}`
   - `{{customer_company}}`
   - `{{customer_address}}`
   - `{{order_details}}`
   - `{{total_amount}}`
   - `{{order_date}}`
   - `{{total_items}}`
   - `{{order_id}}`
   - `{{brands_summary}}`

4. Remplacez les valeurs dans `src/services/emailService.ts` :
   const EMAIL_CONFIG = {
    serviceId: 'VOTRE_SERVICE_ID',
    templateId: 'VOTRE_TEMPLATE_ID',
    publicKey: 'VOTRE_PUBLIC_KEY'
  };
  ```

## Fichier `.env`

Créez un fichier `.env` à la racine du projet avec vos identifiants Supabase :

```bash
VITE_SUPABASE_URL=<votre_url_supabase>
VITE_SUPABASE_ANON_KEY=<votre_cle_anon>
VITE_API_BASE=http://localhost:5001
```

Ce fichier est ignoré par Git afin de protéger vos informations sensibles.

## Technologies utilisées

- **React 18** avec TypeScript
- **Tailwind CSS** pour le design
- **Lucide React** pour les icônes
- **XLSX** pour la manipulation Excel
- **EmailJS** pour l'envoi d'emails
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
- `GET /product_calculations/count` : renvoie le nombre de résultats de calcul disponibles.

Dans l'application React, le fichier traité est automatiquement transmis au backend via l'endpoint `/upload`. L'import du référentiel utilise quant à lui l'endpoint `/import`.

## Vérifications locales

Le projet fournit quelques commandes pour garder une base de code cohérente.

### Lint

Exécutez `npm run lint` après avoir installé les dépendances de développement (`npm install`). Sans ces packages, la commande peut échouer.

### Tests Python

Il n'existe pas encore de tests automatisés mais `pytest` est configuré pour unifier la procédure. Lancez simplement `pytest` pour vérifier qu'aucune erreur n'est remontée.

### Docker

Une configuration Docker est fournie pour lancer rapidement l'API Flask et la base PostgreSQL.

```bash
# Construire les images
make docker-build

# Démarrer l'environnement en arrière-plan
make docker-up

# Consulter les logs
make docker-logs

# Arrêter les conteneurs
make docker-down
```

Par défaut l'image utilise **Python 3.12** et **PostgreSQL 16**. La base de données est accessible sur `localhost:5432` et l'API Flask sur `localhost:5001`.
Le fichier `docker-compose.yml` définit également la variable `FRONTEND_URL` sur `http://localhost:5173`. Modifiez-la si votre application frontend tourne sur une autre URL afin que la politique CORS fonctionne correctement.
