# Quick Start: Production Data Migration

## 🚀 Ready to Migrate? Follow These Steps:

### Step 1: Test Connection (30 seconds)
```bash
uv run python test_production_connection.py
```

**Expected output:**
```
✅ Connected successfully!
👤 Total users: 354
🏛️  Total districts: 12
🏢 Total units: 333
```

---

### Step 2: Backup Local Database (1 minute)
```bash
./backup_local_db.sh
```

**Expected output:**
```
✅ Backup created successfully!
📁 Location: backups/local_db_backup_20251208_HHMMSS.sql
```

---

### Step 3: Run Migration (5-10 minutes)
```bash
uv run python migrate_production_data.py
```

**You will see:**
1. Confirmation prompt - type `yes`
2. Progress for each table
3. Final summary with counts

**Expected summary:**
```
============================================================
📊 MIGRATION SUMMARY
============================================================
✅ Districts:        12
✅ Units:            333
✅ Users:            354
✅ Unit Members:     10,764
✅ Unit Officials:   293
✅ Unit Councilors:  564
============================================================
```

---

### Step 4: Verify Migration
```bash
# Quick check
uv run python -c "
from sqlalchemy import create_engine, text
engine = create_engine('postgresql+psycopg://postgres:postgres@localhost:5432/csi_kalamela')
with engine.connect() as conn:
    print('Users:', conn.execute(text('SELECT COUNT(*) FROM custom_user')).scalar())
    print('Districts:', conn.execute(text('SELECT COUNT(*) FROM clergy_district')).scalar())
    print('Units:', conn.execute(text('SELECT COUNT(*) FROM unit_name')).scalar())
    print('Members:', conn.execute(text('SELECT COUNT(*) FROM unit_members')).scalar())
"
```

---

### Step 5: Test Login
```bash
# Start the server
uv run uvicorn main:app --reload

# In another terminal, test login with a production user
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "test@example.com", "password": "password123"}'
```

---

## 🎯 What Gets Migrated

| Data Type | Count | Status |
|-----------|-------|--------|
| Clergy Districts | 12 | ✅ Ready |
| Units | 333 | ✅ Ready |
| Users | 354 | ✅ Ready |
| Unit Members | 10,764 | ✅ Ready |
| Unit Officials | 293 | ✅ Ready |
| Unit Councilors | 564 | ✅ Ready |
| Login Audit | Last 1000 | ✅ Ready |

---

## ⚠️  Important Notes

1. **Passwords:** All users keep their existing passwords (hashes are migrated)
2. **Tokens:** Users must log in again to get new JWT tokens
3. **Duplicate Prevention:** Script checks for existing records before inserting
4. **Rollback:** Backup is created - can restore if needed

---

## 🆘 Troubleshooting

### "Connection refused"
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql
sudo systemctl start postgresql
```

### "Foreign key violation"
- The script handles these automatically
- Check the summary for any errors

### Need to rollback?
```bash
# List backups
ls -lh backups/

# Restore
psql -h localhost -U postgres -d csi_kalamela < backups/local_db_backup_TIMESTAMP.sql
```

---

## 📚 Full Documentation

See `MIGRATION_GUIDE.md` for complete details, troubleshooting, and advanced options.

---

## ✅ After Migration

1. Update sequence counters (if needed)
2. Test user login with production credentials
3. Verify data in admin panel
4. All users need to log in again (new JWT system)

---

**Ready? Start with Step 1!** 🚀


