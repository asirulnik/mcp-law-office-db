-- Law Office Database Schema
-- This schema defines the tables, indexes, triggers, and views needed for
-- managing law office client matters, billing, and invoicing.

-- Clients Table
-- Stores information about clients.
CREATE TABLE clients (
    client_id INTEGER PRIMARY KEY,      -- Unique identifier for the client
    client_name TEXT NOT NULL,          -- Name of the client
    contact_info TEXT                   -- Contact information for the client
);

-- Matters Table (formerly case_files)
-- Tracks individual matters associated with clients.
CREATE TABLE matters (
    matter_id INTEGER PRIMARY KEY,      -- Unique identifier for the matter
    client_id INTEGER,                  -- References the client associated with this matter
    matter_name TEXT,                   -- Name or title of the matter
    matter_status TEXT,                 -- Current status of the matter (e.g., Open, Closed, In Progress)
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
);

-- Case File Entries Table
-- Contains detailed entries for each matter.
-- Each row represents an activity that the attorney engaged in or document or other thing that the attorney created or reviewed 
CREATE TABLE case_file_entries (
    entry_id INTEGER PRIMARY KEY,        -- Unique identifier for the entry
    matter_id INTEGER,                   -- References the matter this entry belongs to
    type TEXT,                           -- Type of entry (e.g., Email, Document, Note)
    date DATETIME,                       -- Date and time of the entry
    title TEXT,                          -- Title or subject of the entry
    from_party TEXT,                     -- Sender of the communication
    to_party TEXT,                       -- Recipient of the communication
    cc_party TEXT,                       -- CC recipients
    content TEXT,                        -- Full content of the entry
    content_original TEXT,               -- Original unmodified content of the entry
    attachments TEXT,                    -- List or details of attachments
    synopsis TEXT,                       -- Brief summary of the entry
    comments TEXT,                       -- Additional comments or notes
    last_modified TEXT,                  -- Timestamp when entry was last modified
    FOREIGN KEY (matter_id) REFERENCES matters(matter_id)
);

-- Billing Entries Table
-- Tracks billing information for matter-related activities.
-- Each row in the billing_entries table represents a single contiguous block of time during which the attorney was engaged in a discrete billable activity.
CREATE TABLE billing_entries (
    billing_id INTEGER PRIMARY KEY NOT NULL,             -- Unique identifier for the billing entry
    matter_id INTEGER NOT NULL,                         -- References the matter associated with this billing entry
    substantiating_entry_id_1 INTEGER NOT NULL,         -- Primary reference to a case file entry that substantiates this billing activity
    substantiating_entry_id_2 INTEGER,                  -- Optional additional substantiating entry reference
    substantiating_entry_id_3 INTEGER,                  -- Optional additional substantiating entry reference
    substantiating_entry_id_4 INTEGER,                  -- Optional additional substantiating entry reference
    substantiating_entry_id_5 INTEGER,                  -- Optional additional substantiating entry reference
    billing_category TEXT,                              -- Category of billing (e.g., Legal Consultation, Research)
    billing_start DATETIME,                             -- Start time of billable activity
    billing_stop DATETIME,                              -- End time of billable activity
    billing_hours REAL,                                 -- Duration of billable activity in hours
    billing_description TEXT,                           -- Detailed description of billable work
    billing_substantiation TEXT,                        -- Detailed explanation of how this billable activity was determined
    status TEXT DEFAULT 'unbilled',                     -- Status of the billing entry (unbilled, committed)
    last_modified TEXT,                                 -- Timestamp when entry was last modified
    FOREIGN KEY (matter_id) REFERENCES matters(matter_id),
    FOREIGN KEY (substantiating_entry_id_1) REFERENCES case_file_entries(entry_id),
    FOREIGN KEY (substantiating_entry_id_2) REFERENCES case_file_entries(entry_id),
    FOREIGN KEY (substantiating_entry_id_3) REFERENCES case_file_entries(entry_id),
    FOREIGN KEY (substantiating_entry_id_4) REFERENCES case_file_entries(entry_id),
    FOREIGN KEY (substantiating_entry_id_5) REFERENCES case_file_entries(entry_id)
);

