#!/usr/bin/env bash
#
# Fan the local pg_dump backups out to a NAS (2nd copy) and an encrypted
# off-site target (3rd copy) — the "2" and "1" of the 3-2-1 rule.
#
# Run from HOST cron after the daily dump, e.g.:
#   30 2 * * *  /path/to/vec-manager/scripts/offsite-sync.sh >> /var/log/vec-backup.log 2>&1
#
# Config via environment (see .env.example):
#   BACKUP_DIR      local backups dir            (default: ./backups)
#   NAS_DEST        rsync destination for NAS    (e.g. /mnt/nas/vec-backups  or  user@nas:/vol/backups)
#   OFFSITE_REMOTE  rclone remote:path off-site  (e.g. minio-dr:vec-backups)
#   AGE_RECIPIENT   age public key to encrypt with (recipient), OR
#   AGE_RECIPIENTS_FILE  file of age recipients
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-$(cd "$(dirname "$0")/.." && pwd)/backups}"
NAS_DEST="${NAS_DEST:?set NAS_DEST}"
OFFSITE_REMOTE="${OFFSITE_REMOTE:?set OFFSITE_REMOTE}"

log() { printf '%s %s\n' "$(date -u +%FT%TZ)" "$*"; }

# --- 2nd copy: NAS (same site) -------------------------------------------------
log "rsync -> NAS ($NAS_DEST)"
rsync -a --delete "$BACKUP_DIR/" "$NAS_DEST/"

# --- checksum + encrypt the newest daily dump ---------------------------------
latest="$(ls -1t "$BACKUP_DIR"/daily/*.sql.gz 2>/dev/null | head -n1 || true)"
if [[ -z "${latest}" ]]; then
  log "ERROR: no daily *.sql.gz found in $BACKUP_DIR/daily"
  exit 1
fi
log "latest daily backup: $latest"
sha256sum "$latest" > "$latest.sha256"

age_args=()
if [[ -n "${AGE_RECIPIENTS_FILE:-}" ]]; then
  age_args=(-R "$AGE_RECIPIENTS_FILE")
elif [[ -n "${AGE_RECIPIENT:-}" ]]; then
  age_args=(-r "$AGE_RECIPIENT")
else
  log "ERROR: set AGE_RECIPIENT or AGE_RECIPIENTS_FILE to encrypt off-site copy"
  exit 1
fi
enc="$latest.age"
log "encrypt -> $enc"
age "${age_args[@]}" -o "$enc" "$latest"

# --- 3rd copy: off-site (encrypted only) --------------------------------------
log "rclone -> off-site ($OFFSITE_REMOTE)"
rclone copy "$enc" "$OFFSITE_REMOTE/daily/"
rclone copy "$latest.sha256" "$OFFSITE_REMOTE/daily/"

log "offsite-sync complete"
