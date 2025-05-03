# db_schema_update.py
import sqlite3
import logging
import os
from contextlib import closing

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
# Adjust this path if your database is located elsewhere
DB_PATH = "/Users/andrewsirulnik/claude_mcp_servers/mcp-law-office-db/database/law_office.db"

# --- Trigger Definitions ---

# Drop old/potentially conflicting triggers first (idempotent)
TRIGGERS_TO_DROP = [
    "check_billing_time_overlaps",      # Old trigger on billing_entries insert
    "check_billing_overlaps_part1",     # Old trigger on billing_entries insert
    "check_billing_overlaps_part2",     # Old trigger on billing_entries update
    "mark_valid_billing_entries",       # Old trigger related to invoice validity flag
    # Keep enforce_validity_on_submit for now as a final check
    # Keep mark_committed_billing_entries
    # Keep prevent_double_billing (checks if item is already on *another* submitted invoice)
]

# New strict rejection triggers
CREATE_TRIGGER_BEFORE_INSERT = """
CREATE TRIGGER prevent_overlap_before_insert
BEFORE INSERT ON billing_entries
FOR EACH ROW
BEGIN
    -- Check for overlap with ANY committed billing entry
    SELECT RAISE(ABORT, 'Time conflict: New entry overlaps with a committed entry.')
    WHERE EXISTS (
        SELECT 1
        FROM billing_entries be
        JOIN invoice_billing_items ibi ON be.billing_id = ibi.billing_id
        JOIN client_invoices ci ON ibi.invoice_id = ci.invoice_id
        WHERE
            ci.status = 'submitted'  -- Only check against committed entries
            AND ibi.status = 'committed' -- Redundant check for clarity
            AND (
                -- Standard overlap conditions:
                -- New starts during existing
                (NEW.billing_start >= be.billing_start AND NEW.billing_start < be.billing_stop)
                OR
                -- New ends during existing
                (NEW.billing_stop > be.billing_start AND NEW.billing_stop <= be.billing_stop)
                OR
                -- New encapsulates existing
                (NEW.billing_start <= be.billing_start AND NEW.billing_stop >= be.billing_stop)
            )
    );
END;
"""

CREATE_TRIGGER_BEFORE_UPDATE = """
CREATE TRIGGER prevent_overlap_before_update
BEFORE UPDATE ON billing_entries
FOR EACH ROW
BEGIN
    -- Check for overlap with ANY committed billing entry (excluding the row being updated itself)
    SELECT RAISE(ABORT, 'Time conflict: Updated entry overlaps with a committed entry.')
    WHERE EXISTS (
        SELECT 1
        FROM billing_entries be
        JOIN invoice_billing_items ibi ON be.billing_id = ibi.billing_id
        JOIN client_invoices ci ON ibi.invoice_id = ci.invoice_id
        WHERE
            ci.status = 'submitted'  -- Only check against committed entries
            AND ibi.status = 'committed'
            AND be.billing_id != NEW.billing_id -- Don't compare the row to its old self if it was committed (edge case)
                                               -- Although updating committed entries shouldn't typically happen.
            AND (
                -- Standard overlap conditions:
                (NEW.billing_start >= be.billing_start AND NEW.billing_start < be.billing_stop)
                OR
                (NEW.billing_stop > be.billing_start AND NEW.billing_stop <= be.billing_stop)
                OR
                (NEW.billing_start <= be.billing_start AND NEW.billing_stop >= be.billing_stop)
            )
    );
END;
"""


# --- Main Execution ---
def apply_schema_updates(db_file):
    """Connects to the database and applies schema updates."""
    logging.info(f"Connecting to database: {db_file}")
    if not os.path.exists(db_file):
        logging.error(f"Database file not found at {db_file}. Please ensure the path is correct.")
        return False

    try:
        with closing(sqlite3.connect(db_file)) as conn:
            cursor = conn.cursor()
            logging.info("Connection successful.")

            # Drop old triggers
            logging.info("Dropping old/conflicting triggers...")
            for trigger_name in TRIGGERS_TO_DROP:
                try:
                    cursor.execute(f"DROP TRIGGER IF EXISTS {trigger_name};")
                    logging.info(f" - Dropped trigger (if exists): {trigger_name}")
                except sqlite3.Error as e:
                    logging.warning(f" - Could not drop trigger {trigger_name} (may not exist or error): {e}")
            conn.commit()

            # Create new triggers
            logging.info("Creating new strict overlap rejection triggers...")
            try:
                cursor.execute(CREATE_TRIGGER_BEFORE_INSERT)
                logging.info(" - Created trigger: prevent_overlap_before_insert")
            except sqlite3.Error as e:
                logging.error(f" - FAILED to create prevent_overlap_before_insert: {e}")
                raise # Stop execution if critical trigger fails

            try:
                cursor.execute(CREATE_TRIGGER_BEFORE_UPDATE)
                logging.info(" - Created trigger: prevent_overlap_before_update")
            except sqlite3.Error as e:
                logging.error(f" - FAILED to create prevent_overlap_before_update: {e}")
                raise # Stop execution if critical trigger fails

            conn.commit()
            logging.info("Schema update script completed successfully.")
            return True

    except sqlite3.Error as e:
        logging.error(f"Database error during schema update: {e}")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    if apply_schema_updates(DB_PATH):
        print("Database schema updates applied successfully.")
    else:
        print("Database schema updates failed. Check logs for details.")