-- Client Invoices Table
-- Stores information about invoices created for clients
CREATE TABLE client_invoices (
    invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number INTEGER UNIQUE NOT NULL,
    client_id INTEGER NOT NULL,
    matter_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    total_amount REAL DEFAULT 0.0,
    total_hours REAL DEFAULT 0.0,
    date_created TEXT,
    last_modified TEXT,
    version_number INTEGER DEFAULT 1,
    date_submitted TEXT,
    date_payment_received TEXT,
    notes TEXT,
    balance_due REAL DEFAULT 0.0,
    is_valid BOOLEAN DEFAULT 1,
    last_validity_check TEXT,
    FOREIGN KEY (client_id) REFERENCES clients(client_id),
    FOREIGN KEY (matter_id) REFERENCES matters(matter_id)
);

-- Invoice Billing Items Table
-- Junction table linking billing entries to invoices
CREATE TABLE invoice_billing_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    billing_id INTEGER NOT NULL,
    status TEXT DEFAULT 'draft', -- 'draft' or 'committed'
    FOREIGN KEY (invoice_id) REFERENCES client_invoices(invoice_id) ON DELETE CASCADE,
    FOREIGN KEY (billing_id) REFERENCES billing_entries(billing_id)
);

-- Optional: Indexes for performance
-- These indexes improve query performance for common operations
CREATE INDEX idx_clients_name ON clients(client_name);                  -- Optimize client lookup by name
CREATE INDEX idx_matters_client ON matters(client_id);                 -- Optimize finding matters for a specific client
CREATE INDEX idx_case_file_entries_matter ON case_file_entries(matter_id); -- Optimize finding entries for a specific matter
CREATE INDEX idx_billing_entries_matter ON billing_entries(matter_id);    -- Optimize finding billing entries for a specific matter
CREATE INDEX idx_invoice_client ON client_invoices(client_id);         -- Optimize finding invoices for a specific client
CREATE INDEX idx_invoice_matter ON client_invoices(matter_id);         -- Optimize finding invoices for a specific matter
CREATE INDEX idx_invoice_status ON client_invoices(status);            -- Optimize finding invoices by status
CREATE INDEX idx_invoice_billing ON invoice_billing_items(invoice_id); -- Optimize finding billing items for an invoice
CREATE INDEX idx_billing_invoice ON invoice_billing_items(billing_id); -- Optimize finding invoices for a billing entry

-- Triggers for Automatic Timestamp Updates
CREATE TRIGGER set_client_invoices_date_created
AFTER INSERT ON client_invoices
FOR EACH ROW
WHEN NEW.date_created IS NULL
BEGIN
    UPDATE client_invoices SET date_created = datetime('now') WHERE invoice_id = NEW.invoice_id;
END;

CREATE TRIGGER update_client_invoices_last_modified
AFTER UPDATE ON client_invoices
FOR EACH ROW
BEGIN
    UPDATE client_invoices SET last_modified = datetime('now') WHERE invoice_id = NEW.invoice_id;
END;

-- Trigger to Prevent Double Billing
CREATE TRIGGER prevent_double_billing
BEFORE UPDATE ON client_invoices
FOR EACH ROW
WHEN NEW.status = 'submitted' AND OLD.status = 'draft'
BEGIN
    SELECT RAISE(ABORT, 'Cannot submit: One or more billing entries are already on another submitted invoice')
    WHERE EXISTS (
        SELECT 1 FROM invoice_billing_items ibi1
        WHERE ibi1.invoice_id = NEW.invoice_id
        AND EXISTS (
            SELECT 1 FROM invoice_billing_items ibi2
            WHERE ibi2.billing_id = ibi1.billing_id
            AND ibi2.status = 'committed'
        )
    );
END;

