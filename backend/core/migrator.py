import os
import logging
import psycopg2
from pathlib import Path

logger = logging.getLogger("DatabaseMigrator")

class DatabaseMigrator:
    def __init__(self):
        self.db_url = os.environ.get("SUPABASE_DB_URL")
        self.sql_path = Path(__file__).resolve().parent.parent / "supabase_setup.sql"

    def run_migrations(self):
        """
        Executes the SQL setup script directly against the database.
        Allows for 'Code-First' schema management.
        """
        if not self.db_url:
            logger.warning("SUPABASE_DB_URL not found. Skipping auto-migrations.")
            logger.warning("To enable auto-migrations, add 'SUPABASE_DB_URL=postgres://...' to your .env")
            return

        if not self.sql_path.exists():
            logger.error(f"Migration file not found: {self.sql_path}")
            return

        try:
            logger.info("Connecting to Database for migrations...")
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()
            
            # Read SQL
            with open(self.sql_path, 'r') as f:
                sql_script = f.read()
            
            # Execute
            cur.execute(sql_script)
            conn.commit()
            
            logger.info("✅ Database Migrations executed successfully.")
            
            cur.close()
            conn.close()
            
        except psycopg2.Error as e:
            logger.error(f"❌ Database Migration Failed: {e}")
            logger.error(f"Error Code: {e.pgcode}")
            # We do NOT raise here to allow app to start in 'Offline Mode' if needed
        except Exception as e:
            logger.error(f"Unexpected Migration Error: {e}")
