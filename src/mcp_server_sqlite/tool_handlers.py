# Inside prompt_handlers.py

"""
Prompt handlers for the Law Office SQLite MCP Server.
Provides implementations for specialized prompts related to legal work.
"""

import logging
from typing import Any, Dict
import mcp.types as types

# Initialize logger for this module
logger = logging.getLogger('mcp_law_office_server.prompts')

def list_prompts():
    """List available prompts for the Law Office SQLite MCP Server"""
    logger.debug("Handling list_prompts request")
    return [
        # Existing prompts (potentially modified)
        types.Prompt(
            name="new-matter",
            description="Guides the creation of a new legal matter, client record (if needed), and initial setup.",
            arguments=[
                 # Keep arguments simple, let the prompt guide the interaction
                types.PromptArgument(
                    name="client_name",
                    description="Name of the client (new or existing).",
                    required=True,
                ),
                types.PromptArgument(
                    name="matter_name",
                    description="Name of the new legal matter.",
                    required=True,
                ),
                # Removed matter_type, can be discussed in the prompt flow
            ],
        ),
        types.Prompt(
            name="billing-analysis",
            description="Initiates an analysis of billing patterns for a client or matter, guiding tool usage.",
            arguments=[
                types.PromptArgument(
                    name="client_id",
                    description="Client ID to analyze (optional, if analyzing specific client).",
                    required=False,
                ),
                types.PromptArgument(
                    name="matter_id",
                    description="Matter ID to analyze (optional, if analyzing specific matter).",
                    required=False,
                )
                # Can add date range arguments if needed
            ],
        ),
        types.Prompt(
            name="create-invoice",
            description="Guides the process of creating an invoice for billable time for a specific matter.",
            arguments=[
                types.PromptArgument(
                    name="matter_id",
                    description="Matter ID to create the invoice for.",
                    required=True,
                ),
                 types.PromptArgument(
                    name="invoice_number",
                    description="The unique number to assign to this new invoice.",
                    required=True,
                )
            ],
        ),
        # New task-specific prompts
        types.Prompt(
            name="document-intake",
            description="Guides the process of adding a new document or email to a specific case file.",
            arguments=[
                 types.PromptArgument(
                    name="matter_id",
                    description="The ID of the matter this document belongs to.",
                    required=True,
                ),
                 types.PromptArgument(
                    name="document_text",
                    description="Paste the full text of the document or email here.",
                    required=True,
                ),
                 types.PromptArgument(
                    name="document_type",
                    description="Specify the type (e.g., 'Email', 'Letter', 'Pleading', 'Note').",
                    required=True,
                ),
                 # Optional metadata can be passed or extracted by AI
                 types.PromptArgument(
                    name="document_title",
                    description="Title or subject of the document (optional).",
                    required=False,
                ),
                 types.PromptArgument(
                    name="document_date",
                    description="Authoritative date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS) (optional).",
                    required=False,
                ),
            ]
        ),
        types.Prompt(
            name="case-timeline",
            description="Generates a chronological timeline of events for a specific matter.",
            arguments=[
                 types.PromptArgument(
                    name="matter_id",
                    description="The ID of the matter to generate the timeline for.",
                    required=True,
                ),
                 types.PromptArgument(
                    name="start_date",
                    description="Start date for the timeline (YYYY-MM-DD) (optional).",
                    required=False,
                ),
                 types.PromptArgument(
                    name="end_date",
                    description="End date for the timeline (YYYY-MM-DD) (optional).",
                    required=False,
                ),
            ]
        )
    ]

# --- Handler Implementations ---

