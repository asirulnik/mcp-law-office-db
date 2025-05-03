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

* Standard SQL operations (SELECT, INSERT, UPDATE, DELETE) via specific tools (read\_query, write\_query).  
* Table management (create\_table) and schema information (describe\_table, list\_tables).  
* Multi-statement transactions and batch operations via execute\_script tool (use semicolon separation).

### **Specialized Legal Tools (Highlights)**

* record\_case\_entry: Adds documents/emails to case files with metadata.  
* update\_case\_entry\_synopsis: Updates summaries/comments without altering original content.  
* record\_billable\_time: Logs time with required substantiation, confidence levels, and rationale.  
* get\_unbilled\_time: Tracks unbilled work by client or matter.  
* create\_invoice, add\_billing\_to\_invoice, check\_invoice\_validity, submit\_invoice: Manage the invoice lifecycle.  
* calculate\_billing\_hours: Utility for calculating time durations with rounding.  
* generate\_weekly\_timesheet: Creates formatted timesheets for review.

### **Database Schema & Logic**

* Tables for clients, matters, case file entries, billing entries, invoices, invoice items, and calendar events (see details below).  
* Comprehensive billing and invoice workflow support.  
* Automatic created and last\_modified timestamp management.  
* **Strict Conflict Prevention:** Database triggers (BEFORE INSERT/UPDATE on billing\_entries) automatically reject attempts to save time entries that overlap with previously committed time on submitted invoices.

### **Dynamic Resources**

* Summaries for all cases (case://summary/all) or specific matters (case://summary/{matter\_id}).  
* Billing reports for all entries (billing://report/all), specific matters (billing://report/{matter\_id}), or clients (billing://client/{client\_id}).  
* Detailed invoice views (invoice://detail/{invoice\_id}).  
* Upcoming deadline lists (deadline://list/{matter\_id}).

### **Guided Prompts**

* Structured prompts to initiate common workflows like creating new matters (new-matter), analyzing billing (billing-analysis), creating invoices (create-invoice), adding documents (document-intake), and generating timelines (case-timeline).


## **Usage**

### **Starting the Server Manually (for testing)**

Ensure your virtual environment is active (source .venv/bin/activate) and run:  
\# Make sure the db path points to your initialized database  
python run\_server.py \--db-path ./database/law\_office.db

## **Claude Desktop Integration (Recommended)**

1. **Find your claude\_desktop\_config.json file.**  
   * macOS: \~/Library/Application Support/Claude/claude\_desktop\_config.json  
   * Windows: %APPDATA%\\Claude\\claude\_desktop\_config.json  
   * Linux: \~/.config/Claude/claude\_desktop\_config.json  
2. **Add or modify the mcpServers entry.** Replace \<absolute\_path\_to\_repo\> with the full path to where you cloned this repository. Ensure the python executable path (.venv/bin/python3 or .venv/Scripts/python.exe on Windows) is correct.  
   {  
     "mcpServers": {  
       "law-office-sqlite": { // Use the server name defined in server\_law\_office.py  
         "command": "\<absolute\_path\_to\_repo\>/.venv/bin/python3", // Adjust for Windows if needed  
         "args": \[  
           "\<absolute\_path\_to\_repo\>/run\_server.py", // Or the correct entry point if using package script  
           "--db-path",  
           "\<absolute\_path\_to\_repo\>/database/law\_office.db"  
         \],  
         "cwd": "\<absolute\_path\_to\_repo\>"  
       }  
       // Add other servers here if needed  
     }  
     // Other Claude Desktop settings...  
   }

3. **Save the configuration file.**  
4. **Restart Claude Desktop.** The "law-office-sqlite" server should now be available in the MCP integration menu.

## **Development Notes**

* The server relies heavily on database triggers for data integrity (timestamps, invoice totals, time conflict rejection). See db\_schema\_update.py and the schema details above.  
* The core multi-pass billing logic is intended to be driven by the AI assistant following the system prompt, using the provided tools for database interaction.