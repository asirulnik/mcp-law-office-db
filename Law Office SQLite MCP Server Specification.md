<!-- Content from local file -->
# **Law Office SQLite MCP Server - Application Specification**

**Version:** 1.1 (Reflecting implemented tools/prompts)

## **1. Introduction**

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

## **2. Architecture**

### **2.1 Overview**

The application is a Python-based MCP server that interacts with a local SQLite database file. It uses the mcp-server-sdk library to handle the MCP communication protocol.

### **2.2 Components**

* **MCP Server Core (`server_law_office.py`):** Initializes the server, registers handlers, and manages the main execution loop.
* **Database Interface (`database.py`):** Contains the `SqliteDatabase` class responsible for connecting to the SQLite file and executing SQL queries (`_execute_query`, `_execute_script`).
* **Tool Handlers (`tool_handlers.py`):** Defines the available tools (schema and description via `list_tools`) and implements their execution logic (`handle_call_tool`).
* **Resource Handlers (`resource_handlers.py`):** Defines available dynamic resources (schema and description via `handle_list_resources`) and implements the logic to generate their content (`handle_read_resource`).
* **Prompt Handlers (`prompt_handlers.py`):** Defines available guided prompts (schema and description via `list_prompts`) and implements the logic to generate the initial prompt text (`handle_get_prompt`).
* **Timestamp Logic (`auto_timestamps.py`):** Provides functions to manage automatic `created` and `last_modified` timestamp columns via database triggers.
* **Database Schema (Appendix_1_SQLite_DB_Schema in System Prompt / `setup_law_office.py`):** Defines the structure of the SQLite database, including tables, columns, views, and crucial triggers.
* **Database Setup/Update Scripts (`setup_law_office.py`, `db_schema_update.py`):** Scripts to initialize the database schema and apply subsequent modifications (like trigger updates).

### **2.3 Data Storage**

* All persistent data is stored in a single SQLite database file (default: `./database/law_office.db`).
* Configuration (server command, args) is managed externally via the MCP client (e.g., `claude_desktop_config.json`).

## **3. Database Schema**

*(This section assumes the schema definition provided previously is accurate and applied by `setup_law_office.py` or similar.)*

### **3.1 Key Tables**

* `clients`: Stores client information (`client_id`, `client_name`, `contact_info`).
* `matters`: Stores legal matter details (`matter_id`, `client_id`, `matter_name`, `matter_status`).
* `case_file_entries`: Stores individual records related to a matter (documents, emails, notes). Includes metadata (`type`, `date`, `received`, `sent`, `title`, `from`, `to`, `cc`, `attachments`) and content (`content`, `content_original`, `synopsis`, `comments`).
* `billing_entries`: Stores potentially billable time entries. Includes links to substantiating `case_file_entries`, time window (`billing_start`, `billing_stop`), calculated `billing_hours`, category, description, and crucial audit fields (`billing_substantiation`, `activity_confidence`, `timing_confidence`, `confidence_rationale`).
* `client_invoices`: Header information for client invoices (`invoice_id`, `invoice_number`, `client_id`, `matter_id`, `status`, totals, dates, validity flag).
* `invoice_billing_items`: Junction table linking `billing_entries` to `client_invoices`. Tracks item status (`draft`, `committed`).
* `calendar_events`: Stores deadlines, meetings, and other scheduled events related to matters.

### **3.2 Key Triggers**

* **Timestamps:** Automatically set `created` and `last_modified` fields in relevant tables (via `auto_timestamps.py` logic invoked during table creation/initialization).
* **Invoice Totals:** Update `total_hours`, `total_amount`, `balance_due` on `client_invoices` when items are added/removed from `invoice_billing_items`.
* **Strict Overlap Rejection (Critical):** `BEFORE INSERT` and `BEFORE UPDATE` triggers on `billing_entries` (`prevent_overlap_before_insert`, `prevent_overlap_before_update`) check if the new/updated time window overlaps with any *committed* entry on a *submitted* invoice. If an overlap exists, the trigger raises an error (`RAISE(ABORT, ...)`) and **rejects** the change, preventing the overlap.
* **Invoice Submission:**
    * `prevent_double_billing`: `BEFORE UPDATE` trigger on `client_invoices` prevents submitting an invoice if any of its items are *already* committed on *another* submitted invoice.
    * `mark_committed_billing_entries`: `AFTER UPDATE` trigger on `client_invoices` sets `invoice_billing_items.status` to 'committed' and records `date_submitted` when `client_invoices.status` changes from 'draft' to 'submitted'.

