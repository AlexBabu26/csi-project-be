# Production Data Migration Guide

## Overview

This guide explains how to migrate data from the production Django database (Neon) to the new FastAPI database (local PostgreSQL).

## What Will Be Migrated

- ✅ **Clergy Districts** - All districts
- ✅ **Unit Names** - All units
- ✅ **Users** - All user accounts (with existing password hashes)
- ✅ **Unit Registration Data** - Registration status
- ✅ **Unit Details** - Registration year, member counts
- ✅ **Unit Members** - All unit members with personal details
- ✅ **Unit Officials** - President, VP, Secretary, Joint Secretary, Treasurer
- ✅ **Unit Councilors** - All councilors
- ✅ **Login Audit Logs** - Last 1000 login attempts

## Pre-Migration Checklist

### 1. Verify Database Connections

**Production (Neon):**
```bash
psql 'postgresql://neondb_owner:npg_mcp40TxrFHVC@ep-round-waterfall-a13doc66-pooler.ap-southeast-1.aws.neon.tech/csi_youth_db?sslmode=require'
```

**Local (Development):**
```bash
psql -h localhost -U postgres -d csi_kalamela
```

### 2. Backup Local Database

**IMPORTANT:** Always backup before migration!

```bash
./backup_local_db.sh
```

This creates a timestamped backup in `backups/` directory.

### 3. Ensure Local Database is Up-to-Date

Run all migrations first:

```bash
uv run alembic upgrade head
```

## Running the Migration

### Step 1: Install Dependencies (if needed)

The migration script uses SQLAlchemy which is already installed.

### Step 2: Run Migration Script

```bash
uv run python migrate_production_data.py
```

**The script will:**
1. Show you what databases it will connect to
2. Ask for confirmation
3. Inspect production tables
4. Migrate data in correct order (respecting foreign keys)
5. Show progress for each table
6. Display final summary

### Step 3: Verify Migration

After migration, verify the data:

```bash
# Check user count
psql -h localhost -U postgres -d csi_kalamela -c "SELECT COUNT(*) FROM custom_user;"

# Check districts
psql -h localhost -U postgres -d csi_kalamela -c "SELECT * FROM clergy_district;"

# Check units
psql -h localhost -U postgres -d csi_kalamela -c "SELECT COUNT(*) FROM unit_name;"

# Check unit members
psql -h localhost -U postgres -d csi_kalamela -c "SELECT COUNT(*) FROM unit_members;"
```

## Migration Order

The migration follows this order to respect foreign key constraints:

1. **Clergy Districts** (no dependencies)
2. **Unit Names** (depends on districts)
3. **Users** (depends on units and districts)
4. **Unit Data** (depends on users)
   - Registration data
   - Unit details
   - Members
   - Officials
   - Councilors
5. **Login Audit** (depends on users)

## Post-Migration Tasks

### 1. Update Sequences

After migration, you may need to update PostgreSQL sequences:

```sql
SELECT setval('clergy_district_id_seq', (SELECT MAX(id) FROM clergy_district));
SELECT setval('unit_name_id_seq', (SELECT MAX(id) FROM unit_name));
SELECT setval('custom_user_id_seq', (SELECT MAX(id) FROM custom_user));
SELECT setval('unit_members_id_seq', (SELECT MAX(id) FROM unit_members));
```

### 2. Test User Login

Try logging in with a production user:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user@example.com", "password": "production_password"}'
```

**Note:** Users will use their existing passwords. The password hashes are migrated as-is.

### 3. Invalidate Old Sessions

Since we migrated to a new JWT system, all users will need to log in again to get new tokens.

## Troubleshooting

### Connection Issues

**Error:** "Connection refused"
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Start if not running
sudo systemctl start postgresql
```

**Error:** "Authentication failed"
```bash
# Update .env file with correct credentials
# For local: DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/csi_kalamela
```

### Foreign Key Violations

If you get foreign key errors, the migration script will skip those records and continue. Check the summary for errors.

### Duplicate Key Errors

The script checks for existing records before inserting. If you run it multiple times, it will skip existing records.

## Rollback

If something goes wrong, restore from backup:

```bash
# List available backups
ls -lh backups/

# Restore from backup
psql -h localhost -U postgres -d csi_kalamela < backups/local_db_backup_YYYYMMDD_HHMMSS.sql
```

## Data Not Migrated

The following data is **NOT** migrated (will be added in future):

- ❌ Conference data (tables may not exist yet)
- ❌ Kalamela event data (tables may not exist yet)
- ❌ Refresh tokens (users need to log in again)
- ❌ Change request history (can be added if needed)

## Security Notes

1. **Passwords:** Password hashes are migrated as-is. Users keep their existing passwords.
2. **Tokens:** No tokens are migrated. Users must log in again.
3. **Credentials:** Production credentials are stored in `.env.production` (gitignored)
4. **Backups:** Store backups securely and don't commit them to git

## Support

If you encounter issues:
1. Check the error message in the terminal
2. Verify both database connections work independently
3. Check the migration summary for which tables failed
4. Review the `errors` list in the summary

## Example Output

```
============================================================
🚀 DATA MIGRATION: Production → Local
============================================================

⚠️  WARNING: This will import data from production database
📍 Production: Neon Database (csi_youth_db)
📍 Local: postgresql+psycopg://postgres:postgres@localhost:5432/csi_kalamela

Do you want to continue? (yes/no): yes

🔌 Connecting to databases...
✅ Connected to both databases

📋 Inspecting production database schema...

Found 25 tables in production:
  - auth_app_clergydistrict
  - auth_app_customuser
  - auth_app_loginaudit
  - auth_app_unitname
  - auth_app_unitmembers
  ...

🏛️  Migrating clergy districts...
✅ Migrated 12 districts

🏢 Migrating unit names...
✅ Migrated 156 units

👤 Migrating users...
✅ Migrated 234 users

📝 Migrating unit data...
✅ Migrated unit data:
   - 2,341 members
   - 156 officials
   - 312 councilors

📊 Migrating login audit logs...
✅ Migrated 1000 login audit logs

============================================================
📊 MIGRATION SUMMARY
============================================================
✅ Districts:        12
✅ Units:            156
✅ Users:            234
✅ Unit Members:     2,341
✅ Unit Officials:   156
✅ Unit Councilors:  312
============================================================

✅ Migration completed successfully!
```


