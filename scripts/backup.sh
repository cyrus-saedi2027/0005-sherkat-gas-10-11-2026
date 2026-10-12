#!/usr/bin/env bash
# Periodic backup (R35, R42): PostgreSQL dump + uploaded files, rotated.
# cron:  15 2 * * *  /opt/gazyar/scripts/backup.sh >> /var/log/gazyar-backup.log 2>&1
set -euo pipefail
DEST="${BACKUP_DIR:-/var/backups/gazyar}"
KEEP_DAYS="${KEEP_DAYS:-14}"
COMPOSE="docker compose -f $(dirname "$0")/../deploy/docker-compose.yml"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$DEST"
$COMPOSE exec -T db pg_dump -U gazyar -Fc gazyar > "$DEST/db-$stamp.dump"
$COMPOSE exec -T api tar -C /srv/var -czf - uploads > "$DEST/uploads-$stamp.tgz"
# Fail loudly on an empty dump rather than rotating good backups away.
[ -s "$DEST/db-$stamp.dump" ] || { echo "empty dump"; exit 1; }
find "$DEST" -type f -mtime +"$KEEP_DAYS" -delete
echo "backup ok $stamp"
# Restore: pg_restore -U gazyar -d gazyar --clean db-<stamp>.dump ; tar -xzf uploads-<stamp>.tgz -C /srv/var
