# **Law Office SQLite MCP Server \- Application Specification**

**Version:** 1.0 (Based on recent updates)

## **1\. Introduction**

### **1.1 Purpose**

This document specifies the design and functionality of the Law Office SQLite Model Context Protocol (MCP) Server. The server acts as an interface between an AI assistant (e.g., Claude) and a dedicated SQLite database containing law practice management data. Its primary purpose is to enable the AI assistant to perform paralegal tasks related to case management, document handling, time tracking, billing, and reporting according to strict operational rules and workflows defined in a corresponding AI system prompt.

### **1.2 Scope**

The server manages data for:

* Clients and Legal Matters  
* Case File Entries (Emails, Documents, Notes, etc.)  
* Billable Time Tracking (including substantiation and confidence assessment)  
* Client Invoicing Workflow  
* Calendar Events/Deadlines

The server provides tools for database manipulation, resource endpoints for dynamic information retrieval, and guided prompts to initiate specific workflows.

### **1.3 Target Audience**

* AI Assistants interacting with the server via MCP.  
* Developers maintaining or extending the server codebase.  
* Users (Attorneys/Paralegals) understanding the capabilities and limitations of the AI interaction facilitated by this server.

## **2\. Architecture**

### **2.1 Overview**

The application is a Python-based MCP server that interacts with a local SQLite database file. It uses the mcp-server-sdk library to handle the MCP communication protocol.

### **2.2 Components**

* **MCP Server Core (server\_law\_office.py):** Initializes the server, registers handlers, and manages the main execution loop.  
* **Database Interface (database.py):** Contains the SqliteDatabase class responsible for connecting to the SQLite file and executing SQL queries (\_execute\_query, \_execute\_script).  
* **Tool Handlers (tool\_handlers.py):** Defines the available tools (schema and description via list\_tools) and implements their execution logic (handle\_call\_tool).  
* **Resource Handlers (resource\_handlers.py):** Defines available dynamic resources (schema and description via handle\_list\_resources) and implements the logic to generate their content (handle\_read\_resource).  
* **Prompt Handlers (prompt\_handlers.py):** Defines available guided prompts (schema and description via list\_prompts) and implements the logic to generate the initial prompt text (handle\_get\_prompt).  
* **Timestamp Logic (auto\_timestamps.py):** Provides functions to manage automatic created and last\_modified timestamp columns via database triggers.  
* **Database Schema (Appendix\_1\_SQLite\_DB\_Schema in System Prompt / setup\_law\_office.py):** Defines the structure of the SQLite database, including tables, columns, views, and crucial triggers.  
* **Database Setup/Update Scripts (setup\_law\_office.py, db\_schema\_update.py):** Scripts to initialize the database schema and apply subsequent modifications (like trigger updates).

### **2.3 Data Storage**

* All persistent data is stored in a single SQLite database file (default: ./database/law\_office.db).  
* Configuration (server command, args) is managed externally via the MCP client (e.g., claude\_desktop\_config.json).

## **3\. Database Schema**

## **Database Schema Details**

The following SQL statements define the database structure, including tables, indexes, views, and triggers.  
\-- Law Office Database Schema

\-- Clients Table  
CREATE TABLE clients (  
    client\_id INTEGER PRIMARY KEY AUTOINCREMENT,  
    client\_name TEXT NOT NULL UNIQUE, \-- Added UNIQUE constraint  
    contact\_info TEXT,  
    created TEXT,        \-- Added for auto-timestamp  
    last\_modified TEXT \-- Added for auto-timestamp  
);  
CREATE INDEX idx\_clients\_name ON clients(client\_name);

\-- Matters Table  
CREATE TABLE matters (  
    matter\_id INTEGER PRIMARY KEY AUTOINCREMENT, \-- Changed to AUTOINCREMENT  
    client\_id INTEGER NOT NULL, \-- Added NOT NULL  
    matter\_name TEXT NOT NULL,  \-- Added NOT NULL  
    matter\_status TEXT DEFAULT 'Open', \-- Added DEFAULT  
    created TEXT,        \-- Added for auto-timestamp  
    last\_modified TEXT, \-- Added for auto-timestamp  
    FOREIGN KEY (client\_id) REFERENCES clients(client\_id) ON DELETE CASCADE \-- Added ON DELETE CASCADE  
);  
CREATE INDEX idx\_matters\_client ON matters(client\_id); \-- Added index

