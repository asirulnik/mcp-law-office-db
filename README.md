# Law Office SQLite MCP Server

A Model Context Protocol (MCP) server implementation for law office database management, specializing in client records, case filing, time tracking, and invoice management.

## Overview

This server provides a specialized database interface for law firms to:
- Manage client and matter records
- Track case file entries (documents, communications, notes)
- Log billable time with evidentiary links to case activities
- Create and validate client invoices
- Enforce business rules for proper legal billing

## Features

### Core Database Operations
- Standard SQL operations (SELECT, INSERT, UPDATE, DELETE)
- Table management and schema information
- Multi-statement transactions and batch operations

### Specialized Legal Tools
- `record_case_entry`: Add documentation to case files
- `record_billable_time`: Log time with proper substantiation
- `get_unbilled_time`: Track unbilled work by client or matter
- `create_invoice`: Generate new client invoices
- `add_billing_to_invoice`: Associate time entries with invoices
- `check_invoice_validity`: Validate invoices for billing conflicts
- `submit_invoice`: Finalize invoices for client submission

### Database Schema
- Client and matter management
- Case file documentation system
- Comprehensive billing and invoice workflow
- Automatic timestamp management
- Conflict detection for overlapping time entries

## Installation

### Prerequisites
- Python 3.10 or higher
- SQLite3
- Model Context Protocol (MCP) framework

### Setup
1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Initialize the database:
   ```bash
   python setup_law_office.py
   ```

## Usage

### Starting the Server
```bash
python run_server.py --db-path ./database/law_office.db
```

### Claude Integration
This server is designed to work with Claude via the Model Context Protocol. Add it to your Claude configuration:

```json
"mcpServers": {
  "law-office": {
    "command": "python",
    "args": [
      "run_server.py",
      "--db-path",
      "./database/law_office.db"
    ]
  }
}
```

## Development

This project was forked from the [MCP SQLite Server](https://github.com/modelcontextprotocol/servers/tree/main/src/sqlite) and customized for law office management. Key modifications include:

- Specialized database schema for legal matters
- Time tracking and billing validation
- Invoice management workflow
- Matter-specific documentation tools

## License

MIT License