def handle_new_matter_prompt(db, arguments: dict[str, str]) -> types.GetPromptResult:
    """Handle the new-matter prompt"""
    if not arguments or "client_name" not in arguments or "matter_name" not in arguments:
        raise ValueError("Missing required arguments: client_name, matter_name")

    client_name = arguments["client_name"]
    matter_name = arguments["matter_name"]

    # Check if client exists
    client_query = "SELECT client_id, client_name FROM clients WHERE client_name = ?"
    client_results = db._execute_query(client_query, [client_name])

    client_id = None
    client_exists_message = ""
    if client_results:
        client_id = client_results[0]['client_id']
        client_exists_message = f"Client '{client_name}' already exists with ID: {client_id}."
    else:
        client_exists_message = f"Client '{client_name}' does not currently exist in the database."

    text = f"Okay, let's set up the new matter: '{matter_name}' for the client: '{client_name}'.\n\n"
    text += f"{client_exists_message}\n\n"
    text += "Please guide me through the next steps:\n\n"

    if not client_results:
         text += f"1.  **Create Client Record:** Shall I create a new record for '{client_name}'? You can use the `write_query` tool with an INSERT statement for the `clients` table.\n"
         text += "    `INSERT INTO clients (client_name, contact_info) VALUES (?, ?)`\n"
         text += "    Provide the contact info if available.\n\n"
         text += f"2.  **Create Matter Record:** Once the client exists (or if they already did), use `write_query` to create the matter record linked to the client ID.\n"
         text += "    `INSERT INTO matters (client_id, matter_name, matter_status) VALUES (?, ?, 'Open')`\n\n"
    else:
         text += f"1.  **Create Matter Record:** The client exists (ID: {client_id}). Use `write_query` to create the matter record linked to this client ID.\n"
         text += f"    `INSERT INTO matters (client_id, matter_name, matter_status) VALUES ({client_id}, '{matter_name}', 'Open')`\n\n" # Example with values filled

    text += "3.  **Initial Case Entries:** Are there any initial documents, emails, or notes to add to the case file for this matter? Use the `record_case_entry` tool for each item.\n\n"
    text += "4.  **Initial Billing:** Was there any billable time spent setting up this matter (e.g., initial client consultation)? Use `record_billable_time` to log it, ensuring you provide all required substantiation and confidence details.\n\n"
    text += "Let me know how you'd like to proceed."

    return types.GetPromptResult(
        description=f"Guide for creating matter '{matter_name}' for client '{client_name}'",
        messages=[
            types.PromptMessage(
                role="user", # Presenting instructions to the AI assistant
                content=types.TextContent(type="text", text=text),
            )
        ],
    )

def handle_billing_analysis_prompt(db, arguments: dict[str, str] | None) -> types.GetPromptResult:
    """Handle the billing-analysis prompt - Guides AI on tool usage"""
    # Arguments are optional, analysis can be general if none provided
    client_id = arguments.get("client_id") if arguments else None
    matter_id = arguments.get("matter_id") if arguments else None

    text = "Okay, let's analyze billing patterns.\n\n"
    target = "the entire firm"
    filter_clause = ""
    params = []

    if matter_id:
        # Validate matter exists and get details
        matter_query = "SELECT m.matter_name, c.client_name FROM matters m JOIN clients c ON m.client_id = c.client_id WHERE m.matter_id = ?"
        matter_info = db._execute_query(matter_query, [matter_id])
        if not matter_info: raise ValueError(f"Matter ID {matter_id} not found.")
        target = f"matter '{matter_info[0]['matter_name']}' (ID: {matter_id}) for client '{matter_info[0]['client_name']}'"
        filter_clause = "WHERE be.matter_id = ?"
        params.append(matter_id)
    elif client_id:
         # Validate client exists
        client_query = "SELECT client_name FROM clients WHERE client_id = ?"
        client_info = db._execute_query(client_query, [client_id])
        if not client_info: raise ValueError(f"Client ID {client_id} not found.")
        target = f"client '{client_info[0]['client_name']}' (ID: {client_id})"
        filter_clause = "WHERE be.matter_id IN (SELECT matter_id FROM matters WHERE client_id = ?)"
        params.append(client_id)

    text += f"**Analysis Target:** {target}\n\n"
    text += "**Instructions for Analysis:**\n\n"
    text += "To perform the analysis, please use the available tools to gather the necessary data:\n\n"
    text += f"1.  **Query Billing Data:** Use `read_query` to select relevant fields from the `billing_entries` table.\n"
    text += f"    *Example Query Structure:*\n    `SELECT billing_category, billing_hours, billing_start, activity_confidence, timing_confidence FROM billing_entries be {filter_clause} ORDER BY billing_start`\n"
    text += "    *(Remember to provide parameters if filtering)*\n\n"
    text += f"2.  **Query Invoice Data (if applicable):** Use `read_query` to get information from `client_invoices` and `invoice_billing_items` tables, joining with `billing_entries` if needed.\n"
    text += f"    *Example:* `SELECT ci.status, ci.total_hours, ci.total_amount FROM client_invoices ci {filter_clause.replace('be.matter_id', 'ci.matter_id')}`\n\n" # Adjust filter clause
    text += "3.  **Analyze the Data:** Based on the data retrieved, analyze the following aspects:\n"
    text += "    * Time distribution across billing categories.\n"
    text += "    * Entries with 'low' activity or timing confidence.\n"
    text += "    * Total hours billed vs. potentially unbilled time (use `get_unbilled_time` tool for comparison if needed).\n"
    text += "    * Any apparent patterns or anomalies in time entries or descriptions.\n\n"
    text += "4.  **Present Findings:** Summarize your analysis and provide actionable insights or recommendations based on the data.\n"

    return types.GetPromptResult(
        description=f"Guide for analyzing billing patterns for {target}",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(type="text", text=text),
            )
        ],
    )

