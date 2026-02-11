# Roadmap AJT PRO

Ce document recense les fonctionnalites prevues pour les prochaines versions. Le code backend et frontend existe deja pour la plupart de ces modules ; il reste a les activer dans la navigation et a les valider en conditions reelles.

---

## Tableau referentiel produit

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

## Synchronisation API fournisseurs

Page dediee a l'import et au suivi des donnees fournisseurs :

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
