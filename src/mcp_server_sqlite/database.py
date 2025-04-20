"""
Database module for the Law Office SQLite MCP Server.
Handles database connections and query execution.
"""

import sqlite3
import logging
from contextlib import closing
from pathlib import Path
from typing import Any, List, Dict, Optional

from . import auto_timestamps

logger = logging.getLogger('mcp_law_office_server.database')

class SqliteDatabase:
    def __init__(self, db_path: str):
        """Initialize the SQLite database connection"""
        self.db_path = str(Path(db_path).expanduser())
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize connection to the SQLite database and set up automatic timestamp triggers"""
        logger.debug("Initializing database connection")
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            
            # Set up automatic timestamp triggers for all existing tables
            table_names = auto_timestamps.get_table_names(conn)
            for table_name in table_names:
                auto_timestamps.create_timestamp_triggers(conn, table_name)
                logger.info(f"Setup automatic timestamp triggers for table: {table_name}")
                
            conn.close()

    def _execute_query(self, query: str, params: Any = None) -> list[dict[str, Any]]:
        """Execute a SQL query and return results as a list of dictionaries"""
        logger.debug(f"Executing query: {query}")
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                with closing(conn.cursor()) as cursor:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)

                    if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER')):
                        # For CREATE TABLE statements, set up timestamp triggers
                        if query.strip().upper().startswith('CREATE TABLE'):
                            auto_timestamps.initialize_timestamps_for_new_table(conn, query)
                            
                        conn.commit()
                        affected = cursor.rowcount
                        logger.debug(f"Write query affected {affected} rows")
                        return [{"affected_rows": affected}]

                    results = [dict(row) for row in cursor.fetchall()]
                    logger.debug(f"Read query returned {len(results)} rows")
                    return results
        except Exception as e:
            logger.error(f"Database error executing query: {e}")
            raise

# Inside src/mcp_server_sqlite/database.py within the SqliteDatabase class:

    def _execute_script(self, script: str) -> dict[str, Any]:
        """Execute multiple SQL statements from a script using context managers."""
        logger.debug(f"Executing script with context manager: {script[:100]}...")
        try:
            # Use 'with closing' for automatic connection and cursor management
            with closing(sqlite3.connect(self.db_path)) as conn:
                # conn.row_factory = sqlite3.Row # Not strictly needed for executescript
                with closing(conn.cursor()) as cursor:
                    cursor.executescript(script) # Execute the script
                    conn.commit() # Commit if the entire script was successful
                    logger.debug(f"Successfully executed script.")
                    # Return success status
                    return {"status": "success", "message": "Script executed successfully."}

        except sqlite3.Error as e:
            # An error occurred during script execution.
            # 'with closing' will handle closing the connection.
            # executescript already performed a rollback automatically.
            logger.error(f"Database error during script execution: {e}")
            # Re-raise the original error to report the specific SQL issue
            raise e
            
        except Exception as e:
            # Catch any other unexpected errors
            logger.error(f"Unexpected error executing script: {e}", exc_info=True)
            # Re-raise the caught exception
            raise