\-- Case File Entries Table  
CREATE TABLE case\_file\_entries (  
    entry\_id INTEGER PRIMARY KEY AUTOINCREMENT, \-- Changed to AUTOINCREMENT  
    client\_id INTEGER NOT NULL, \-- Added NOT NULL (derived from matter)  
    matter\_id INTEGER NOT NULL, \-- Added NOT NULL  
    type TEXT,                  \-- E.g., 'Email', 'Pleading', 'Note', 'Document'  
    date DATETIME NOT NULL,     \-- Authoritative date of the event/document  
    received DATETIME,          \-- Specific time email was received (if applicable)  
    sent DATETIME,              \-- Specific time email was sent (if applicable)  
    title TEXT,  
    "from" TEXT,                \-- Using quotes as 'from' is a keyword  
    "to" TEXT,                  \-- Using quotes as 'to' is a keyword  
    cc TEXT,  
    content TEXT NOT NULL,      \-- Added NOT NULL, core content must exist  
    attachments TEXT,           \-- Description/list of attachments  
    synopsis TEXT,              \-- AI-generated or user summary  
    comments TEXT,              \-- User/AI comments about the entry  
    content\_original TEXT,      \-- Store the initial verbatim content if needed for diffs  
    created TEXT,               \-- Added for auto-timestamp  
    last\_modified TEXT,         \-- Added for auto-timestamp  
    FOREIGN KEY (matter\_id) REFERENCES matters(matter\_id) ON DELETE CASCADE, \-- Added ON DELETE CASCADE  
    \-- Removed client\_id FK, assuming relationship is via matter\_id  
    CHECK (date IS NOT NULL)    \-- Explicit check  
);  
CREATE INDEX idx\_case\_file\_entries\_matter ON case\_file\_entries(matter\_id);  
CREATE INDEX idx\_case\_file\_entries\_date ON case\_file\_entries(date); \-- Added index on date

\-- Billing Entries Table  
CREATE TABLE billing\_entries (  
    billing\_id INTEGER PRIMARY KEY AUTOINCREMENT, \-- Changed to AUTOINCREMENT  
    matter\_id INTEGER NOT NULL,  
    substantiating\_entry\_id\_1 INTEGER NOT NULL, \-- Primary source document/event  
    substantiating\_entry\_id\_2 INTEGER,  
    substantiating\_entry\_id\_3 INTEGER,  
    substantiating\_entry\_id\_4 INTEGER,  
    substantiating\_entry\_id\_5 INTEGER,  
    billing\_category TEXT NOT NULL,      \-- Added NOT NULL  
    billing\_start DATETIME NOT NULL,     \-- Added NOT NULL  
    billing\_stop DATETIME NOT NULL,      \-- Added NOT NULL  
    billing\_hours REAL,                 \-- Can be calculated by trigger or provided  
    billing\_description TEXT NOT NULL,   \-- Added NOT NULL  
    billing\_substantiation TEXT NOT NULL,-- Added NOT NULL  
    activity\_confidence TEXT NOT NULL CHECK(activity\_confidence IN ('conclusive', 'medium', 'low')), \-- Added NOT NULL  
    timing\_confidence TEXT NOT NULL CHECK(timing\_confidence IN ('conclusive', 'medium', 'low')),     \-- Added NOT NULL  
    confidence\_rationale TEXT NOT NULL, \-- Added NOT NULL  
    created TEXT,                       \-- Added for auto-timestamp  
    last\_modified TEXT,                 \-- Added for auto-timestamp  
    FOREIGN KEY (matter\_id) REFERENCES matters(matter\_id) ON DELETE CASCADE, \-- Added ON DELETE CASCADE  
    FOREIGN KEY (substantiating\_entry\_id\_1) REFERENCES case\_file\_entries(entry\_id), \-- Added FK constraints  
    FOREIGN KEY (substantiating\_entry\_id\_2) REFERENCES case\_file\_entries(entry\_id),  
    FOREIGN KEY (substantiating\_entry\_id\_3) REFERENCES case\_file\_entries(entry\_id),  
    FOREIGN KEY (substantiating\_entry\_id\_4) REFERENCES case\_file\_entries(entry\_id),  
    FOREIGN KEY (substantiating\_entry\_id\_5) REFERENCES case\_file\_entries(entry\_id),  
    CHECK (billing\_stop \>= billing\_start) \-- Ensure end is not before start  
);  
CREATE INDEX idx\_billing\_entries\_matter ON billing\_entries(matter\_id); \-- Added index  
CREATE INDEX idx\_billing\_entries\_start ON billing\_entries(billing\_start); \-- Added index

