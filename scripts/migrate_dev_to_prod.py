"""
Data migration script from Development Neon DB to Production Neon DB.
Full sync - truncates production tables and copies all data from development.

Usage:
    python scripts/migrate_dev_to_prod.py --yes
"""

import os
import sys
import io
import time
from datetime import datetime
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# Fix Windows console encoding for Unicode
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Development database (source)
DEV_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://neondb_owner:npg_mcp40TxrFHVC@ep-snowy-heart-a1z65pya-pooler.ap-southeast-1.aws.neon.tech/csi_youth_db?sslmode=require"
)

# Production database (target)
PROD_DB_URL = os.getenv(
    "PROD_DATABASE_URL",
    "postgresql://neondb_owner:npg_mcp40TxrFHVC@ep-round-waterfall-a13doc66-pooler.ap-southeast-1.aws.neon.tech/csi_youth_db?sslmode=require"
)

# Tables in correct order (respecting foreign key dependencies)
# These are the FastAPI table names that exist in BOTH databases
ORDERED_TABLES = [
    # Base tables (no foreign keys)
    "clergy_district",
    "site_settings",
    "notices",  # Note: plural in actual DB
    "quick_links",  # Note: plural in actual DB
    "event_category",
    "kalamela_rules",
    
    # Unit hierarchy
    "unit_name",
    
    # Users (depends on unit_name, clergy_district)
    "custom_user",
    
    # User-related tables
    "refresh_token",
    "login_audit",
    "unit_registration_data",
    "unit_details",
    "unit_members",
    "unit_officials",
    "unit_councilor",
    
    # Unit management tables
    "archived_unit_member",
    "removed_unit_member",
    "unit_transfer_request",
    "unit_member_change_request",
    "unit_officials_change_request",
    "unit_councilor_change_request",
    "unit_member_add_request",
    
    # Conference tables
    "conference",
    "conference_registration_data",
    "conference_delegate",
    "conference_payment",
    "food_preference",
    
    # Kalamela tables (depend on custom_user, unit_members, event_category)
    "registration_fee",
    "individual_event",
    "group_event",
    "individual_event_participation",
    "group_event_participation",
    "kalamela_exclude_members",
    "kalamela_payments",
    "individual_event_score_card",
    "group_event_score_card",
    "appeal",
    "appeal_payments",
]


