#!/bin/bash
# Complete Backup Script for Mnemosyne Production
# Backs up PostgreSQL, LightRAG data, and uploads

set -e

# Configuration
BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-7}

# Database connection
export PGPASSWORD="${POSTGRES_PASSWORD}"
DB_HOST="postgres"
DB_USER="${POSTGRES_USER}"
DB_NAME="${POSTGRES_DB}"

echo "[$(date)] Starting Mnemosyne backup..."

# Create backup directory
mkdir -p "${BACKUP_DIR}"/{postgres,lightrag,uploads}

# ============================================================================
# 1. PostgreSQL Backup (embeddings + metadata)
# ============================================================================
echo "[$(date)] Backing up PostgreSQL..."
POSTGRES_BACKUP="${BACKUP_DIR}/postgres/postgres_${TIMESTAMP}.sql.gz"

pg_dump -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}" \
    --verbose \
    --format=custom \
    --compress=9 \
    --file="${POSTGRES_BACKUP%.gz}" \
    2>&1 | tee "${BACKUP_DIR}/postgres/backup_${TIMESTAMP}.log"

gzip "${POSTGRES_BACKUP%.gz}"

if [ -f "${POSTGRES_BACKUP}" ]; then
    SIZE=$(du -h "${POSTGRES_BACKUP}" | cut -f1)
    echo "[$(date)] ✓ PostgreSQL backup: ${SIZE}"
else
    echo "[$(date)] ✗ PostgreSQL backup failed!"
    exit 1
fi

# ============================================================================
# 2. LightRAG Backup (knowledge graph)
# ============================================================================
echo "[$(date)] Backing up LightRAG knowledge graph..."
LIGHTRAG_DIR="/app/data/lightrag"
LIGHTRAG_BACKUP="${BACKUP_DIR}/lightrag/lightrag_${TIMESTAMP}.tar.gz"

if [ -d "${LIGHTRAG_DIR}" ]; then
    tar -czf "${LIGHTRAG_BACKUP}" -C /app/data lightrag \
        2>&1 | tee -a "${BACKUP_DIR}/lightrag/backup_${TIMESTAMP}.log"

    if [ -f "${LIGHTRAG_BACKUP}" ]; then
        SIZE=$(du -h "${LIGHTRAG_BACKUP}" | cut -f1)
        echo "[$(date)] ✓ LightRAG backup: ${SIZE}"
    else
        echo "[$(date)] ⚠ LightRAG backup failed (may not exist yet)"
    fi
else
    echo "[$(date)] ⚠ LightRAG directory not found (skipping)"
fi

# ============================================================================
# 3. Uploads Backup (original files)
# ============================================================================
echo "[$(date)] Backing up uploaded files..."
UPLOADS_DIR="/app/uploads"
UPLOADS_BACKUP="${BACKUP_DIR}/uploads/uploads_${TIMESTAMP}.tar.gz"

if [ -d "${UPLOADS_DIR}" ] && [ "$(ls -A ${UPLOADS_DIR})" ]; then
    tar -czf "${UPLOADS_BACKUP}" -C /app uploads \
        2>&1 | tee -a "${BACKUP_DIR}/uploads/backup_${TIMESTAMP}.log"

    if [ -f "${UPLOADS_BACKUP}" ]; then
        SIZE=$(du -h "${UPLOADS_BACKUP}" | cut -f1)
        echo "[$(date)] ✓ Uploads backup: ${SIZE}"
    else
        echo "[$(date)] ⚠ Uploads backup failed"
    fi
else
    echo "[$(date)] ⚠ No uploads to backup"
fi

# ============================================================================
# 4. Cleanup old backups
# ============================================================================
echo "[$(date)] Cleaning up backups older than ${RETENTION_DAYS} days..."

find "${BACKUP_DIR}/postgres" -name "postgres_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
find "${BACKUP_DIR}/lightrag" -name "lightrag_*.tar.gz" -mtime +${RETENTION_DAYS} -delete
find "${BACKUP_DIR}/uploads" -name "uploads_*.tar.gz" -mtime +${RETENTION_DAYS} -delete
find "${BACKUP_DIR}" -name "backup_*.log" -mtime +${RETENTION_DAYS} -delete

# ============================================================================
# 5. Create backup manifest
# ============================================================================
MANIFEST="${BACKUP_DIR}/manifest_${TIMESTAMP}.txt"
cat > "${MANIFEST}" <<MANIFEST_EOF
Mnemosyne Backup Manifest
========================
Timestamp: ${TIMESTAMP}
Date: $(date)

PostgreSQL Backup:
  File: postgres/postgres_${TIMESTAMP}.sql.gz
  Size: $(du -h "${POSTGRES_BACKUP}" 2>/dev/null | cut -f1 || echo "N/A")

LightRAG Backup:
  File: lightrag/lightrag_${TIMESTAMP}.tar.gz
  Size: $(du -h "${LIGHTRAG_BACKUP}" 2>/dev/null | cut -f1 || echo "N/A")

Uploads Backup:
  File: uploads/uploads_${TIMESTAMP}.tar.gz
  Size: $(du -h "${UPLOADS_BACKUP}" 2>/dev/null | cut -f1 || echo "N/A")

Total Backup Size: $(du -sh "${BACKUP_DIR}" | cut -f1)
MANIFEST_EOF

echo "[$(date)] Created manifest: ${MANIFEST}"

# ============================================================================
# 6. Optional: Upload to S3
# ============================================================================
if [ -n "${BACKUP_S3_BUCKET}" ]; then
    echo "[$(date)] Uploading backups to S3..."

    # Upload all backups for this timestamp
    aws s3 sync "${BACKUP_DIR}" "s3://${BACKUP_S3_BUCKET}/mnemosyne-backups/" \
        --exclude "*" \
        --include "*${TIMESTAMP}*" \
        2>&1 | tee -a "${BACKUP_DIR}/s3_upload_${TIMESTAMP}.log"

    echo "[$(date)] ✓ S3 upload complete"
fi

# ============================================================================
# 7. Summary
# ============================================================================
echo ""
echo "=========================================="
echo "BACKUP COMPLETE"
echo "=========================================="
echo "Timestamp: ${TIMESTAMP}"
echo ""
echo "Current backups:"
echo "  PostgreSQL: $(ls -1 ${BACKUP_DIR}/postgres/postgres_*.sql.gz 2>/dev/null | wc -l) backups"
echo "  LightRAG:   $(ls -1 ${BACKUP_DIR}/lightrag/lightrag_*.tar.gz 2>/dev/null | wc -l) backups"
echo "  Uploads:    $(ls -1 ${BACKUP_DIR}/uploads/uploads_*.tar.gz 2>/dev/null | wc -l) backups"
echo ""
echo "Total size: $(du -sh ${BACKUP_DIR} | cut -f1)"
echo "Retention:  ${RETENTION_DAYS} days"
echo "=========================================="
