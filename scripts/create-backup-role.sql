-- Least-privilege role for backups (read-only across all tables).
-- Apply once:
--   docker compose exec -T postgres psql -U vec -d vec -f - < scripts/create-backup-role.sql
-- Then point the db-backup service at POSTGRES_USER=backup_ro.
--
-- Change the password before running.
CREATE ROLE backup_ro WITH LOGIN PASSWORD 'change-me';
GRANT pg_read_all_data TO backup_ro;