\-- Client Invoices Table  
CREATE TABLE client\_invoices (  
    invoice\_id INTEGER PRIMARY KEY AUTOINCREMENT,  
    invoice\_number INTEGER UNIQUE NOT NULL,  
    client\_id INTEGER NOT NULL,  
    matter\_id INTEGER NOT NULL,  
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft', 'submitted', 'paid', 'void')), \-- Added CHECK  
    total\_amount REAL DEFAULT 0.0,  
    total\_hours REAL DEFAULT 0.0,  
    date\_created TEXT,          \-- Managed by trigger  
    last\_modified TEXT,         \-- Managed by trigger  
    version\_number INTEGER DEFAULT 1,  
    date\_submitted TEXT,        \-- Managed by trigger  
    date\_payment\_received TEXT, \-- Manually updated  
    notes TEXT,  
    balance\_due REAL DEFAULT 0.0, \-- Managed by trigger  
    is\_valid BOOLEAN DEFAULT 1,   \-- Flag for validity checks (less critical with strict rejection)  
    last\_validity\_check TEXT,   \-- Timestamp of last check run  
    created TEXT,               \-- Added for auto-timestamp (consistency)  
    last\_modified\_invoice TEXT, \-- Renamed to avoid conflict with base last\_modified  
    FOREIGN KEY (client\_id) REFERENCES clients(client\_id) ON DELETE CASCADE,  
    FOREIGN KEY (matter\_id) REFERENCES matters(matter\_id) ON DELETE CASCADE  
);  
CREATE INDEX idx\_invoices\_client ON client\_invoices(client\_id);  
CREATE INDEX idx\_invoices\_matter ON client\_invoices(matter\_id);  
CREATE INDEX idx\_invoices\_status ON client\_invoices(status);  
CREATE INDEX idx\_invoices\_number ON client\_invoices(invoice\_number); \-- Added index

\-- Invoice Billing Items Table (Junction Table)  
CREATE TABLE invoice\_billing\_items (  
    id INTEGER PRIMARY KEY AUTOINCREMENT,  
    invoice\_id INTEGER NOT NULL,  
    billing\_id INTEGER NOT NULL,  
    status TEXT DEFAULT 'draft' CHECK(status IN ('draft', 'committed')), \-- Status of the item on this invoice  
    created TEXT,               \-- Added for auto-timestamp  
    last\_modified TEXT,         \-- Added for auto-timestamp  
    FOREIGN KEY (invoice\_id) REFERENCES client\_invoices(invoice\_id) ON DELETE CASCADE,  
    FOREIGN KEY (billing\_id) REFERENCES billing\_entries(billing\_id) ON DELETE CASCADE, \-- Added ON DELETE CASCADE  
    UNIQUE (invoice\_id, billing\_id) \-- Prevent adding same item twice  
);  
CREATE INDEX idx\_invoice\_items\_invoice ON invoice\_billing\_items(invoice\_id);  
CREATE INDEX idx\_invoice\_items\_billing ON invoice\_billing\_items(billing\_id);  
CREATE INDEX idx\_invoice\_items\_status ON invoice\_billing\_items(status);

