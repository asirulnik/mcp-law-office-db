"""
Automatic timestamp management for SQLite databases.

This module provides functionality to automatically add and update timestamp
fields in SQLite tables. It adds triggers to:
1. Set 'created' fields to the current datetime when a record is inserted
2. Update 'last_modified' fields to the current datetime when a record is updated
"""

import sqlite3
import logging
from contextlib import closing
from typing import List, Dict, Any, Optional

logger = logging.getLogger('mcp_sqlite_server')

def has_column(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    """Check if a table has a specific column."""
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        return any(column[1] == column_name for column in columns)
    except sqlite3.Error as e:
        logger.error(f"Error checking for column {column_name} in {table_name}: {e}")
        return False

def get_table_names(conn: sqlite3.Connection) -> List[str]:
    """Get all table names in the database."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Error getting table names: {e}")
        return []

def create_timestamp_triggers(conn: sqlite3.Connection, table_name: str) -> None:
    """Create triggers for automatic timestamp management if applicable columns exist."""
    created_field_exists = has_column(conn, table_name, "created")
    last_modified_field_exists = has_column(conn, table_name, "last_modified")
    
    if not (created_field_exists or last_modified_field_exists):
        return
    
    cursor = conn.cursor()
    
    try:
        # First drop any existing triggers to avoid duplication
        if created_field_exists:
            cursor.execute(f"""
            DROP TRIGGER IF EXISTS {table_name}_set_created_timestamp
            """)
            
            # Create trigger for 'created' field
            cursor.execute(f"""
            CREATE TRIGGER {table_name}_set_created_timestamp
            AFTER INSERT ON {table_name}
            FOR EACH ROW
            WHEN NEW.created IS NULL
            BEGIN
                UPDATE {table_name} 
                SET created = DATETIME('now') 
                WHERE rowid = NEW.rowid;
            END
            """)
            logger.info(f"Created INSERT trigger for 'created' field on table {table_name}")
    
        if last_modified_field_exists:
            # Drop existing update trigger if it exists
            cursor.execute(f"""
            DROP TRIGGER IF EXISTS {table_name}_update_modified_timestamp
            """)
            
            # Create trigger for 'last_modified' field on UPDATE
            cursor.execute(f"""
            CREATE TRIGGER {table_name}_update_modified_timestamp
            AFTER UPDATE ON {table_name}
            FOR EACH ROW
            BEGIN
                UPDATE {table_name} 
                SET last_modified = DATETIME('now') 
                WHERE rowid = NEW.rowid;
            END
            """)
            logger.info(f"Created UPDATE trigger for 'last_modified' field on table {table_name}")
            
            # Drop existing insert trigger if it exists
            cursor.execute(f"""
            DROP TRIGGER IF EXISTS {table_name}_insert_modified_timestamp
            """)
            
            # Create trigger for 'last_modified' field on INSERT
            cursor.execute(f"""
            CREATE TRIGGER {table_name}_insert_modified_timestamp
            AFTER INSERT ON {table_name}
            FOR EACH ROW
            WHEN NEW.last_modified IS NULL
            BEGIN
                UPDATE {table_name} 
                SET last_modified = DATETIME('now') 
                WHERE rowid = NEW.rowid;
            END
            """)
            logger.info(f"Created INSERT trigger for 'last_modified' field on table {table_name}")
        
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Error creating triggers for table {table_name}: {e}")

def setup_all_timestamp_triggers(db_path: str) -> None:
    """Set up timestamp triggers for all applicable tables in the database."""
    try:
        with closing(sqlite3.connect(db_path)) as conn:
            table_names = get_table_names(conn)
            for table_name in table_names:
                create_timestamp_triggers(conn, table_name)
    except Exception as e:
        logger.error(f"Error setting up timestamp triggers: {e}")

def add_timestamp_columns_if_needed(conn: sqlite3.Connection, table_name: str) -> None:
    """Add timestamp columns to existing tables if they don't already exist."""
    try:
        cursor = conn.cursor()
        
        # Check for 'created' column
        if not has_column(conn, table_name, "created"):
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN created TEXT")
            logger.info(f"Added 'created' column to table {table_name}")
        
        # Check for 'last_modified' column
        if not has_column(conn, table_name, "last_modified"):
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN last_modified TEXT")
            logger.info(f"Added 'last_modified' column to table {table_name}")
        
        # Create triggers
        create_timestamp_triggers(conn, table_name)
        
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Error adding timestamp columns to {table_name}: {e}")

def initialize_timestamps_for_new_table(conn: sqlite3.Connection, query: str) -> None:
    """Parse a CREATE TABLE statement and set up timestamp triggers if applicable."""
    try:
        # Extract table name from CREATE TABLE statement
        # This is a basic parser and may need improvement for complex cases
        query_upper = query.upper()
        create_table_idx = query_upper.find("CREATE TABLE")
        if create_table_idx == -1:
            return
        
        # Skip past "CREATE TABLE" and handle optional "IF NOT EXISTS"
        start_idx = create_table_idx + len("CREATE TABLE")
        if "IF NOT EXISTS" in query_upper[start_idx:]:
            start_idx = query_upper.find("IF NOT EXISTS", start_idx) + len("IF NOT EXISTS")
        
        # Find table name
        while start_idx < len(query) and query[start_idx].isspace():
            start_idx += 1
        
        end_idx = start_idx
        while end_idx < len(query) and not query[end_idx].isspace() and query[end_idx] != '(':
            end_idx += 1
        
        table_name = query[start_idx:end_idx].strip('`"[]')
        
        # If the table was just created, set up triggers (we'll check for columns directly)
        if table_name:
            # Wait a moment to ensure the table is fully created before checking columns
            conn.commit()
            
            # Now check if the table has timestamp columns
            if has_column(conn, table_name, "created") or has_column(conn, table_name, "last_modified"):
                create_timestamp_triggers(conn, table_name)
                logger.info(f"Set up timestamp triggers for new table {table_name}")
        
    except Exception as e:
        logger.error(f"Error initializing timestamps for new table: {e}")
