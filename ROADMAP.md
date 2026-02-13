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

## Statistiques de prix

Module d'analyse graphique avec 11 types de visualisations :

| Graphique | Description |
|-----------|-------------|
| Vue globale | Evolution du prix moyen toutes marques/fournisseurs confondus |
| Prix moyen marque/fournisseur | Comparaison croisee marque x fournisseur |
| Prix moyen produit/fournisseur | Comparaison croisee produit x fournisseur |
| Evolution du produit | Courbe de prix d'un produit specifique dans le temps |
| Evolution relative (%) | Variation en pourcentage par rapport a une semaine de reference |
| Distribution des prix | Histogramme de la repartition des prix |
| Ecart-type par fournisseur | Mesure de la dispersion des prix par fournisseur |
| Prix min/max par semaine | Amplitude des prix sur chaque semaine |
| Indice des prix | Indice normalise pour comparer des gammes differentes |
| Correlation des prix | Analyse de la correlation entre fournisseurs |
| Anomalies detectees | Detection automatique des variations de prix inhabituelles |

Fonctionnalites transversales :
- **Filtres** par fournisseur, marque et produit
- **Activation/desactivation** de chaque type de graphique via les parametres (table `graph_settings`)

Composants concernes : `StatisticsPage`, `StatsFilters`, `PriceChart`, `BrandSupplierChart`, `ProductEvolutionChart`

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

- **Navbar** : logo AJT Pro, liens de navigation style pill (fond dore quand actif), menu deroulant Parametres anime avec separateur, responsive mobile (icones seules), sticky avec backdrop-blur
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

Fichiers concernes : `App.tsx`, `LoginPage.tsx`, `SearchPage.tsx`, `SearchControls.tsx`, `ProductsPage.tsx`, `AdminPage.tsx`, `DataImportPage.tsx`, `ReferenceAdmin.tsx`, `TranslationAdmin.tsx`, `UserAdmin.tsx`, `SupplierApiAdmin.tsx`, `StatisticsPage.tsx`, `StatsFilters.tsx`, `PriceChart.tsx`, `BrandSupplierChart.tsx`, `ProductEvolutionChart.tsx`, `FormattingPage.tsx`, `ProcessingPage.tsx`, `index.css`

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
- **Creation automatique** des references manquantes (marques, couleurs, etc.)
- **Rapports detailles** : produits crees, mis a jour, inchanges, supprimes, erreurs
- **Suppression des orphelins** : les produits lies a Odoo mais absents de la synchronisation sont supprimes physiquement (references fournisseurs detachees, calculs supprimes). Compteur orange et rapport detaille dans l'historique
- **Synchronisation manuelle** : bouton de declenchement dans l'interface
- **Synchronisation automatique** : planificateur configurable (intervalle minimum 15 min)
- **Historique** : suivi de tous les jobs de synchronisation avec rapports expansibles

Composants concernes : `OdooSyncPanel`, `DataImportPage`

---

## Tests automatises (implementee)

Infrastructure de tests unitaires et d'integration pour le backend et le frontend, integree dans la CI GitHub Actions.

### Backend (pytest)

- **Infrastructure** : SQLite in-memory, fixtures `admin_user`, `client_user`, `admin_headers`
- **Tests unitaires** : `utils/pricing.py` (seuils, TCP, marges, edge cases), `utils/auth.py` (JWT generation, decodage, expiration, decorator)
- **Tests d'integration** : routes `POST /login`, CRUD `/users`, CRUD `/products`, operations en masse (`bulk_update`, `bulk_delete`), routes Odoo (config, test connexion, sync, jobs, auto-sync)
- **71 tests** dans 6 fichiers
- **Zero warning applicatif** : `datetime.utcnow()` remplace par `datetime.now(timezone.utc)`, `Query.get()` remplace par `db.session.get()`, secret JWT >= 32 octets

### Frontend (Vitest + Testing Library)

- **Tests utils** : `date.ts`, `numbers.ts`, `text.ts`, `processing.ts`, `html.ts` (fonctions pures)
- **Tests composants** : `LoginPage`, `NotificationProvider`, `App` (rendu, formulaires, navigation conditionnelle)
- **108 tests** dans 11 fichiers

### CI/CD

- Jobs `frontend` et `backend` parallelises dans `.github/workflows/ci.yml`
- Tests executes automatiquement sur chaque push et pull request vers `main`
- **Job Summary** : recap des resultats (tests passes/echoues) affiche dans l'onglet Actions de GitHub
- **Deploy** (`.github/workflows/deploy.yml`) : deploiement automatique sur le VPS via SSH apres chaque push sur `main`