-- Trigger to Mark Billing Items as Committed Upon Invoice Submission
CREATE TRIGGER mark_committed_billing_entries
AFTER UPDATE ON client_invoices
FOR EACH ROW
WHEN NEW.status = 'submitted' AND OLD.status = 'draft'
BEGIN
    -- Mark all this invoice's billing entries as committed
    UPDATE invoice_billing_items
    SET status = 'committed'
    WHERE invoice_id = NEW.invoice_id;
    
    -- Also record the submission date
    UPDATE client_invoices
    SET date_submitted = datetime('now')
    WHERE invoice_id = NEW.invoice_id;
END;

-- Trigger to Update Invoice Totals When Billing Entries Are Added
CREATE TRIGGER update_invoice_totals_insert
AFTER INSERT ON invoice_billing_items
FOR EACH ROW
BEGIN
    UPDATE client_invoices 
    SET 
        total_hours = (SELECT COALESCE(SUM(be.billing_hours), 0) 
                       FROM invoice_billing_items ibi
                       JOIN billing_entries be ON ibi.billing_id = be.billing_id
                       WHERE ibi.invoice_id = NEW.invoice_id),
        total_amount = (SELECT COALESCE(SUM(be.billing_hours * 250), 0) 
                        FROM invoice_billing_items ibi
                        JOIN billing_entries be ON ibi.billing_id = be.billing_id
                        WHERE ibi.invoice_id = NEW.invoice_id),
        balance_due = (SELECT COALESCE(SUM(be.billing_hours * 250), 0) 
                      FROM invoice_billing_items ibi
                      JOIN billing_entries be ON ibi.billing_id = be.billing_id
                      WHERE ibi.invoice_id = NEW.invoice_id)
    WHERE invoice_id = NEW.invoice_id;
END;

-- Trigger to Update Invoice Totals When Billing Entries Are Removed
CREATE TRIGGER update_invoice_totals_delete
AFTER DELETE ON invoice_billing_items
FOR EACH ROW
BEGIN
    UPDATE client_invoices 
    SET 
        total_hours = (SELECT COALESCE(SUM(be.billing_hours), 0) 
                       FROM invoice_billing_items ibi
                       JOIN billing_entries be ON ibi.billing_id = be.billing_id
                       WHERE ibi.invoice_id = OLD.invoice_id),
        total_amount = (SELECT COALESCE(SUM(be.billing_hours * 250), 0) 
                        FROM invoice_billing_items ibi
                        JOIN billing_entries be ON ibi.billing_id = be.billing_id
                        WHERE ibi.invoice_id = OLD.invoice_id),
        balance_due = (SELECT COALESCE(SUM(be.billing_hours * 250), 0) 
                      FROM invoice_billing_items ibi
                      JOIN billing_entries be ON ibi.billing_id = be.billing_id
                      WHERE ibi.invoice_id = OLD.invoice_id)
    WHERE invoice_id = OLD.invoice_id;
END;

-- Temporal Consistency Triggers
-- Trigger to check for overlapping billing times (for billing entry inserts)
CREATE TRIGGER check_billing_time_overlaps
AFTER INSERT ON billing_entries
FOR EACH ROW
BEGIN
    -- Update validity status for all draft invoices containing overlapping times
    UPDATE client_invoices
    SET 
        is_valid = 0,
        last_validity_check = DATETIME('now')
    WHERE 
        status = 'draft' 
        AND invoice_id IN (
            SELECT ibi.invoice_id 
            FROM invoice_billing_items ibi
            WHERE ibi.billing_id = NEW.billing_id
        )
        AND EXISTS (
            -- Find if this entry overlaps with any committed billing entry
            SELECT 1 
            FROM billing_entries be
            JOIN invoice_billing_items ibi ON be.billing_id = ibi.billing_id
            JOIN client_invoices ci ON ibi.invoice_id = ci.invoice_id
            WHERE ci.status = 'submitted'
            AND ibi.status = 'committed'
            AND be.billing_id != NEW.billing_id
            AND (
                -- New entry starts during existing entry
                (NEW.billing_start >= be.billing_start AND NEW.billing_start < be.billing_stop)
                OR
                -- New entry ends during existing entry
                (NEW.billing_stop > be.billing_start AND NEW.billing_stop <= be.billing_stop)
                OR
                -- New entry completely contains existing entry
                (NEW.billing_start <= be.billing_start AND NEW.billing_stop >= be.billing_stop)
            )
        );
