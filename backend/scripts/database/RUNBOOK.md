# Runbook — Scripts base de données

Tous les scripts se lancent via Docker :
```bash
docker exec -it ajt_backend_prod python scripts/database/<script>.py [args]
```

---

## Comptes utilisateurs

### Modifier l'email d'un utilisateur
```bash
docker exec -it ajt_backend_prod python scripts/database/update_admin_email.py --email nouveau@email.com
docker exec -it ajt_backend_prod python scripts/database/update_admin_email.py --email nouveau@email.com --username client
```

### Lister / reset les emails (admin + client)
```bash
docker exec -it ajt_backend_prod python scripts/database/users.py
```
> Remet `admin@admin` et `client@client` — à n'utiliser qu'en dev.

---

## Import de données

### Importer les produits de référence (Odoo 24/10/2025)
```bash
docker exec -it ajt_backend_prod python scripts/database/import_reference_products_odoo_20251024.py
```

### Ajouter les références import 23/09/2025
```bash
docker exec -it ajt_backend_prod python scripts/database/add_references_import_2025_0923.py
```

### RAM / normes
```bash
docker exec -it ajt_backend_prod python scripts/database/ram_norme.py
```

---

## Reset Odoo

### Reset complet (produits + matchs + calculs)
```bash
docker exec -it ajt_backend_prod python scripts/reset_odoo_full.py
docker exec -it ajt_backend_prod python scripts/reset_odoo_full.py --dry-run
```

### Reset liens uniquement (sans supprimer les produits)
```bash
docker exec -it ajt_backend_prod python scripts/reset_odoo_links.py
```

---

## Fixes matching LLM (one-time)

### Fix auto-matchs avec région incorrecte (null ≠ EU)
```bash
docker exec -it ajt_backend_prod python scripts/fix_region_null_matches.py
docker exec -it ajt_backend_prod python scripts/fix_region_null_matches.py --dry-run
```

### Remettre les pending matches EU dans le pipe de re-scoring
```bash
docker exec -it ajt_backend_prod python scripts/repromote_region_pending.py
docker exec -it ajt_backend_prod python scripts/repromote_region_pending.py --dry-run
```
