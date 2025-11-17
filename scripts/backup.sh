#!/bin/bash
# PostgreSQL Backup Script for Production

set -e

# Configuration
BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="mnemosyne_backup_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-7}

# Database connection
export PGPASSWORD="${POSTGRES_PASSWORD}"
DB_HOST="postgres"
DB_USER="${POSTGRES_USER}"
DB_NAME="${POSTGRES_DB}"

echo "[$(date)] Starting PostgreSQL backup..."

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Perform backup
pg_dump -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}" \
    --verbose \
    --format=custom \
    --compress=9 \
    --file="${BACKUP_DIR}/${BACKUP_FILE%.gz}" \
    2>&1 | tee "${BACKUP_DIR}/backup_${TIMESTAMP}.log"

# Compress backup
gzip "${BACKUP_DIR}/${BACKUP_FILE%.gz}"

# Verify backup
if [ -f "${BACKUP_DIR}/${BACKUP_FILE}" ]; then
    SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1)
    echo "[$(date)] Backup completed successfully: ${BACKUP_FILE} (${SIZE})"
else
    echo "[$(date)] ERROR: Backup file not created!"
    exit 1
fi

# Clean up old backups
echo "[$(date)] Cleaning up backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "mnemosyne_backup_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
find "${BACKUP_DIR}" -name "backup_*.log" -mtime +${RETENTION_DAYS} -delete

# List remaining backups
echo "[$(date)] Current backups:"
ls -lh "${BACKUP_DIR}"/mnemosyne_backup_*.sql.gz

# Optional: Upload to S3 (uncomment if using)
# if [ -n "${BACKUP_S3_BUCKET}" ]; then
#     echo "[$(date)] Uploading to S3..."
#     aws s3 cp "${BACKUP_DIR}/${BACKUP_FILE}" \
#         "s3://${BACKUP_S3_BUCKET}/backups/${BACKUP_FILE}"
# fi

echo "[$(date)] Backup process completed!"