END;

-- Trigger to check for overlapping billing times (for billing entry updates)
CREATE TRIGGER check_billing_overlaps_part2
AFTER UPDATE ON billing_entries
FOR EACH ROW
BEGIN
    UPDATE client_invoices
    SET 
        is_valid = 0,
        last_validity_check = DATETIME('now')
    WHERE 
        status = 'draft' 
        AND invoice_id IN (
            SELECT ibi.invoice_id 
            FROM invoice_billing_items ibi
            WHERE ibi.billing_id = NEW.billing_id
        )
        AND EXISTS (
            SELECT 1 
            FROM billing_entries be
            JOIN invoice_billing_items ibi ON be.billing_id = ibi.billing_id
            JOIN client_invoices ci ON ibi.invoice_id = ci.invoice_id
            WHERE ci.status = 'submitted'
            AND ibi.status = 'committed'
            AND be.billing_id != NEW.billing_id
            AND (
                (NEW.billing_start >= be.billing_start AND NEW.billing_start < be.billing_stop)
                OR
                (NEW.billing_stop > be.billing_start AND NEW.billing_stop <= be.billing_stop)
                OR
                (NEW.billing_start <= be.billing_start AND NEW.billing_stop >= be.billing_stop)
            )
        );
END;

-- Trigger to enforce validity check before invoice submission
CREATE TRIGGER enforce_validity_on_submit
BEFORE UPDATE ON client_invoices
FOR EACH ROW
WHEN NEW.status = 'submitted' AND OLD.status = 'draft'
BEGIN
    -- First, ensure we have a recent validity check
    UPDATE client_invoices
    SET last_validity_check = DATETIME('now')
    WHERE invoice_id = NEW.invoice_id;
    
    -- Check if any time overlaps exist
    UPDATE client_invoices
    SET is_valid = 0
    WHERE invoice_id = NEW.invoice_id
    AND EXISTS (
        SELECT 1 
        FROM invoice_billing_items ibi1
        JOIN billing_entries be1 ON ibi1.billing_id = be1.billing_id
        WHERE ibi1.invoice_id = NEW.invoice_id
        AND EXISTS (
            SELECT 1 
            FROM invoice_billing_items ibi2
            JOIN billing_entries be2 ON ibi2.billing_id = be2.billing_id
            JOIN client_invoices ci ON ibi2.invoice_id = ci.invoice_id
            WHERE ci.status = 'submitted'
            AND ibi2.status = 'committed'
            AND (
                (be1.billing_start >= be2.billing_start AND be1.billing_start < be2.billing_stop)
                OR
                (be1.billing_stop > be2.billing_start AND be1.billing_stop <= be2.billing_stop)
                OR
                (be1.billing_start <= be2.billing_start AND be1.billing_stop >= be2.billing_stop)
            )
        )
    );
    
    -- If not valid, prevent submission
    SELECT RAISE(ABORT, 'Cannot submit invoice with overlapping time entries')
    WHERE (SELECT is_valid FROM client_invoices WHERE invoice_id = NEW.invoice_id) = 0;
END;