\-- Calendar Events Table  
CREATE TABLE calendar\_events (  
    event\_id INTEGER PRIMARY KEY AUTOINCREMENT, \-- Changed to AUTOINCREMENT  
    client\_id INTEGER,          \-- Optional link directly to client  
    case\_id INTEGER,            \-- Renamed from matter\_id for clarity, linked to matters.matter\_id  
    event\_title TEXT NOT NULL,  
    event\_description TEXT,  
    event\_location TEXT,  
    event\_start DATETIME NOT NULL,  
    event\_end DATETIME NOT NULL,  
    event\_type TEXT,            \-- E.g., 'Deadline', 'Meeting', 'Hearing', 'Reminder'  
    all\_day\_event BOOLEAN DEFAULT 0,  
    reminder\_time INTEGER,      \-- Minutes before event\_start to remind  
    attendees TEXT,             \-- Comma-separated list or JSON  
    event\_status TEXT DEFAULT 'Confirmed' CHECK(event\_status IN ('Confirmed', 'Tentative', 'Cancelled')), \-- Added CHECK  
    notes TEXT,  
    created TEXT,               \-- Changed from created\_at for consistency  
    last\_modified TEXT,         \-- Changed from updated\_at for consistency  
    FOREIGN KEY (client\_id) REFERENCES clients(client\_id) ON DELETE SET NULL, \-- Allow event if client deleted  
    FOREIGN KEY (case\_id) REFERENCES matters(matter\_id) ON DELETE CASCADE \-- Delete event if matter deleted  
);  
CREATE INDEX idx\_calendar\_events\_case ON calendar\_events(case\_id); \-- Added index  
CREATE INDEX idx\_calendar\_events\_start ON calendar\_events(event\_start); \-- Added index

\-- (Removed Email Metadata/Headers tables as they seemed less integrated)

\-- Views  
CREATE VIEW available\_billing\_entries AS  
SELECT  
    be.\*  
FROM  
    billing\_entries be  
WHERE  
    NOT EXISTS (  
        SELECT 1  
        FROM invoice\_billing\_items ibi  
        JOIN client\_invoices ci ON ibi.invoice\_id \= ci.invoice\_id  
        WHERE ibi.billing\_id \= be.billing\_id  
        AND ci.status \= 'submitted' \-- Only exclude if on a SUBMITTED invoice  
        AND ibi.status \= 'committed'  
    );

\-- (Removed draft\_invoices\_with\_committed\_entries view as less relevant now)

\-- Triggers

\-- Auto Timestamps (Conceptual \- managed by auto\_timestamps.py logic)  
\-- CREATE TRIGGER \[table\]\_set\_created\_timestamp AFTER INSERT ON \[table\] ...  
\-- CREATE TRIGGER \[table\]\_update\_modified\_timestamp AFTER UPDATE ON \[table\] ...  
\-- CREATE TRIGGER \[table\]\_insert\_modified\_timestamp AFTER INSERT ON \[table\] ...

\-- Invoice Total Updates  
CREATE TRIGGER update\_invoice\_totals\_insert  
AFTER INSERT ON invoice\_billing\_items  
FOR EACH ROW  
BEGIN  
    UPDATE client\_invoices  
    SET  
        total\_hours \= (SELECT COALESCE(SUM(be.billing\_hours), 0\)  
                       FROM invoice\_billing\_items ibi  
                       JOIN billing\_entries be ON ibi.billing\_id \= be.billing\_id  
                       WHERE ibi.invoice\_id \= NEW.invoice\_id),  
        total\_amount \= (SELECT COALESCE(SUM(be.billing\_hours \* 250), 0\) \-- Assuming fixed rate $250/hr for example  
                        FROM invoice\_billing\_items ibi  
                        JOIN billing\_entries be ON ibi.billing\_id \= be.billing\_id  
                        WHERE ibi.invoice\_id \= NEW.invoice\_id),  
        balance\_due \= (SELECT COALESCE(SUM(be.billing\_hours \* 250), 0\) \-- Balance initially equals total amount  
                       FROM invoice\_billing\_items ibi  
                       JOIN billing\_entries be ON ibi.billing\_id \= be.billing\_id  
                       WHERE ibi.invoice\_id \= NEW.invoice\_id)  
    WHERE invoice\_id \= NEW.invoice\_id;  
END;

