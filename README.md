<!-- Content from local file -->
# **Law Office SQLite MCP Server**

A Model Context Protocol (MCP) server implementation for law office database management, specializing in client records, case filing, time tracking, and invoice management.

## **Overview**

This server provides a specialized database interface for law firms, enabling AI assistants (like Claude) to interact with critical practice data to:

* Manage client and matter records.
* Track case file entries (documents, communications, notes) with verbatim content rules.
* Log billable time with detailed substantiation, confidence levels, and links to case activities.
* Create, validate, and manage client invoices according to defined workflows.
* Enforce business rules for proper legal billing, including strict time conflict prevention.
* Generate formatted reports like weekly timesheets.
* Track deadlines and calendar events.

## **Features**

### **Core Database Operations**

* Standard SQL operations (SELECT, INSERT, UPDATE, DELETE) via specific tools (`read_query`, `write_query`).
* Table management (`create_table`) and schema information (`describe_table`, `list_tables`).
* Multi-statement transactions and batch operations via `execute_script` tool (use semicolon separation).

### **Specialized Legal Tools (Highlights)**

* `record_case_entry`: Adds documents/emails to case files with metadata.
* `record_billable_time`: Logs time with required substantiation, confidence levels, and rationale.
* `get_unbilled_time`: Tracks unbilled work by client or matter.
* `create_invoice`, `add_billing_to_invoice`, `check_invoice_validity`, `submit_invoice`: Manage the invoice lifecycle.
* `generate_weekly_timesheet`: Creates formatted timesheets for review.
    *(Note: `update_case_entry_synopsis` and `calculate_billing_hours` are described in the spec but not yet implemented as distinct tools).*

### **Database Schema & Logic**

* Tables for clients, matters, case file entries, billing entries, invoices, invoice items, and calendar events (see Specification document).
* Comprehensive billing and invoice workflow support.
* Automatic `created` and `last_modified` timestamp management.
* **Strict Conflict Prevention:** Database triggers (BEFORE INSERT/UPDATE on `billing_entries`) automatically reject attempts to save time entries that overlap with previously committed time on submitted invoices.

### **Dynamic Resources**

* Summaries for all cases (`case://summary/all`) or specific matters (`case://summary/{matter_id}`).
* Billing reports for all entries (`billing://report/all`), specific matters (`billing://report/{matter_id}`), or clients (`billing://client/{client_id}`).
* Detailed invoice views (`invoice://detail/{invoice_id}`).
* Upcoming deadline lists (`deadline://list/{matter_id}`).

### **Guided Prompts**

* Structured prompts to initiate common workflows like creating new matters (`new-matter`), analyzing billing (`billing-analysis`), creating invoices (`create-invoice`), and adding documents (`document-intake`).
    *(Note: `case-timeline` is described in the spec but not yet implemented).*

## **Installation**

*(Assuming prerequisites: Python 3.10+, uv, SQLite3, Git)*

1.  **Clone the repository:**
    ```bash
    git clone <repository_url> # Replace with your repo URL
    cd mcp-law-office-db # Or your repository directory name
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # Replace python3.11 with your specific version if needed
    python3.11 -m venv .venv
    source .venv/bin/activate # On Windows use: .venv\Scripts\activate
    ```

3.  **Install dependencies using uv:**
    ```bash
    uv pip install "mcp[cli]" "pydantic>=2.0.0"
    ```

4.  **Install the project package in editable mode:**
    ```bash
    # Use pip for editable installs
    pip install -e .
    ```

5.  **Initialize/Update the database:**
    * **First time:** Run `python setup_law_office.py` (Follow prompts). **Ensure this script exists and creates the schema defined in the Specification.**
    * **Applying updates (like new triggers):** Run `python db_schema_update.py` (or similar update scripts provided). **Always back up your database first!**

## **Usage**

### **Starting the Server Manually (for testing)**

Ensure your virtual environment is active (`source .venv/bin/activate`) and run:

    # Make sure the db path points to your initialized database
    # Use the entry point defined in setup.py (e.g., mcp-server-law-office)
    mcp-server-law-office --db-path ./database/law_office.db --log-level DEBUG

    # Or run the main script directly if no entry point is set up yet:
    # python src/mcp_server_sqlite/server_law_office.py --db-path ./database/law_office.db

## **Claude Desktop Integration (Recommended)**

1.  **Find your `claude_desktop_config.json` file.** Common locations:
    * macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
    * Windows: `%APPDATA%\Claude\claude_desktop_config.json`
    * Linux: `~/.config/Claude/claude_desktop_config.json`

2.  **Add or modify the `mcpServers` entry.**
    * Replace `<absolute_path_to_repo>` with the full path to where you cloned this repository.
    * Ensure the Python executable path is correct for your OS (e.g., `<absolute_path_to_repo>/.venv/bin/python3` or `<absolute_path_to_repo>\.venv\Scripts\python.exe`).
    * Use the server name defined in `server_law_office.py` (which is "law-office-sqlite").

    ```json
    {
      "mcpServers": {
        "law-office-sqlite": {
          "command": "<absolute_path_to_repo>/.venv/bin/python3",
          "args": [
            "-m",
            "mcp_server_sqlite",
            "--db-path",
            "<absolute_path_to_repo>/database/law_office.db",
            "--log-level",
            "INFO"
          ],
          "cwd": "<absolute_path_to_repo>"
        }
      }
    }
    ```

    *(Note: Using `python -m mcp_server_sqlite` assumes your package is installed correctly and its entry point is configured.)*

3.  **Save the configuration file.**

4.  **Restart Claude Desktop.** The "law-office-sqlite" server should now appear in the MCP integration menu.

## **Development Notes**

* The server relies heavily on database triggers for data integrity (timestamps, invoice totals, time conflict rejection). See the Specification document for schema and trigger details. Ensure `setup_law_office.py` or similar correctly defines these.
* The core multi-pass billing logic is intended to be driven by the AI assistant following the system prompt, using the provided tools for database interaction.
