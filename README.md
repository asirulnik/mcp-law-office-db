# Law Office SQLite MCP Server
[![smithery badge](https://smithery.ai/badge/@asirulnik/mcp-law-office-db)](https://smithery.ai/server/@asirulnik/mcp-law-office-db)

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
- Multi-statement transactions and batch operations via `execute_script` tool

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

### Installing via Smithery

To install Law Office Database Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@asirulnik/mcp-law-office-db):

```bash
npx -y @smithery/cli install @asirulnik/mcp-law-office-db --client claude
```

### Prerequisites
- **Python 3.10 or higher (Python 3.11+ recommended)**. Check with `python3.11 --version` (or similar). If needed, install using your system's package manager (e.g., `brew install python@3.11` on macOS).
- **uv**: A fast Python package installer. Install from [astral.sh](https://astral.sh/uv#installation) (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
- **SQLite3** (usually pre-installed on macOS/Linux).
- Git (for cloning).

### Setup Instructions

1.  **Clone the repository:**
    ```bash
    git clone <repository_url> # Replace with your repo URL
    cd mcp-law-office-db # Or your repository directory name
    ```

2.  **Create and activate a virtual environment (using your Python 3.10+ interpreter):**
    ```bash
    # Replace python3.11 with your specific version (e.g., python3.10)
    python3.11 -m venv .venv
    source .venv/bin/activate
    ```
    *(You should see `(.venv)` at the start of your terminal prompt)*

3.  **Upgrade pip (optional but recommended):**
    ```bash
    python3 -m pip install --upgrade pip
    ```

4.  **Install dependencies using `uv`:**
    *(This installs `mcp` and its extras, plus `pydantic`)*
    ```bash
    uv pip install "mcp[cli]" "pydantic>=2.0.0"
    ```

5.  **Install the project package in editable mode:**
    ```bash
    pip install -e .
    ```

6.  **Initialize the database:**
    *(This script sets up the SQLite schema)*
    ```bash
    python setup_law_office.py
    ```
    *(Follow prompts to optionally add sample data)*

## Usage

### Starting the Server Manually (for testing)
Ensure your virtual environment is active (`source .venv/bin/activate`) and run:
```bash
python run_server.py --db-path ./database/law_office.db
````

## Claude Desktop Integration (Recommended)

1.  **Find your `claude_desktop_config.json` file.**
    * macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
    * Windows: `%APPDATA%\Claude\claude_desktop_config.json`
    * Linux: `~/.config/Claude/claude_desktop_config.json`

2.  **Add or modify the `mcpServers` entry for this server.** Replace `<absolute_path_to_repo>` with the full path to where you cloned the repository (e.g., `/Users/andrewsirulnik/claude_mcp_servers/mcp-law-office-db`).

    ```json
    {
      "mcpServers": {
        "law-office_db": {
          "command": "<absolute_path_to_repo>/.venv/bin/python3",
          "args": [
            "<absolute_path_to_repo>/run_server.py",
            "--db-path",
            "<absolute_path_to_repo>/database/law_office.db"
          ],
          "cwd": "<absolute_path_to_repo>"
        }
        // Add other servers here if needed
      }
      // Other Claude Desktop settings...
    }
    ```

3.  **Save the configuration file.**

4.  **Restart Claude Desktop.** The server should now be available in the MCP integration menu.