-- Trigger to mark invoices as valid when billing entries are added
CREATE TRIGGER mark_valid_billing_entries
AFTER INSERT ON invoice_billing_items
FOR EACH ROW
BEGIN
    -- Mark invoice as valid by default (will be changed to invalid if overlaps found)
    UPDATE client_invoices
    SET 
        is_valid = 1,
        last_validity_check = DATETIME('now')
    WHERE 
        invoice_id = NEW.invoice_id
        AND status = 'draft'
        AND NOT EXISTS (
            -- Only mark as valid if no overlaps with committed entries
            SELECT 1 
            FROM billing_entries be1
            JOIN invoice_billing_items ibi1 ON be1.billing_id = ibi1.billing_id 
            WHERE ibi1.invoice_id = NEW.invoice_id
            AND EXISTS (
                SELECT 1 
                FROM billing_entries be2
                JOIN invoice_billing_items ibi2 ON be2.billing_id = ibi2.billing_id
                JOIN client_invoices ci2 ON ibi2.invoice_id = ci2.invoice_id
                WHERE ci2.status = 'submitted'
                AND ibi2.status = 'committed'
                AND (
                    (be1.billing_start >= be2.billing_start AND be1.billing_start < be2.billing_stop)
                    OR
                    (be1.billing_stop > be2.billing_start AND be1.billing_stop <= be2.billing_stop)
                    OR
                    (be1.billing_start <= be2.billing_start AND be1.billing_stop >= be2.billing_stop)
                )
            )
        );
END;

-- Trigger to mark invoices as invalid when billing entries with overlaps are added
CREATE TRIGGER mark_invalid_billing_entries
AFTER INSERT ON invoice_billing_items
FOR EACH ROW
BEGIN
    -- Mark invoice as invalid if overlaps found
    UPDATE client_invoices
    SET 
        is_valid = 0,
        last_validity_check = DATETIME('now')
    WHERE 
        invoice_id = NEW.invoice_id
        AND status = 'draft'
        AND EXISTS (
            -- Find if any entry in this invoice overlaps with committed entries
            SELECT 1 
            FROM billing_entries be1
            JOIN invoice_billing_items ibi1 ON be1.billing_id = ibi1.billing_id 
            WHERE ibi1.invoice_id = NEW.invoice_id
            AND EXISTS (
                SELECT 1 
                FROM billing_entries be2
                JOIN invoice_billing_items ibi2 ON be2.billing_id = ibi2.billing_id
                JOIN client_invoices ci2 ON ibi2.invoice_id = ci2.invoice_id
                WHERE ci2.status = 'submitted'
                AND ibi2.status = 'committed'
                AND (
                    (be1.billing_start >= be2.billing_start AND be1.billing_start < be2.billing_stop)
                    OR
                    (be1.billing_stop > be2.billing_start AND be1.billing_stop <= be2.billing_stop)
                    OR
                    (be1.billing_start <= be2.billing_start AND be1.billing_stop >= be2.billing_stop)
                )
            )
        );
END;

-- View to help identify problematic entries with overlapping times
CREATE VIEW invalid_invoice_details AS
SELECT 
    ci.invoice_id,
    ci.invoice_number,
    ci.client_id,
    ci.matter_id,
    ci.last_validity_check,
    be1.billing_id as problematic_entry_id,
    be1.billing_start,
    be1.billing_stop,
    be1.billing_hours,
    be1.billing_description,
    be2.billing_id as conflicting_entry_id,
    be2.billing_start as conflicting_start,
    be2.billing_stop as conflicting_stop
FROM client_invoices ci
JOIN invoice_billing_items ibi1 ON ci.invoice_id = ibi1.invoice_id
JOIN billing_entries be1 ON ibi1.billing_id = be1.billing_id
JOIN invoice_billing_items ibi2 ON ibi2.invoice_id != ci.invoice_id
JOIN billing_entries be2 ON ibi2.billing_id = be2.billing_id
JOIN client_invoices ci2 ON ibi2.invoice_id = ci2.invoice_id
WHERE 
    ci.is_valid = 0
    AND ci2.status = 'submitted'
    AND ibi2.status = 'committed'
    AND (
        (be1.billing_start >= be2.billing_start AND be1.billing_start < be2.billing_stop)
        OR
        (be1.billing_stop > be2.billing_start AND be1.billing_stop <= be2.billing_stop)
        OR
        (be1.billing_start <= be2.billing_start AND be1.billing_stop >= be2.billing_stop)
    );
