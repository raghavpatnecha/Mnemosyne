#!/bin/bash
# Restore Mnemosyne from backup

set -e

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <timestamp>"
    echo "Example: $0 20240117_120000"
    echo ""
    echo "Available backups:"
    ls -1 /backups/manifest_*.txt 2>/dev/null | sed 's/.*manifest_/  /' | sed 's/.txt$//' || echo "  No backups found"
    exit 1
fi

TIMESTAMP=$1
BACKUP_DIR="/backups"

# Database connection
export PGPASSWORD="${POSTGRES_PASSWORD}"
DB_HOST="postgres"
DB_USER="${POSTGRES_USER}"
DB_NAME="${POSTGRES_DB}"

echo "=========================================="
echo "Mnemosyne Restore"
echo "=========================================="
echo "Timestamp: ${TIMESTAMP}"
echo ""

# Check if backup exists
if [ ! -f "${BACKUP_DIR}/manifest_${TIMESTAMP}.txt" ]; then
    echo "ERROR: Backup manifest not found for timestamp ${TIMESTAMP}"
    exit 1
fi

# Show manifest
cat "${BACKUP_DIR}/manifest_${TIMESTAMP}.txt"
echo ""

read -p "Do you want to proceed with restore? This will REPLACE all data! (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled"
    exit 0
fi

# ============================================================================
# 1. Restore PostgreSQL
# ============================================================================
POSTGRES_BACKUP="${BACKUP_DIR}/postgres/postgres_${TIMESTAMP}.sql.gz"

if [ -f "${POSTGRES_BACKUP}" ]; then
    echo ""
    echo "[$(date)] Restoring PostgreSQL..."

    # Drop and recreate database (DANGEROUS!)
    psql -h "${DB_HOST}" -U "${DB_USER}" -c "DROP DATABASE IF EXISTS ${DB_NAME};"
    psql -h "${DB_HOST}" -U "${DB_USER}" -c "CREATE DATABASE ${DB_NAME};"

    # Restore
    gunzip -c "${POSTGRES_BACKUP}" | pg_restore -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}" --verbose

    echo "[$(date)] ✓ PostgreSQL restored"
else
    echo "[$(date)] ⚠ PostgreSQL backup not found, skipping"
fi

# ============================================================================
# 2. Restore LightRAG
# ============================================================================
LIGHTRAG_BACKUP="${BACKUP_DIR}/lightrag/lightrag_${TIMESTAMP}.tar.gz"

if [ -f "${LIGHTRAG_BACKUP}" ]; then
    echo ""
    echo "[$(date)] Restoring LightRAG knowledge graph..."

    # Remove existing data
    rm -rf /app/data/lightrag/*

    # Extract backup
    tar -xzf "${LIGHTRAG_BACKUP}" -C /app/data

    echo "[$(date)] ✓ LightRAG restored"
else
    echo "[$(date)] ⚠ LightRAG backup not found, skipping"
fi

# ============================================================================
# 3. Restore Uploads
# ============================================================================
UPLOADS_BACKUP="${BACKUP_DIR}/uploads/uploads_${TIMESTAMP}.tar.gz"

if [ -f "${UPLOADS_BACKUP}" ]; then
    echo ""
    echo "[$(date)] Restoring uploaded files..."

    # Remove existing uploads
    rm -rf /app/uploads/*

    # Extract backup
    tar -xzf "${UPLOADS_BACKUP}" -C /app

    echo "[$(date)] ✓ Uploads restored"
else
    echo "[$(date)] ⚠ Uploads backup not found, skipping"
fi

echo ""
echo "=========================================="
echo "RESTORE COMPLETE"
echo "=========================================="
echo "Please restart all services:"
echo "  docker-compose -f docker-compose.prod.yml restart"
echo "=========================================="
