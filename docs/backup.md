# Backup & Restore (on-prem)

Backup strategy for the pgvector database when the stack runs on-prem via
`docker-compose.yml`.

## Objectives

| | |
|---|---|
| **RPO** (max data loss) | 24h — one daily snapshot |
| **RTO** (time to restore) | data load + HNSW index rebuild; record from first drill |
| **Resilience** | 3-2-1 — local disk + NAS + off-site (encrypted) |

Embeddings are also re-derivable from the source markdown text (which the dump
contains), so a daily logical backup is sufficient. Point-in-time recovery
(WAL archiving) is intentionally out of scope at this RPO — see *Future*.

## What runs

- **`db-backup` service** (`prodrigestivill/postgres-backup-local:16`, in
  `docker-compose.yml`) — a scheduled `pg_dump` (gzipped plain SQL) on `@daily`
  with retention **7 daily / 5 weekly / 6 monthly**. Output lands in
  `./backups/{daily,weekly,monthly,last}/`.
- **`scripts/offsite-sync.sh`** — host cron job that copies `./backups` to the NAS
  (2nd copy) and pushes an **encrypted** copy of the newest daily dump off-site
  (3rd copy), with a `.sha256`.
- **`scripts/restore.sh`** — restores a dump into the `postgres` container.
- **`scripts/create-backup-role.sql`** — optional least-privilege `backup_ro` role.

```
postgres (pgvector) ──daily pg_dump──▶ ./backups (local)
                                          │  offsite-sync.sh (host cron)
                        ┌─────────────────┴─────────────────┐
                    rsync → NAS                    age-encrypt → rclone off-site
```

## Setup

1. Start the backup service:
   ```bash
   docker compose up -d db-backup
   ```
2. (Recommended) create the read-only role and point the service at it:
   ```bash
   # edit the password first
   docker compose exec -T postgres psql -U vec -d vec < scripts/create-backup-role.sql
   # then set POSTGRES_USER=backup_ro (+ its password) on db-backup and recreate it
   ```
3. Install host cron for off-site fan-out (after the nightly dump):
   ```cron
   30 2 * * *  cd /path/to/vec-manager && \
     BACKUP_DIR=./backups \
     NAS_DEST=/mnt/nas/vec-backups \
     OFFSITE_REMOTE=minio-dr:vec-backups \
     AGE_RECIPIENT=age1... \
     scripts/offsite-sync.sh >> /var/log/vec-backup.log 2>&1
   ```

### offsite-sync.sh environment

| Var | Meaning | Example |
|---|---|---|
| `BACKUP_DIR` | local backups dir | `./backups` |
| `NAS_DEST` | rsync target (NAS) | `/mnt/nas/vec-backups` or `user@nas:/vol/backups` |
| `OFFSITE_REMOTE` | rclone `remote:path` off-site | `minio-dr:vec-backups` |
| `AGE_RECIPIENT` / `AGE_RECIPIENTS_FILE` | age public key(s) for encryption | `age1qz...` |

Requires `rsync`, `age`, and `rclone` on the host. The **age private key** lives
off the host (or in a locked keystore) — without it the off-site copy is useless
to an attacker, but also un-restorable, so store it safely and separately.

## Restore

```bash
scripts/restore.sh ./backups/daily/vec-YYYYMMDD-HHMMSS.sql.gz            # into running DB
# or a specific target DB name:
scripts/restore.sh ./backups/daily/vec-....sql.gz vec
```

The script verifies the checksum + gzip integrity, then pipes the SQL into the
`postgres` container. Dumps are made with `--clean --if-exists`, so this DROPs and
recreates objects. Restore **into a pgvector image** — the dump runs
`CREATE EXTENSION IF NOT EXISTS vector`, and the HNSW index on
`embeddings_chunk.embedding` is rebuilt as part of restore (the slow step for
large tables).

An off-site copy is `.age`-encrypted; decrypt before restoring:
```bash
age -d -i /secure/age.key vec-....sql.gz.age > vec-....sql.gz
```

**Total-loss fallback (no vector backup):** restore only schema + the
`embeddings_markdown` rows (source text) and re-embed by calling the Celery
`embed_markdown` task per document — slower, but needs no vector data.

## Verification & drills

- **Every dump:** the off-site step writes a `.sha256`; `restore.sh` checks it and
  `gzip -t` before restoring.
- **Monthly drill:** restore the latest dump into a throwaway DB and run smoke
  checks — `SELECT count(*) FROM embeddings_chunk;` plus one similarity query
  (`ORDER BY embedding <=> :vec LIMIT 5`). Record the elapsed time here as the RTO
  baseline. Log each drill (date / dump / result / duration) below.

| Drill date | Dump | Result | Duration (RTO) |
|---|---|---|---|
| _tbd_ | | | |

## Monitoring / alerting

Alert on: backup job failure, **staleness** (newest local dump > 26h), off-site
sync failure, and low disk on `./backups` / NAS. Wire to the ops channel. PgHero
covers DB health but **not** backups — this is separate.

## Future

To tighten RPO below 24h: enable `archive_mode` + `archive_command`, adopt
**pgBackRest** (full + incremental + WAL → PITR), and keep this 3-2-1 layout.
