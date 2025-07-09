# AJT PRO - Système de Tarification avec Panier

Application complète de gestion de tarifs avec système de panier et commande par email.

## Fonctionnalités

### 🔧 Étape 1 - Traitement des données
- Import de fichiers Excel
- Calculs automatiques (TCP, marges)
- Filtrage par marques
- Exclusion configurable de certains produits
- Nettoyage automatique et suppression des doublons
- Export des données traitées

### 🎨 Étape 2 - Mise en forme
- Génération de fichiers Excel formatés
- Création de pages web de consultation client
- Interface moderne avec design professionnel
- Publication en ligne

### 🛒 Système de panier
- Sélection de produits avec quantités
- Gestion complète du panier
- Formulaire de commande client
- Envoi automatique par email

### ⚙️ Administration
- Gestion des produits Hotwav
- Interface d'administration intuitive
- Ajout/modification/suppression de produits

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
│   ├── ProcessingPage.tsx      # Étape 1 - Traitement
│   ├── FormattingPage.tsx      # Étape 2 - Mise en forme
│   ├── HotwavAdmin.tsx         # Administration Hotwav
│   ├── QuantityModal.tsx       # Modal de sélection quantité
│   └── CartModal.tsx           # Modal du panier
├── contexts/
│   └── CartContext.tsx         # Gestion du panier
├── services/
│   └── emailService.ts         # Service d'envoi email
├── types/
│   └── cart.ts                 # Types TypeScript
└── App.tsx                     # Application principale
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

