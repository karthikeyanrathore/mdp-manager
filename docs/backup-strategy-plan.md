# Plan: On-Prem Backup Strategy for the pgvector Database

## Context

The service stores embeddings in Postgres 16 + pgvector (the `postgres` service in
`docker-compose.yml`, data in the `pgdata` volume). On-prem means **we own
recovery** — no managed-DB point-in-time restore to fall back on. We need a
documented, automated backup + restore strategy so a disk failure, bad migration,
or accidental `DELETE`/`DROP` doesn't lose project data.

**Confirmed parameters:**
- **RPO: 24h** → a **daily snapshot** is sufficient (losing ≤1 day is acceptable;
  embeddings are also re-derivable from the source markdown text, which the dump
  already contains).
- **Deployment:** the docker-compose pgvector container on the on-prem host.
- **Resilience:** full **3-2-1** — local disk + NAS + off-site copy.

## Strategy (overview)

Daily **logical backup** with `pg_dump` (custom format, `-Fc`), retained on the
host, then fanned out to NAS and off-site, encrypted before leaving the host.
Logical (not physical/WAL) is the right fit for a 24h RPO: portable across
minor/patch versions, easy partial restore, and simplest to operate in
docker-compose. PITR/WAL archiving is intentionally **out of scope** (see Future).

```
postgres (pgvector) ──pg_dump -Fc──▶ /backups (local, host disk)
                                        │
                        retention prune (daily/weekly/monthly)
                                        │
                    ┌───────────────────┴───────────────────┐
              rsync to NAS                        encrypt + rclone off-site
              (2nd copy, same site)               (3rd copy, other location)
```

## pgvector-specific considerations

- **Vector columns** dump/restore fine — `pg_dump` serializes `vector(384)` as
  text; no special handling.
- **Extension:** restore target must have the pgvector binary available, so always
  restore into a `pgvector/pgvector:pg16` container. The dump includes
  `CREATE EXTENSION IF NOT EXISTS vector`.
- **HNSW index rebuild:** `pg_restore` recreates the `chunk_emb_hnsw` index; for a
  large `embeddings_chunk` table this is the slow part of restore. Mitigation:
  restore with `--jobs` and, for big tables, restore data first then build the
  index — factor this into RTO.
- **Version parity:** restore onto the **same Postgres major (16)** and a pgvector
  version ≥ the source. Record both in each backup's metadata.

## Implementation

**1. Backup service (`docker-compose.yml`)** — add a `db-backup` service using
`prodrigestivill/postgres-backup-local` (scheduled `pg_dump -Fc` + built-in
daily/weekly/monthly retention), or an equivalent small cron+`pg_dump` container:
- env: `POSTGRES_HOST=postgres`, DB/user/password (reuse `.env`), `SCHEDULE=@daily`,
  `POSTGRES_EXTRA_OPTS=-Fc`, retention `BACKUP_KEEP_DAYS=7 / _WEEKS=5 / _MONTHS=6`.
- volume: `./backups:/backups`; `depends_on: postgres (healthy)`.
- Prefer a **read-only backup role** over the app superuser (create
  `backup_ro` with `pg_read_all_data`); document in the runbook.

**2. Off-site fan-out (`scripts/offsite-sync.sh`, host cron)** — after the daily
dump: `rsync` `/backups` → NAS mount, then **encrypt** newest dump (`age` or
`gpg`) and `rclone`/`rsync` to the off-site target (on-prem MinIO in another
building, or tape). Runs from host cron because containers shouldn't reach host
mounts/off-site creds. Writes a `.sha256` next to each artifact.

**3. Restore script (`scripts/restore.sh`)** — documented, parameterized:
spin up a fresh `pgvector/pgvector:pg16`, `createdb`, `pg_restore --clean
--if-exists --jobs=4 <dump>`, then verify (below).

**4. Config/docs**
- `.gitignore`: add `/backups/`.
- `.env.example`: backup vars (paths, retention, off-site target, encryption key ref).
- `docs/backup.md` (or README section): the runbook — schedule, retention, 3-2-1
  layout, restore steps, RTO/RPO, drill cadence.

## Retention & schedule

- **Schedule:** daily at a low-traffic hour (e.g. 02:00).
- **Retention:** 7 daily, 5 weekly, 6 monthly (tunable). Off-site keeps ≥ the
  monthly set. Prune enforced by the backup image + a NAS/off-site prune step.

## Security

- Encrypt any copy that leaves the host (`age`/`gpg`); store the key **out of the
  repo** (host keystore / secrets manager), never in `.env` committed to git.
- Lock down `/backups` perms (0700, owned by the backup user).
- Least-privilege `backup_ro` DB role.

## Restore runbook & RTO

Steps (also in `scripts/restore.sh`): pick a verified dump → start fresh pgvector
container → `pg_restore` → rebuild/verify HNSW → repoint the app.
- **RTO estimate:** dominated by data load + HNSW rebuild; record the measured time
  from the first drill and keep it in `docs/backup.md`.
- **Fallback for a total loss with only source data:** restore the schema + the
  `embeddings_markdown` rows (source text) and **re-run embedding** via the Celery
  `embed_markdown` task per document — slower but needs no vector backup.

## Verification & drills

- **Per backup:** `pg_restore --list <dump>` (integrity) + `sha256sum` check; fail
  the job (non-zero exit + alert) if either fails.
- **Monthly restore drill:** restore the latest dump into a throwaway container and
  run smoke checks — `SELECT count(*) FROM embeddings_chunk;` and one
  `ORDER BY embedding <=> :vec LIMIT 5` similarity query — to prove the backup is
  *usable*, not just present. Log drill results in `docs/backup.md`.

## Monitoring / alerting

- Alert on: backup job failure (exit code), **staleness** (newest local dump > 26h),
  off-site sync failure, and `/backups`/NAS disk-space thresholds.
- Wire to the existing ops channel (email/Slack/webhook). PgHero already covers DB
  health but **not** backups — keep this separate.

## Verification of the implementation (when built)

1. `docker-compose up -d postgres db-backup`; trigger a manual run and confirm a
   `*.sql.gz`/`*.dump` lands in `./backups` with a matching `.sha256`.
2. Run `scripts/offsite-sync.sh` (dry-run first) → confirm copies on NAS + off-site,
   encrypted.
3. Run `scripts/restore.sh` into a scratch container → smoke queries pass.
4. Simulate staleness (skip a day) → confirm the alert fires.

## Non-goals / future

- **PITR / WAL archiving** (pgBackRest or Barman) — not needed at 24h RPO; the
  upgrade path if RPO tightens is: enable `archive_mode` + `archive_command`,
  adopt pgBackRest for full+incremental+WAL, keep this 3-2-1 layout.
- No cross-region cloud replication (on-prem only by requirement).