CREATE TRIGGER update\_invoice\_totals\_delete  
AFTER DELETE ON invoice\_billing\_items  
FOR EACH ROW  
BEGIN  
    UPDATE client\_invoices  
    SET  
        total\_hours \= (SELECT COALESCE(SUM(be.billing\_hours), 0\)  
                       FROM invoice\_billing\_items ibi  
                       JOIN billing\_entries be ON ibi.billing\_id \= be.billing\_id  
                       WHERE ibi.invoice\_id \= OLD.invoice\_id),  
        total\_amount \= (SELECT COALESCE(SUM(be.billing\_hours \* 250), 0\)  
                        FROM invoice\_billing\_items ibi  
                        JOIN billing\_entries be ON ibi.billing\_id \= be.billing\_id  
                        WHERE ibi.invoice\_id \= OLD.invoice\_id),  
        balance\_due \= (SELECT COALESCE(SUM(be.billing\_hours \* 250), 0\)  
                       FROM invoice\_billing\_items ibi  
                       JOIN billing\_entries be ON ibi.billing\_id \= be.billing\_id  
                       WHERE ibi.invoice\_id \= OLD.invoice\_id)  
    WHERE invoice\_id \= OLD.invoice\_id;  
END;

\-- Strict Overlap Rejection Triggers (Replaces previous validity flag logic)  
CREATE TRIGGER prevent\_overlap\_before\_insert  
BEFORE INSERT ON billing\_entries  
FOR EACH ROW  
BEGIN  
    \-- Check for overlap with ANY committed billing entry  
    SELECT RAISE(ABORT, 'Time conflict: New entry overlaps with a committed entry.')  
    WHERE EXISTS (  
        SELECT 1  
        FROM billing\_entries be  
        JOIN invoice\_billing\_items ibi ON be.billing\_id \= ibi.billing\_id  
        JOIN client\_invoices ci ON ibi.invoice\_id \= ci.invoice\_id  
        WHERE  
            ci.status \= 'submitted'  \-- Only check against committed entries  
            AND ibi.status \= 'committed'  
            AND (  
                (NEW.billing\_start \>= be.billing\_start AND NEW.billing\_start \< be.billing\_stop) OR  
                (NEW.billing\_stop \> be.billing\_start AND NEW.billing\_stop \<= be.billing\_stop) OR  
                (NEW.billing\_start \<= be.billing\_start AND NEW.billing\_stop \>= be.billing\_stop)  
            )  
    );  
END;

CREATE TRIGGER prevent\_overlap\_before\_update  
BEFORE UPDATE ON billing\_entries  
FOR EACH ROW  
BEGIN  
    \-- Check for overlap with ANY committed billing entry (excluding the row being updated itself)  
    SELECT RAISE(ABORT, 'Time conflict: Updated entry overlaps with a committed entry.')  
    WHERE EXISTS (  
        SELECT 1  
        FROM billing\_entries be  
        JOIN invoice\_billing\_items ibi ON be.billing\_id \= ibi.billing\_id  
        JOIN client\_invoices ci ON ibi.invoice\_id \= ci.invoice\_id  
        WHERE  
            ci.status \= 'submitted'  
            AND ibi.status \= 'committed'  
            AND be.billing\_id \!= NEW.billing\_id \-- Don't compare the row to itself  
            AND (  
                (NEW.billing\_start \>= be.billing\_start AND NEW.billing\_start \< be.billing\_stop) OR  
                (NEW.billing\_stop \> be.billing\_start AND NEW.billing\_stop \<= be.billing\_stop) OR  
                (NEW.billing\_start \<= be.billing\_start AND NEW.billing\_stop \>= be.billing\_stop)  
            )  
    );  
END;

\-- Invoice Submission Triggers  
CREATE TRIGGER prevent\_double\_billing \-- Check if item is already on ANOTHER submitted invoice  
BEFORE UPDATE ON client\_invoices  
FOR EACH ROW  
WHEN NEW.status \= 'submitted' AND OLD.status \= 'draft'  
BEGIN  
    SELECT RAISE(ABORT, 'Cannot submit: One or more billing entries are already committed on another submitted invoice.')  
    WHERE EXISTS (  
        SELECT 1 FROM invoice\_billing\_items ibi1 \-- Items on the invoice being submitted  
        WHERE ibi1.invoice\_id \= NEW.invoice\_id  
        AND EXISTS (  
            SELECT 1 FROM invoice\_billing\_items ibi2 \-- Check if this item exists elsewhere committed  
            JOIN client\_invoices ci2 ON ibi2.invoice\_id \= ci2.invoice\_id  
            WHERE ibi2.billing\_id \= ibi1.billing\_id  
              AND ibi2.invoice\_id \!= NEW.invoice\_id \-- Must be on a DIFFERENT invoice  
              AND ci2.status \= 'submitted'  
              AND ibi2.status \= 'committed' \-- Redundant but clear  
        )  
    );  