def handle_create_invoice_prompt(db, arguments: dict[str, str]) -> types.GetPromptResult:
    """Handle the create-invoice prompt - Guides AI through the process"""
    if not arguments or "matter_id" not in arguments or "invoice_number" not in arguments:
        raise ValueError("Missing required arguments: matter_id, invoice_number")

    matter_id = arguments["matter_id"]
    invoice_number = arguments["invoice_number"]

    # Get matter and client details
    matter_query = "SELECT m.matter_name, m.client_id, c.client_name FROM matters m JOIN clients c ON m.client_id = c.client_id WHERE m.matter_id = ?"
    matter_info = db._execute_query(matter_query, [matter_id])
    if not matter_info: raise ValueError(f"Matter ID {matter_id} not found.")
    matter_name = matter_info[0]['matter_name']
    client_id = matter_info[0]['client_id']
    client_name = matter_info[0]['client_name']

    text = f"Okay, let's create Invoice #{invoice_number} for matter '{matter_name}' (ID: {matter_id}, Client: '{client_name}', ID: {client_id}).\n\n"
    text += "**Invoice Creation Workflow:**\n\n"
    text += f"1.  **Create Invoice Record:** Use the `create_invoice` tool with `client_id={client_id}`, `matter_id={matter_id}`, and `invoice_number={invoice_number}`. Note the returned `invoice_id`.\n\n"
    text += f"2.  **Identify Billable Items:** Use the `get_unbilled_time` tool with `matter_id={matter_id}` to list available billing entries.\n\n"
    text += "3.  **Select & Add Items:** Review the unbilled items. For each item you want to include on this invoice, use the `add_billing_to_invoice` tool, providing the `invoice_id` (from step 1) and the `billing_id` of the item.\n\n"
    text += "4.  **Verify Invoice:** Once all desired items are added, use the `check_invoice_validity` tool with the `invoice_id`. This checks for time conflicts based on database triggers.\n\n"
    text += "5.  **Submit Invoice:** If `check_invoice_validity` confirms the invoice is VALID, use the `submit_invoice` tool with the `invoice_id` to finalize it.\n\n"
    text += "**Important:** If `check_invoice_validity` reports INVALID, you must resolve the time conflicts (e.g., by removing items using `write_query` on `invoice_billing_items` or adjusting source `billing_entries` times) before attempting to submit again.\n\n"
    text += "Please proceed with step 1."

    return types.GetPromptResult(
        description=f"Guide for creating invoice {invoice_number} for matter {matter_id}",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(type="text", text=text),
            )
        ],
    )

# --- New Prompt Handlers ---

def handle_document_intake_prompt(db, arguments: dict[str, str]) -> types.GetPromptResult:
    """Handles the document-intake prompt"""
    required_args = ["matter_id", "document_text", "document_type"]
    if not arguments or not all(k in arguments for k in required_args):
        raise ValueError(f"Missing required arguments for document-intake: {required_args}")

    matter_id = arguments["matter_id"]
    doc_text = arguments["document_text"] # Keep it short for the prompt text
    doc_type = arguments["document_type"]
    doc_title = arguments.get("document_title")
    doc_date = arguments.get("document_date")

    # Verify matter exists
    matter_query = "SELECT matter_name FROM matters WHERE matter_id = ?"
    matter_info = db._execute_query(matter_query, [matter_id])
    if not matter_info: raise ValueError(f"Matter ID {matter_id} not found.")
    matter_name = matter_info[0]['matter_name']

    text = f"Okay, let's add a '{doc_type}' document to the case file for matter '{matter_name}' (ID: {matter_id}).\n\n"
    text += "**Document Intake Steps:**\n\n"
    text += "1.  **Extract Metadata:** Review the provided document text and identify key metadata:\n"
    text += "    * `date`: The authoritative date/time (Use rules from System Prompt 10.1.2.1). Use format 'YYYY-MM-DD HH:MM:SS'.\n"
    text += "    * `received` / `sent`: If it's an email, extract these times.\n"
    text += "    * `from` / `to` / `cc`: Identify parties if applicable.\n"
    text += "    * `title`: Use the provided title or derive one (e.g., email subject).\n"
    text += "    * `attachments`: Note any mentioned attachments.\n\n"
    text += "2.  **Prepare Content:** Ensure the `content` field contains the *exact, verbatim* text of the document (applying only permitted modifications from System Prompt 6.2.1.1.5).\n\n"
    text += "3.  **Generate Synopsis:** Create a brief `synopsis` summarizing the document's main point.\n\n"
    text += "4.  **Record Entry:** Use the `record_case_entry` tool, providing all extracted metadata and the prepared content and synopsis.\n"
    text += "    * `matter_id`: " + str(matter_id) + "\n"
    text += "    * `type`: '" + doc_type + "'\n"
    text += "    * `title`: Use extracted/provided title ('" + (doc_title or "[Determine Title]") + "').\n"
    text += "    * `content`: Provide the full verbatim text.\n"
    text += "    * `date`: Provide the determined authoritative date ('" + (doc_date or "[Determine Date]") + "').\n"
    text += "    * *(Include other optional fields like `from`, `to`, `received`, `sent`, `synopsis` as determined)*\n\n"
    text += "5.  **Confirm:** Check the tool's response to ensure the entry was created successfully and note the new `entry_id`.\n"

    # Include the document text preview in the prompt for the AI
    text += "\n**Document Text Preview:**\n"
    text += "```\n"
    text += doc_text[:500] + ("..." if len(doc_text) > 500 else "") # Show preview
    text += "\n```\n"
    text += "\nPlease proceed with extracting metadata and recording the entry."


    return types.GetPromptResult(
        description=f"Guide for adding a {doc_type} to matter {matter_id}",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(type="text", text=text),
            )
        ],
    )

