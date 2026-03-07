# Module Matching LLM — Documentation technique

## Vue d'ensemble

Le matching LLM rapproche automatiquement les labels fournisseurs avec les produits du référentiel Odoo. Il fonctionne en 2 phases :

1. **Phase 1 — Extraction** : Claude Haiku extrait les attributs structurés de chaque label fournisseur
2. **Phase 2 — Scoring** : Chaque produit Odoo est comparé aux extractions pour trouver le meilleur match

## Attributs extraits (12)

| # | Attribut | Type | Description |
|---|----------|------|-------------|
| 1 | `brand` | string | Marque identifiée parmi les marques connues |
| 2 | `model_family` | string | Nom commercial SANS marque, stockage, couleur |
| 3 | `storage` | string/null | Capacité stockage normalisée en "Go" |
| 4 | `color` | string/null | Couleur normalisée en français |
| 5 | `device_type` | string | Smartphone, Tablette, Accessoire, Audio, etc. |
| 6 | `region` | string | "EU" par défaut, "US", "IN", "DE", etc. Jamais null |
| 7 | `connectivity` | string/null | "WiFi", "Cellular", "5G", null |
| 8 | `grade` | string/null | A, B, C si mentionné |
| 9 | `confidence` | float | Score de confiance LLM (0.0-1.0) |
| 10 | `ram` | string/null | RAM en "Go" si mentionnée séparément du stockage |
| 11 | `dual_sim` | bool | true si Dual SIM / DS détecté |
| 12 | `enterprise_edition` | bool | true si Enterprise Edition / EE détecté |

## Scoring (0-100 pts)

| Composant | Points | Type |
|-----------|--------|------|
| Brand | 15 | Hard disqualifier si mismatch |
| Device Type | 0 | Hard disqualifier si mismatch |
| Storage | 25 | Hard disqualifier si mismatch |
| Model Family | 0-45 | Fuzzy matching (ratio ≥0.6) |
| Model Variant | 0 | Hard disqualifier si suffixe diffère (Pro/Plus/Ultra/Max/Lite/FE/FE+/Mini/S) |
| Color | 15 | Hard disqualifier si mismatch |
| Enterprise Edition | -20 | Soft malus si mismatch |
| Dual SIM | -10 | Soft malus si mismatch |
| Region | ×0/×1 | Gate (mismatch → score 0) |
| Label similarity | ±10 | Bonus/malus fuzzy sur le label brut |

**Seuils** : ≥90 → auto-match, 50-89 → pending review, <50 → not found

## Post-traitement regex (`_apply_post_processing`)

Après l'extraction LLM, un post-traitement déterministe enrichit/corrige les attributs via regex. Cela rattrape les patterns que le LLM peut manquer :

| Pattern | Champ enrichi | Exemple |
|---------|--------------|---------|
| `enterprise edition` | `enterprise_edition = True` | "Galaxy A36 Enterprise Edition" |
| `EE` (isolé) | `enterprise_edition = True` | "S25 5G 256GB EE Silver" |
| `dual sim` | `dual_sim = True` | "Galaxy A16 Dual Sim 128GB" |
| `DS` (isolé) | `dual_sim = True` | "Galaxy A07 DS 64GB" |
| `Xgb ram Ygb` | `ram = "X Go"` | "6GB RAM 128GB" → ram="6 Go" |
| `X/Ygb` | `ram = "X Go"` | "12/256GB" → ram="12 Go" |
| `{W}` ou `w` isolé | `connectivity = "WiFi"` | "Tab S10 128Go W EU" |
| `tablet ` préfixe | `device_type = "Tablette"` | "Tablet Samsung Galaxy Tab..." |
| `watch ` préfixe | `device_type = "Montre"` | "Watch Samsung Galaxy Watch..." |

## Nettoyage model (`_clean_model_for_scoring`)

Avant le fuzzy matching du model_family, les deux côtés (extraction + produit) sont nettoyés symétriquement :

- Stockage : `128GB`, `256 Go`, `1 To` → supprimé
- RAM/Storage combiné : `12/128GB`, `6gb ram` → supprimé
- Enterprise Edition / EE → supprimé
- Dual SIM / DS → supprimé
- Region : `Indian Spec`, `US Spec`, `(DE)` → supprimé
- Connectivity : `5G`, `4G`, `LTE`, `WiFi` → supprimé
- Parenthèses vides, espaces multiples → nettoyés

## Conventions par fournisseur

### einsAmobile (Ensa) — Labels compacts

| Convention | Exemple | Signification |
|-----------|---------|---------------|
| `W` ou `w` suffixe | `tab s10 lite 128go silver w eu` | WiFi |
| `EU` / `DE` suffixe | `256go black eu` | Région |
| Pas de marqueur | `iphone 16 256gb black` | EU par défaut |
| `EE` suffixe | `s25 5g 256gb ee silver` | Enterprise Edition |
| Stockage seul | `256go` | Pas de RAM dans le label |

### Yuka — Labels verbeux

| Convention | Exemple | Signification |
|-----------|---------|---------------|
| `Dual Sim` explicite | `galaxy a16 dual sim 128gb` | Dual SIM |
| `Xgo ram Ygo` | `12go ram 512go` | RAM + Stockage séparés |
| `Enterprise Edition` | `s26 12go ram 512go enterprise edition` | EE en toutes lettres |
| `WiFi` | `tab x400 wifi 256go` | Connectivité |
| Préfixes catégorie | `tablet`, `watch`, `laptop` | Type d'appareil |
| `region west` | `watch 7 lte region west` | Région |