### **3.3 Key Views**

* `available_billing_entries`: Shows `billing_entries` not yet committed to a submitted invoice.

## **4. MCP Tools (tool_handlers.py)**

*(See `tool_handlers.py` for complete input schemas)*

* **`list_tables`**: Lists database tables.
* **`describe_table`**: Shows columns and types for a table.
* **`read_query`**: Executes a *single* SELECT query.
* **`write_query`**: Executes a *single* non-SELECT, non-CREATE query.
* **`create_table`**: Executes a *single* CREATE TABLE statement.
* **`execute_script`**: Executes *multiple* SQL statements (semicolon-separated). **Use for batch operations.**
* **`record_case_entry`**: Inserts a new record into `case_file_entries` with provided metadata and verbatim content. Requires `matter_id`, `type`, `title`, `content`, `date`. Optional: `from_party`, `to_party`, `cc`, `attachments`, `synopsis`, `comments`, `received_time`, `sent_time`.
* **`record_billable_time`**: Inserts a new record into `billing_entries`. Requires `matter_id`, `substantiating_entry_id_1`, `billing_category`, `billing_start`, `billing_stop`, `billing_description`, `billing_substantiation`, `activity_confidence`, `timing_confidence`, `confidence_rationale`. Optional: `billing_hours` (calculated if omitted), `substantiating_entry_id_2` through `_5`. Database trigger `prevent_overlap_before_insert` will reject this operation if the time conflicts with committed entries.
* **`get_unbilled_time`**: Retrieves billing entries not yet committed to a submitted invoice, optionally filtered by client or matter. Uses the `available_billing_entries` view.
* **`create_invoice`**: Creates a new header record in `client_invoices` with 'draft' status. Requires `client_id`, `matter_id`, `invoice_number` (integer).
* **`add_billing_to_invoice`**: Links a `billing_entries` record to a draft `client_invoices` record via `invoice_billing_items`. Requires `invoice_id`, `billing_id`. Updates invoice totals via triggers. Rejects if billing entry is not available or invoice is not draft.
* **`check_invoice_validity`**: Reports the status of the `is_valid` flag on a draft `client_invoices` record. *Note: Less critical due to strict rejection triggers on billing entries and invoice submission.* Requires `invoice_id`.
* **`submit_invoice`**: Attempts to change a draft `client_invoices` record's status to 'submitted'. Requires `invoice_id`. Relies on triggers (`prevent_double_billing`, `mark_committed_billing_entries`) to perform final checks and reject if necessary.
* **`generate_weekly_timesheet`**: Queries `billing_entries` for a specific matter and week, returning a formatted text timesheet. Requires `matter_id`, `week_start_date` (YYYY-MM-DD).

*(Removed entries for `update_case_entry_synopsis`, `calculate_billing_hours` as they are not implemented as distinct tools).*

## **5. MCP Resources (resource_handlers.py)**

*(See `resource_handlers.py` for details)*

* **`case://summary/all`**: Summary list of all matters.
* **`case://summary/{matter_id}`**: Detailed summary for a specific matter, including recent entries and billing category totals.
* **`billing://report/all`**: List of the latest 50 billing entries across all matters.
* **`billing://report/{matter_id}`**: Full billing report for a specific matter, showing billed/unbilled status.
* **`billing://client/{client_id}`**: Consolidated report for a client, summarizing matters, billing by category per matter, and invoices.
* **`invoice://detail/{invoice_id}`**: Detailed view of an invoice header and its line items.
* **`deadline://list/{matter_id}`**: List of upcoming events/deadlines for a matter from the `calendar_events` table.

## **6. MCP Prompts (prompt_handlers.py)**

*(See `prompt_handlers.py` for details)*

