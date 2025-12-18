#!/bin/bash
# Backup local database before migration

BACKUP_DIR="backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/local_db_backup_$TIMESTAMP.sql"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "📦 Creating backup of local database..."
echo "Backup file: $BACKUP_FILE"

# Backup using pg_dump
pg_dump -h localhost -U postgres -d csi_kalamela > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Backup created successfully!"
    echo "📁 Location: $BACKUP_FILE"
    echo "💾 Size: $(du -h "$BACKUP_FILE" | cut -f1)"
else
    echo "❌ Backup failed!"
    exit 1
fi


