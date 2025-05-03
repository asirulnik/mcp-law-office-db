import sqlite3
import os
from datetime import datetime

# Configuration
DATABASE_PATH = "/Users/andrewsirulnik/claude_mcp_servers/mcp-law-office-db/database/law_office.db"
BACKUP_PATH = f"{DATABASE_PATH}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def create_backup(source_path, backup_path):
    """Create a backup of the database file."""
    try:
        import shutil
        shutil.copy2(source_path, backup_path)
        print(f"Database backup created: {backup_path}")
    except Exception as e:
        print(f"ERROR: Could not create backup. {e}")
        return False
    return True

def migrate_database(db_path):
    """Perform database migration."""
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys=OFF")
        cursor = conn.cursor()
        
        print("Starting database migration...")
        
        # 1. Rename columns with a new table
        cursor.execute('''
        CREATE TABLE case_file_entries_new (
            entry_id INTEGER PRIMARY KEY,
            client_id INTEGER,
            matter_id INTEGER,
            type TEXT,
            date DATETIME NOT NULL,
            sent DATETIME,
            received DATETIME,
            title TEXT,
            `from` TEXT,
            `to` TEXT,
            cc TEXT,
            content TEXT,
            attachments TEXT,
            synopsis TEXT,
            comments TEXT,
            last_modified TEXT,
            content_original TEXT,
            FOREIGN KEY (client_id) REFERENCES clients(client_id),
            FOREIGN KEY (matter_id) REFERENCES matters(matter_id)
        )''')
        
        # Migration query 
        migration_query = '''
        INSERT INTO case_file_entries_new (
            entry_id, client_id, matter_id, type, date, 
            sent, received, title, `from`, `to`, cc, 
            content, attachments, synopsis, comments, 
            last_modified, content_original
        )
        SELECT 
            entry_id, client_id, matter_id, type, date, 
            date_sent_or_created, date_received, title, 
            from_party, to_party, cc_party, 
            content, attachments, synopsis, comments, 
            last_modified, content_original
        FROM case_file_entries
        '''
        
        cursor.execute(migration_query)
        
        # Drop old table
        cursor.execute("DROP TABLE case_file_entries")
        
        # Rename new table
        cursor.execute("ALTER TABLE case_file_entries_new RENAME TO case_file_entries")
        
        # Recreate indexes
        cursor.execute("CREATE INDEX idx_case_file_entries_matter ON case_file_entries(matter_id)")
        cursor.execute("CREATE INDEX idx_case_file_entries_client ON case_file_entries(client_id)")
        
        # Find and update any views or triggers
        views_to_update = [
            'invalid_invoice_details',
            'invoice_details'
        ]
        
        for view in views_to_update:
            # Attempt to drop and recreate views (will fail if view doesn't reference these columns)
            try:
                cursor.execute(f"DROP VIEW IF EXISTS {view}")
                print(f"Dropped view: {view}")
            except sqlite3.OperationalError as e:
                print(f"Could not drop {view}: {e}")
        
        # Re-enable foreign key constraints
        conn.execute("PRAGMA foreign_keys=ON")
        
        # Commit changes
        conn.commit()
        
        print("Database migration completed successfully!")
        
        # Verify new schema
        cursor.execute("PRAGMA table_info(case_file_entries)")
        new_columns = [col[1] for col in cursor.fetchall()]
        print("New columns:", new_columns)
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        conn.rollback()
    except Exception as e:
        print(f"Unexpected error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

def main():
    # Confirm before proceeding
    confirmation = input(f"""
DATABASE MIGRATION WARNING:
- This will modify your database schema
- A backup will be created at: {BACKUP_PATH}
- Existing case_file_entries columns will be renamed
- Referenced views may be dropped

Type 'YES' to proceed: """)
    
    if confirmation.strip().upper() != 'YES':
        print("Migration cancelled.")
        return
    
    # Create backup
    if not create_backup(DATABASE_PATH, BACKUP_PATH):
        print("Backup failed. Aborting migration.")
        return
    
    # Perform migration
    migrate_database(DATABASE_PATH)

if __name__ == "__main__":
    main()