def handle_case_timeline_prompt(db, arguments: dict[str, str] | None) -> types.GetPromptResult:
    """Handles the case-timeline prompt"""
    if not arguments or "matter_id" not in arguments:
        raise ValueError("Missing required argument: matter_id")

    matter_id = arguments["matter_id"]
    start_date = arguments.get("start_date")
    end_date = arguments.get("end_date")

    # Verify matter exists
    matter_query = "SELECT matter_name FROM matters WHERE matter_id = ?"
    matter_info = db._execute_query(matter_query, [matter_id])
    if not matter_info: raise ValueError(f"Matter ID {matter_id} not found.")
    matter_name = matter_info[0]['matter_name']

    text = f"Okay, let's generate a case timeline for matter '{matter_name}' (ID: {matter_id}).\n\n"
    date_range_text = "all available entries"
    date_filter_clause = ""
    params = [matter_id]

    if start_date and end_date:
        date_range_text = f"entries between {start_date} and {end_date}"
        date_filter_clause = "AND date(date) BETWEEN ? AND ?"
        params.extend([start_date, end_date])
    elif start_date:
        date_range_text = f"entries on or after {start_date}"
        date_filter_clause = "AND date(date) >= ?"
        params.append(start_date)
    elif end_date:
        date_range_text = f"entries on or before {end_date}"
        date_filter_clause = "AND date(date) <= ?"
        params.append(end_date)

    text += f"**Timeline Scope:** {date_range_text}.\n\n"
    text += "**Timeline Generation Steps:**\n\n"
    text += "1.  **Query Case Entries:** Use the `read_query` tool to retrieve relevant information from `case_file_entries` for the specified matter and date range. Select fields like `entry_id`, `date`, `type`, `title`, and `synopsis` (or the start of `content` if synopsis is null).\n"
    text += f"    *Example Query:*\n    `SELECT entry_id, date, type, title, COALESCE(synopsis, SUBSTR(content, 1, 100)) as summary FROM case_file_entries WHERE matter_id = ? {date_filter_clause} ORDER BY date ASC`\n"
    text += "    *(Remember to provide parameters)*\n\n"
    text += "2.  **Format Timeline:** Process the query results and format them into a clear, chronological list. Include the date, type, title, and a brief summary for each significant event.\n"
    text += "    *Example Format per entry:*\n    `YYYY-MM-DD HH:MM:SS - [Type] - [Title] - [Summary...]`\n\n"
    text += "3.  **Present Timeline:** Output the formatted timeline.\n\n"
    text += "Please execute the query and generate the timeline."

    return types.GetPromptResult(
        description=f"Guide for generating case timeline for matter {matter_id}",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(type="text", text=text),
            )
        ],
    )

# --- Main Handler Dispatch ---

def handle_get_prompt(db, name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
    """Handle prompt retrieval requests by dispatching to specific handlers"""
    logger.debug(f"Handling get_prompt request for prompt: {name} with args: {arguments}")

    # Ensure arguments is a dict, even if None was passed
    arguments = arguments or {}

    if name == "new-matter":
        return handle_new_matter_prompt(db, arguments)
    elif name == "billing-analysis":
        return handle_billing_analysis_prompt(db, arguments)
    elif name == "create-invoice":
        return handle_create_invoice_prompt(db, arguments)
    elif name == "document-intake":
        return handle_document_intake_prompt(db, arguments)
    elif name == "case-timeline":
        return handle_case_timeline_prompt(db, arguments)
    else:
        logger.error(f"Unknown or unsupported prompt requested: {name}")
        raise ValueError(f"Unsupported prompt: {name}")