END;

CREATE TRIGGER mark\_committed\_billing\_entries  
AFTER UPDATE ON client\_invoices  
FOR EACH ROW  
WHEN NEW.status \= 'submitted' AND OLD.status \= 'draft'  
BEGIN  
    \-- Mark all this invoice's billing items as committed  
    UPDATE invoice\_billing\_items  
    SET status \= 'committed'  
    WHERE invoice\_id \= NEW.invoice\_id;

    \-- Also record the submission date  
    UPDATE client\_invoices  
    SET date\_submitted \= datetime('now')  
    WHERE invoice\_id \= NEW.invoice\_id;  
END;

\-- (Removed triggers related to the is\_valid flag as primary rejection is now on billing\_entries)

\-- Optional: Trigger to calculate billing\_hours if not provided  
CREATE TRIGGER calculate\_billing\_hours\_on\_insert  
AFTER INSERT ON billing\_entries  
FOR EACH ROW  
WHEN NEW.billing\_hours IS NULL AND NEW.billing\_start IS NOT NULL AND NEW.billing\_stop IS NOT NULL  
BEGIN  
    UPDATE billing\_entries  
    SET billing\_hours \= ROUND((julianday(NEW.billing\_stop) \- julianday(NEW.billing\_start)) \* 24.0, 1\) \-- Round to nearest 0.1  
    WHERE billing\_id \= NEW.billing\_id;  
END;

CREATE TRIGGER calculate\_billing\_hours\_on\_update  
AFTER UPDATE ON billing\_entries  
FOR EACH ROW  
WHEN (NEW.billing\_hours IS NULL OR NEW.billing\_start \!= OLD.billing\_start OR NEW.billing\_stop \!= OLD.billing\_stop)  
     AND NEW.billing\_start IS NOT NULL AND NEW.billing\_stop IS NOT NULL  
BEGIN  
    UPDATE billing\_entries  
    SET billing\_hours \= ROUND((julianday(NEW.billing\_stop) \- julianday(NEW.billing\_start)) \* 24.0, 1\) \-- Round to nearest 0.1  
    WHERE billing\_id \= NEW.billing\_id;  
END;

## **Installation**

### **Prerequisites**

