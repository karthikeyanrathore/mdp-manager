#!/usr/bin/env bash
#
# Restore a pg_dump (gzipped or plain SQL) into the pgvector database.
#
# Usage:
#   scripts/restore.sh <path-to-backup.sql.gz> [db_name]
#
# The dumps are plain-SQL, gzipped, and created with --clean --if-exists, so this
# DROPs and recreates the objects in the target DB. The dump includes
# `CREATE EXTENSION IF NOT EXISTS vector`, so restore into a pgvector image.
#
# By default it restores into the running compose `postgres` service. Set
# RESTORE_INTO=scratch to instead restore into a throwaway container (drill).
set -euo pipefail

# Guard against an unquoted glob (e.g. vec-*.sql.gz) expanding to several files,
# which would silently turn the 2nd match into the "db name".
if [[ $# -gt 2 ]]; then
  echo "error: too many arguments ($#). Pass exactly ONE backup file." >&2
  echo "  (a glob like vec-*.sql.gz can match multiple files + the -latest symlink)" >&2
  exit 1
fi

BACKUP_FILE="${1:?usage: restore.sh <backup.sql.gz> [db_name]}"
DB_NAME="${2:-vec}"
DB_USER="${DB_USER:-vec}"

# A db name should not look like a file path.
if [[ "$DB_NAME" == */* || "$DB_NAME" == *.sql* ]]; then
  echo "error: db name '$DB_NAME' looks like a file path, not a database." >&2
  exit 1
fi

[[ -f "$BACKUP_FILE" ]] || { echo "no such file: $BACKUP_FILE" >&2; exit 1; }

# Optional integrity check if a sidecar .sha256 exists.
if [[ -f "$BACKUP_FILE.sha256" ]]; then
  echo "verifying checksum..."
  sha256sum -c "$BACKUP_FILE.sha256"
fi
# Detect the real format by magic bytes — the dump may be gzipped or plain SQL
# (the backup image does not always compress, despite the .sql.gz name).
if gzip -t "$BACKUP_FILE" 2>/dev/null; then
  echo "format: gzip (verified)"
  reader=(gunzip -c "$BACKUP_FILE")
else
  echo "format: plain SQL (not gzip)"
  reader=(cat "$BACKUP_FILE")
fi

echo "WARNING: this overwrites data in DB '$DB_NAME'. Ctrl-C within 5s to abort."
sleep 5

echo "restoring $BACKUP_FILE -> $DB_NAME ..."
"${reader[@]}" | docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U "$DB_USER" -d "$DB_NAME"

echo "restore complete. Smoke check:"
docker compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" \
  -c "SELECT count(*) AS chunks FROM embeddings_chunk;"