* **`new-matter`**: Guides the AI through creating client/matter records and initial setup using appropriate tools. Requires `client_id`, `matter_name`, `matter_type`.
* **`billing-analysis`**: Initiates billing analysis, guiding the AI on which tools (`read_query`, `get_unbilled_time`) and tables/views to use for data gathering. Requires `client_id` or `matter_id`.
* **`create-invoice`**: Provides a step-by-step workflow for the AI to create an invoice using the relevant tools (`create_invoice`, `get_unbilled_time`, `add_billing_to_invoice`, `submit_invoice`). Requires `matter_id`.
* **`document-intake`**: Guides the AI through extracting metadata and using `record_case_entry` to add a new document/email to the case file. Requires `matter_id`, `document_preview`. Optional: `document_source`.

*(Removed entry for `case-timeline` as it is not implemented).*

## **7. Key Workflows**

### **7.1 Document Intake**

1.  User provides document text/context (possibly triggering the **`document-intake`** prompt with `matter_id` and `document_preview`).
2.  AI follows the prompt's instructions: analyzes text, extracts metadata (`date`, `type`, `title`, parties, etc.), prepares verbatim `content` and `content_original`, generates `synopsis`.
3.  AI calls `record_case_entry` tool with all required and extracted data.
4.  Server inserts data into `case_file_entries`. AI confirms with `entry_id`.

### **7.2 Multi-Pass Billing (AI-Driven)**

*(Based on System Prompt Section 11.7, adapted for implemented tools)*

1.  **Pass 1 (Intake):** Done via Document Intake workflow (7.1).
2.  **Pass 2 (Identification/Confidence):**
    * AI uses `read_query` to fetch relevant `case_file_entries`.
    * AI analyzes entries based on system prompt rules (11.7.3) to identify billable activities.
    * AI reconstructs/infers time windows (`billing_start`, `billing_stop`) where necessary (rules 11.2.3, 11.5).
    * AI determines `billing_category`, `billing_description`, `billing_substantiation`.
    * AI assesses `activity_confidence`, `timing_confidence`, and `confidence_rationale`.
    * AI calls `record_billable_time` with the fully determined data for each entry.
    * **Server:** `record_billable_time` handler attempts INSERT. Database trigger `prevent_overlap_before_insert` checks against committed time and **rejects** the insert with an error if an overlap is found. AI must handle this error (e.g., by adjusting time, marking as non-billable, or reporting the conflict).
3.  **Pass 3 (Verification/QC):**
    * AI reviews the entries created in Pass 2 (using `read_query` on `billing_entries` or `get_unbilled_time`).
    * AI checks for logical sequence errors, duration inconsistencies, category mismatches, low confidence entries based on system prompt rules (11.7.4).
    * If errors are found in *unbilled* entries, AI uses `write_query` (for UPDATE/DELETE). Database triggers will reject updates that cause overlaps.
4.  **Pass 4 (Invoice Generation/Reporting):**
    * AI uses `create_invoice` tool (potentially triggered by `create-invoice` prompt).
    * AI uses `get_unbilled_time` to identify items for the invoice.
    * AI uses `add_billing_to_invoice` repeatedly for selected items.
    * AI uses `invoice://detail/{invoice_id}` resource for review.
    * If correct, AI uses `submit_invoice`. Server attempts update; triggers perform final checks and commit items or reject with an error.
    * AI can use **`generate_weekly_timesheet`** or `read_query` to format reports.

### **7.3 Deadline Management**

1.  AI receives information about a deadline/event.
2.  AI uses `write_query` with an INSERT statement for the `calendar_events` table.
3.  User/AI requests upcoming deadlines via the `deadline://list/{matter_id}` resource.
4.  Server's `handle_read_resource` queries `calendar_events` and returns the formatted list.

## **8. Future Considerations**

* Add tools for managing clients and matters directly (e.g., `create_client`, `update_matter_status`).
* Implement `update_case_entry_synopsis` and `calculate_billing_hours` tools.
* Implement `case-timeline` prompt.
* Implement more sophisticated reporting tools or resources.
* Add tools/resources for managing `calendar_events`.
* Consider adding user roles/permissions if multiple users interact via the AI.
* Enhance error handling and reporting from tools back to the AI.