class DevToProdMigrator:
    """Handles data migration from development to production database."""
    
    def __init__(self, dev_url: str, prod_url: str):
        print("🔌 Connecting to databases...")
        print(f"   Dev:  {self._mask_url(dev_url)}")
        print(f"   Prod: {self._mask_url(prod_url)}")
        
        self.dev_url = dev_url
        self.prod_url = prod_url
        
        # Create engines with connection pooling disabled (use fresh connections)
        self.dev_engine = create_engine(dev_url, poolclass=NullPool, echo=False)
        self.prod_engine = create_engine(prod_url, poolclass=NullPool, echo=False)
        
        print("✅ Connected to both databases\n")
        
        self.stats = {"migrated": 0, "tables": 0, "skipped": 0, "errors": []}
        
        # Cache tables list
        self._dev_tables = None
        self._prod_tables = None
    
    def _mask_url(self, url: str) -> str:
        """Mask password in database URL for logging."""
        import re
        return re.sub(r':([^:@]+)@', ':****@', url)
    
    def _get_fresh_connection(self, engine):
        """Get a fresh connection with retry logic."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return engine.connect()
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"   ⚠️ Connection failed, retrying ({attempt + 1}/{max_retries})...")
                    time.sleep(2)
                else:
                    raise
    
    def get_tables(self, engine, use_cache=True) -> set:
        """Get all tables from a database."""
        if use_cache:
            if engine == self.dev_engine and self._dev_tables:
                return self._dev_tables
            if engine == self.prod_engine and self._prod_tables:
                return self._prod_tables
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        result = set(t for t in tables if t != 'alembic_version')
        
        # Cache the result
        if engine == self.dev_engine:
            self._dev_tables = result
        elif engine == self.prod_engine:
            self._prod_tables = result
        
        return result
    
    def get_table_row_count(self, table_name: str, engine) -> int:
        """Get row count for a table."""
        try:
            with engine.connect() as conn:
                result = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
                return result.scalar()
        except Exception:
            return -1
    
    def compare_databases(self):
        """Compare row counts between dev and prod."""
        print("📊 Comparing databases...\n")
        print(f"{'Table':<40} {'Dev':<10} {'Prod':<10} {'Status'}")
        print("-" * 70)
        
        dev_tables = self.get_tables(self.dev_engine)
        prod_tables = self.get_tables(self.prod_engine)
        
        # Only show FastAPI tables we care about
        relevant_tables = set(ORDERED_TABLES) & (dev_tables | prod_tables)
        
        for table in sorted(relevant_tables):
            dev_count = self.get_table_row_count(table, self.dev_engine) if table in dev_tables else "N/A"
            prod_count = self.get_table_row_count(table, self.prod_engine) if table in prod_tables else "N/A"
            
            if table not in dev_tables:
                status = "⚠️ Only in Prod"
            elif table not in prod_tables:
                status = "⚠️ Only in Dev"
            elif dev_count == prod_count:
                status = "✅ Synced"
            else:
                status = "🔄 Needs sync"
            
            print(f"{table:<40} {str(dev_count):<10} {str(prod_count):<10} {status}")
        print()
    
    def truncate_prod_table(self, table_name: str) -> bool:
        """Truncate a single production table."""
        try:
            with self.prod_engine.connect() as conn:
                conn.execute(text(f'TRUNCATE TABLE "{table_name}" CASCADE'))
                conn.commit()
            return True
        except Exception as e:
            error_msg = str(e)
            if "does not exist" not in error_msg:
                print(f"   ⚠️ Could not truncate {table_name}: {error_msg[:60]}")
            return False
    
    def migrate_table(self, table_name: str) -> int:
        """Migrate a single table from dev to prod."""
        dev_tables = self.get_tables(self.dev_engine)
        prod_tables = self.get_tables(self.prod_engine)
        
        # Check if table exists in both databases
        if table_name not in dev_tables:
            print(f"   ⚠️ {table_name}: Not in dev DB")
            self.stats["skipped"] += 1
            return 0
        
        if table_name not in prod_tables:
            print(f"   ⚠️ {table_name}: Not in prod DB")
            self.stats["skipped"] += 1
            return 0
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # First truncate the prod table
                self.truncate_prod_table(table_name)
                
                # Get all data from dev
                with self._get_fresh_connection(self.dev_engine) as dev_conn:
                    result = dev_conn.execute(text(f'SELECT * FROM "{table_name}"'))
                    rows = result.fetchall()
                    columns = list(result.keys())
                
                if not rows:
                    print(f"   ⚠️ {table_name}: No data")
                    return 0
                
                # Build insert statement
                col_names = ", ".join([f'"{col}"' for col in columns])
                placeholders = ", ".join([f":{col}" for col in columns])
                insert_sql = f'INSERT INTO "{table_name}" ({col_names}) VALUES ({placeholders})'
                
                # Insert all rows in batches
                batch_size = 100
                with self._get_fresh_connection(self.prod_engine) as prod_conn:
                    count = 0
                    for i, row in enumerate(rows):
                        row_dict = dict(zip(columns, row))
                        try:
                            prod_conn.execute(text(insert_sql), row_dict)
                            count += 1
                            
                            # Commit every batch_size rows
                            if (i + 1) % batch_size == 0:
                                prod_conn.commit()
                        except Exception as e:
                            self.stats["errors"].append(f"{table_name} row: {str(e)[:80]}")
                    
                    # Final commit
                    prod_conn.commit()
                
                return count
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"   ⚠️ {table_name}: Retry {attempt + 1}/{max_retries} - {str(e)[:50]}")
                    time.sleep(2)
                else:
                    self.stats["errors"].append(f"{table_name}: {str(e)[:100]}")
                    return -1
    
    def reset_sequence(self, table_name: str):
        """Reset sequence for a table to max ID + 1."""
        try:
            with self.prod_engine.connect() as conn:
                result = conn.execute(text(f'SELECT MAX(id) FROM "{table_name}"'))
                max_id = result.scalar()
                
                if max_id is not None:
                    seq_name = f"{table_name}_id_seq"
                    conn.execute(text(f"SELECT setval('{seq_name}', {max_id + 1}, false)"))
                    conn.commit()
                    return max_id + 1
        except Exception:
            pass
        return None
    
    def migrate_all(self):
        """Migrate all tables from dev to prod."""
        print(f"🚀 Starting full migration...\n")
        
        # Get actual tables that exist in both databases
        dev_tables = self.get_tables(self.dev_engine)
        prod_tables = self.get_tables(self.prod_engine)
        common_tables = dev_tables & prod_tables
        
        # Filter to only tables we want to migrate (in our ordered list)
        tables_to_migrate = [t for t in ORDERED_TABLES if t in common_tables]
        
        print(f"📋 Found {len(tables_to_migrate)} tables to migrate\n")
        
        # Migrate each table in order
        for table in tables_to_migrate:
            count = self.migrate_table(table)
            if count > 0:
                print(f"   ✅ {table}: {count} rows")
                self.stats["migrated"] += count
                self.stats["tables"] += 1
            elif count == 0:
                pass  # Already printed warning
            else:
                print(f"   ❌ {table}: Error")
        
        # Reset sequences
        print("\n🔢 Resetting sequences...")
        for table in tables_to_migrate:
            seq_val = self.reset_sequence(table)
            if seq_val:
                print(f"   ✓ {table}: {seq_val}")
        
        print(f"\n📊 Migration Summary:")
        print(f"   Tables migrated: {self.stats['tables']}")
        print(f"   Tables skipped: {self.stats['skipped']}")
        print(f"   Total rows: {self.stats['migrated']}")
        
        if self.stats["errors"]:
            print(f"\n⚠️ Errors encountered ({len(self.stats['errors'])}):")
            for error in self.stats["errors"][:10]:
                print(f"   - {error}")
            if len(self.stats["errors"]) > 10:
                print(f"   ... and {len(self.stats['errors']) - 10} more")
    
    def close(self):
        """Close database connections."""
        self.dev_engine.dispose()
        self.prod_engine.dispose()
        print("\n🔌 Database connections closed")


def main():
    print("\n" + "=" * 70)
    print("🚀 FULL DATA MIGRATION: Development → Production")
    print("=" * 70)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    print("⚠️  WARNING: This will TRUNCATE production tables and copy data from DEV!")
    print("📍 Source (Dev):  ep-snowy-heart-a1z65pya-pooler.ap-southeast-1.aws.neon.tech")
    print("📍 Target (Prod): ep-round-waterfall-a13doc66-pooler.ap-southeast-1.aws.neon.tech\n")
    
    # Check for --yes flag for non-interactive mode
    if "--yes" not in sys.argv:
        try:
            response = input("Type 'yes' to confirm: ").strip().lower()
            if response != "yes":
                print("❌ Migration cancelled")
                return
        except EOFError:
            print("❌ Non-interactive mode detected. Use --yes flag to confirm.")
            return
    else:
        print("✅ Auto-confirmed via --yes flag\n")
    
    try:
        migrator = DevToProdMigrator(DEV_DB_URL, PROD_DB_URL)
        
        # Compare before migration
        print("📊 BEFORE Migration:")
        migrator.compare_databases()
        
        # Perform migration
        migrator.migrate_all()
        
        # Compare after migration
        print("\n📊 AFTER Migration:")
        migrator.compare_databases()
        
        migrator.close()
        
        print(f"\n✅ Migration completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
