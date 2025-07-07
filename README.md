# AJT PRO - Système de Tarification avec Panier

Application complète de gestion de tarifs avec système de panier et commande par email.

## Fonctionnalités

### 🔧 Étape 1 - Traitement des données
- Import de fichiers Excel
- Calculs automatiques (TCP, marges)
- Filtrage par marques
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

Créez un fichier `.env` à la racine du projet avec vos identifiants Supabase&nbsp;:

```bash
VITE_SUPABASE_URL=<votre_url_supabase>
VITE_SUPABASE_ANON_KEY=<votre_cle_anon>
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

Un backend minimal en **Python** est fourni dans le dossier `backend`. Il utilise **Flask** et **SQLite** pour stocker les produits traités.

### Installation et lancement

```bash
cd backend
make venv   # crée l'environnement virtuel et installe les dépendances
make run    # démarre l'API Flask
```

L'application expose notamment les routes :

- `GET /products` : liste l'ensemble des produits en base.
- `POST /products` : ajout d'un produit au format JSON.
- `POST /upload` : envoi d'un fichier Excel pour importer plusieurs produits.

Dans l'application React, le fichier traité est automatiquement transmis au backend via l'endpoint `/upload`.