* **Python 3.10 or higher (Python 3.11+ recommended)**.  
* **uv**: Fast Python package installer ([astral.sh/uv](https://astral.sh/uv)).  
* **SQLite3** (usually pre-installed).  
* Git.

### **Setup Instructions**

1. **Clone the repository:**  
   git clone \<repository\_url\> \# Replace with your repo URL  
   cd mcp-law-office-db \# Or your repository directory name

2. **Create and activate a virtual environment:**  
   \# Replace python3.11 with your specific version  
   python3.11 \-m venv .venv  
   source .venv/bin/activate

3. **Install dependencies using uv:**  
   uv pip install "mcp\[cli\]" "pydantic\>=2.0.0"

4. **Install the project package in editable mode:**  
   pip install \-e .

5. **Initialize/Update the database:**  
   * **First time:** Run python setup\_law\_office.py (Follow prompts).  
   * **Applying updates (like new triggers):** Run python db\_schema\_update.py (or similar update scripts provided). **Always back up your database first\!**

### **3.1 Key Tables**

* clients: Stores client information (client\_id, client\_name, contact\_info).  
* matters: Stores legal matter details (matter\_id, client\_id, matter\_name, matter\_status).  
* case\_file\_entries: Stores individual records related to a matter (documents, emails, notes). Includes metadata (type, date, received, sent, title, from, to, cc, attachments) and content (content, content\_original, synopsis, comments).  
* billing\_entries: Stores potentially billable time entries. Includes links to substantiating case\_file\_entries, time window (billing\_start, billing\_stop), calculated billing\_hours, category, description, and crucial audit fields (billing\_substantiation, activity\_confidence, timing\_confidence, confidence\_rationale).  
* client\_invoices: Header information for client invoices (invoice\_id, invoice\_number, client\_id, matter\_id, status, totals, dates, validity flag).  
* invoice\_billing\_items: Junction table linking billing\_entries to client\_invoices. Tracks item status (draft, committed).  
* calendar\_events: Stores deadlines, meetings, and other scheduled events related to matters.

### **3.2 Key Triggers**

* **Timestamps:** Automatically set created and last\_modified fields in relevant tables (auto\_timestamps.py logic).  
* **Invoice Totals:** Update total\_hours, total\_amount, balance\_due on client\_invoices when items are added/removed from invoice\_billing\_items.  
* **Strict Overlap Rejection (Critical):** BEFORE INSERT and BEFORE UPDATE triggers on billing\_entries (prevent\_overlap\_before\_insert, prevent\_overlap\_before\_update) check if the new/updated time window overlaps with any *committed* entry on a *submitted* invoice. If an overlap exists, the trigger raises an error (RAISE(ABORT, ...)) and **rejects** the change, preventing the overlap.  
* **Invoice Submission:**  
  * mark\_committed\_billing\_entries: Sets invoice\_billing\_items.status to 'committed' and records date\_submitted when client\_invoices.status changes to 'submitted'.  
  * enforce\_validity\_on\_submit: (Secondary check) Prevents updating client\_invoices.status to 'submitted' if the is\_valid flag is 0 (though the primary rejection now happens earlier).  
  * prevent\_double\_billing: Prevents submitting an invoice if any of its items are *already* committed on *another* submitted invoice.

### **3.3 Key Views**

* available\_billing\_entries: Shows billing\_entries not yet committed to a submitted invoice.  
* draft\_invoices\_with\_committed\_entries: (Less relevant with strict rejection) Shows draft invoices containing items already committed elsewhere (indicates an issue).

## **4\. MCP Tools (tool\_handlers.py)**

*(See tool\_handlers.py for complete input schemas)*

* **list\_tables**: Lists database tables.  
* **describe\_table**: Shows columns and types for a table.  
* **read\_query**: Executes a *single* SELECT query.  
* **write\_query**: Executes a *single* non-SELECT, non-CREATE query.  
* **create\_table**: Executes a *single* CREATE TABLE statement.  
* **execute\_script**: Executes *multiple* SQL statements (semicolon-separated). **Use for batch operations.**  
* **record\_case\_entry**: Inserts a new record into case\_file\_entries with provided metadata and verbatim content.  
* **update\_case\_entry\_synopsis**: Updates only the synopsis and/or comments fields of an existing case\_file\_entries record.  
* **record\_billable\_time**: Inserts a new record into billing\_entries with all required fields, including substantiation and confidence details determined by the AI. The database trigger prevent\_overlap\_before\_insert will reject this operation if the time conflicts with committed entries.  
* **get\_unbilled\_time**: Retrieves billing entries not yet committed to a submitted invoice, optionally filtered by client or matter. Uses the available\_billing\_entries view.  
* **calculate\_billing\_hours**: Utility to calculate duration between two datetimes with specified rounding.  
* **create\_invoice**: Creates a new header record in client\_invoices with 'draft' status.  
* **add\_billing\_to\_invoice**: Links a billing\_entries record to a draft client\_invoices record via invoice\_billing\_items. Updates invoice totals via triggers.  
* **check\_invoice\_validity**: Reports the status of the is\_valid flag on a draft client\_invoices record (maintained by triggers).  
* **submit\_invoice**: Attempts to change a draft client\_invoices record's status to 'submitted'. Relies on triggers (enforce\_validity\_on\_submit, prevent\_double\_billing) to perform final checks and reject if necessary. Also triggers mark\_committed\_billing\_entries.  
* **generate\_weekly\_timesheet**: Queries billing\_entries for a specific matter and week, returning a formatted text timesheet.

## **5\. MCP Resources (resource\_handlers.py)**

*(See resource\_handlers.py for details)*

* **case://summary/all**: Summary list of all matters.  
* **case://summary/{matter\_id}**: Detailed summary for a specific matter, including recent entries and billing category totals.  
* **billing://report/all**: List of the latest 50 billing entries across all matters.  
* **billing://report/{matter\_id}**: Full billing report for a specific matter, showing billed/unbilled status.  
* **billing://client/{client\_id}**: Consolidated report for a client, summarizing matters, billing by category per matter, and invoices.  
* **invoice://detail/{invoice\_id}**: Detailed view of an invoice header and its line items.  
* **deadline://list/{matter\_id}**: List of upcoming events/deadlines for a matter from the calendar\_events table.

## **6\. MCP Prompts (prompt\_handlers.py)**

*(See prompt\_handlers.py for details)*

* **new-matter**: Guides the AI through creating client/matter records and initial setup using appropriate tools.  
* **billing-analysis**: Initiates billing analysis, guiding the AI on which tools (read\_query, get\_unbilled\_time) and tables to use for data gathering.  
* **create-invoice**: Provides a step-by-step workflow for the AI to create an invoice using the relevant tools (create\_invoice, get\_unbilled\_time, add\_billing\_to\_invoice, check\_invoice\_validity, submit\_invoice).  
* **document-intake**: Guides the AI through extracting metadata and using record\_case\_entry to add a new document/email to the case file.  
* **case-timeline**: Guides the AI to use read\_query on case\_file\_entries to generate and format a chronological timeline.

## **7\. Key Workflows**

### **7.1 Document Intake**

1. User provides document text/context (possibly via document-intake prompt).  
2. AI parses text, extracts metadata (date, type, title, parties, etc.) based on system prompt rules.  
3. AI prepares verbatim content and generates synopsis.  
4. AI calls record\_case\_entry tool with all data.  
5. Server inserts data into case\_file\_entries.

### **7.2 Multi-Pass Billing (AI-Driven)**

*(Based on System Prompt Section 11.7)*

1. **Pass 1 (Intake):** Done via Document Intake workflow above. AI can optionally use update\_case\_entry\_synopsis if needed.  
2. **Pass 2 (Identification/Confidence):**  
   * AI uses read\_query to fetch relevant case\_file\_entries.  
   * AI analyzes entries based on system prompt rules (11.7.3) to identify billable activities.  
   * AI reconstructs/infers time windows (billing\_start, billing\_stop) where necessary (rules 11.2.3, 11.5).  
   * AI determines billing\_category, billing\_description, billing\_substantiation.  
   * AI assesses activity\_confidence, timing\_confidence, and confidence\_rationale.  
   * AI may use calculate\_billing\_hours for verification.  
   * AI calls record\_billable\_time with the fully determined data for each entry.  
   * **Server:** record\_billable\_time handler attempts INSERT. Database trigger prevent\_overlap\_before\_insert checks against committed time and **rejects** the insert with an error if an overlap is found.  
3. **Pass 3 (Verification/QC):**  
   * AI reviews the entries created in Pass 2 (potentially using read\_query on billing\_entries or get\_unbilled\_time).  
   * AI checks for logical sequence errors, duration inconsistencies, category mismatches, low confidence entries based on system prompt rules (11.7.4).  
   * If errors are found, AI uses write\_query (for UPDATE/DELETE on *unbilled* entries) or re-calls record\_billable\_time (if recreating) to make corrections. Database triggers will reject updates that cause overlaps.  
4. **Pass 4 (Invoice Generation/Reporting):**  
   * AI uses create\_invoice tool.  
   * AI uses get\_unbilled\_time to identify items for the invoice.  
   * AI uses add\_billing\_to\_invoice repeatedly.  
   * AI uses check\_invoice\_validity (reads the flag maintained by triggers).  
   * If valid, AI uses submit\_invoice. Server attempts update; triggers perform final checks and commit items.  
   * AI can use generate\_weekly\_timesheet or read\_query to format reports.

### **7.3 Deadline Management**

1. AI receives information about a deadline/event.  
2. AI uses write\_query with an INSERT statement for the calendar\_events table.  
3. User/AI requests upcoming deadlines via the deadline://list/{matter\_id} resource.  
4. Server's handle\_read\_resource queries calendar\_events and returns the formatted list.

## **8\. Future Considerations**

* Add tools for managing clients and matters directly (e.g., create\_client, update\_matter\_status).  
* Implement more sophisticated reporting tools or resources.  
* Add tools/resources for managing calendar\_events.  
* Consider adding user roles/permissions if multiple users interact via the AI.  
* Enhance error handling and reporting from tools back to the AI.