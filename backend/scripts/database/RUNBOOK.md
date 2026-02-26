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

---

## Requêtes SQL directes

Toutes les requêtes SQL se lancent via le container PostgreSQL :
```bash
docker exec postgres_prod psql -U $(grep POSTGRES_USER .env | cut -d= -f2) -d $(grep POSTGRES_DB .env | cut -d= -f2) -c "<SQL>"
```

### Nettoyer les nightly jobs orphelins (status "running" bloqué)
```bash
docker exec postgres_prod psql -U $(grep POSTGRES_USER .env | cut -d= -f2) -d $(grep POSTGRES_DB .env | cut -d= -f2) -c "
UPDATE nightly_jobs SET status='failed', finished_at=NOW(), error_message='Manually cancelled' WHERE status='running';"
```

### Supprimer les nightly jobs en doublon (garder le meilleur par créneau)
Garde le job `completed` en priorité, sinon le premier par id. Supprime les doublons sur le même créneau (minute).
```bash
docker exec postgres_prod psql -U $(grep POSTGRES_USER .env | cut -d= -f2) -d $(grep POSTGRES_DB .env | cut -d= -f2) -c "
DELETE FROM nightly_jobs WHERE id IN (
  SELECT id FROM (
    SELECT id, ROW_NUMBER() OVER (
      PARTITION BY date_trunc('minute', started_at)
      ORDER BY CASE status WHEN 'completed' THEN 0 ELSE 1 END, id
    ) AS rn
    FROM nightly_jobs
  ) ranked WHERE rn > 1
);"
```

### Lister les nightly jobs récents
```bash
docker exec postgres_prod psql -U $(grep POSTGRES_USER .env | cut -d= -f2) -d $(grep POSTGRES_DB .env | cut -d= -f2) -c "
SELECT id, started_at, status, odoo_synced, suppliers_synced, matching_submitted, email_sent
FROM nightly_jobs ORDER BY id DESC LIMIT 20;"
```

### Vérifier les permissions du volume logs
```bash
docker run --rm -v ajtpro_ajtpro_backend_logs:/logs alpine ls -la /logs/
```

### Fixer les permissions du volume logs (si PermissionError)
```bash
docker run --rm -v ajtpro_ajtpro_backend_logs:/logs alpine chown -R 1000:1000 /logs
docker compose -f docker-compose.prod.yml restart backend
```
