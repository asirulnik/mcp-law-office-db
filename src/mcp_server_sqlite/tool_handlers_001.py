"""
Tool handlers for the Law Office SQLite MCP Server.
Provides implementations for database operations and specialized legal tools.
"""

import logging
import sqlite3 # <-- Add this import
from typing import Any, List, Dict, Optional
import mcp.types as types

logger = logging.getLogger('mcp_law_office_server.tools')

def list_tools():
    """List available tools for the Law Office SQLite MCP Server"""
    logger.debug("Handling list_tools request")
    return [
        types.Tool(
            name="list_tables",
            description="List all tables in the database",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="describe_table",
            description="Get structure of a specific table",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {"type": "string"}
                },
                "required": ["table_name"]
            }
        ),
        types.Tool(
            name="read_query",
            description="Execute a SELECT SQL query (for multiple statements at once, use execute_script tool instead)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="write_query",
            description="Execute a non-SELECT SQL query (INSERT, UPDATE, DELETE) (for multiple statements at once, use execute_script tool instead)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="create_table",
            description="Create a new table in the database (for multiple statements at once, use execute_script tool instead)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        ),
        # --- Added execute_script ---
        types.Tool(
            name="execute_script",
            description="Execute multiple SQL statements provided as a single script string. Use for batch operations like multiple INSERTS or complex transactions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "script": {"type": "string", "description": "A single string containing multiple SQL statements separated by semicolons (;)."}
                },
                "required": ["script"]
            }
        ),
        # --- End execute_script ---
        types.Tool(
            name="record_case_entry",
            description="Record a new case file entry for a matter",
            inputSchema={
                "type": "object",
                "properties": {
                    "matter_id": {"type": "integer"},
                    "type": {"type": "string"},
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "from_party": {"type": "string"},
                    "to_party": {"type": "string"},
                    "synopsis": {"type": "string"},
                    "date": {"type": "string"}
                },
                "required": ["matter_id", "type", "title", "content"]
            }
        ),
        types.Tool(
            name="record_billable_time",
            description="Record billable time for a matter",
            inputSchema={
                "type": "object",
                "properties": {
                    "matter_id": {"type": "integer"},
                    "substantiating_entry_id_1": {"type": "integer"},
                    "billing_category": {"type": "string"},
                    "billing_start": {"type": "string"},
                    "billing_stop": {"type": "string"},
                    "billing_hours": {"type": "number"},
                    "billing_description": {"type": "string"}
                },
                "required": [
                    "matter_id",
                    "substantiating_entry_id_1",
                    "billing_category",
                    "billing_start",
                    "billing_stop",
                    "billing_description"
                ]
            }
        ),
        types.Tool(
            name="get_unbilled_time",
            description="Get unbilled time entries for a client or matter",
            inputSchema={
                "type": "object",
                "properties": {
                    "client_id": {"type": "integer"},
                    "matter_id": {"type": "integer"}
                },
                "required": []
            }
        ),
        types.Tool(
            name="create_invoice",
            description="Create a new invoice for a matter",
            inputSchema={
                "type": "object",
                "properties": {
                    "client_id": {"type": "integer"},
                    "matter_id": {"type": "integer"},
                    "invoice_number": {"type": "string"}
                },
                "required": ["client_id", "matter_id", "invoice_number"]
            }
        ),
        types.Tool(
            name="add_billing_to_invoice",
            description="Add a billing entry to an invoice",
            inputSchema={
                "type": "object",
                "properties": {
                    "invoice_id": {"type": "integer"},
                    "billing_id": {"type": "integer"}
                },
                "required": ["invoice_id", "billing_id"]
            }
        ),
        types.Tool(
            name="submit_invoice",
            description="Submit an invoice (changes status from draft to submitted)",
            inputSchema={
                "type": "object",
                "properties": {
                    "invoice_id": {"type": "integer"}
                },
                "required": ["invoice_id"]
            }
        ),
        types.Tool(
            name="check_invoice_validity",
            description="Check if an invoice has any time conflicts",
            inputSchema={
                "type": "object",
                "properties": {
                    "invoice_id": {"type": "integer"}
                },
                "required": ["invoice_id"]
            }
        )
    ]

def handle_call_tool(db, name: str, arguments: dict[str, Any] | None) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests"""
    try:
        if name == "list_tables":
            results = db._execute_query(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            return [types.TextContent(type="text", text=str(results))]

        elif name == "describe_table":
            if not arguments or "table_name" not in arguments:
                raise ValueError("Missing table_name argument")
            results = db._execute_query(
                f"PRAGMA table_info({arguments['table_name']})"
            )
            return [types.TextContent(type="text", text=str(results))]

        elif name == "read_query":
            if not arguments or "query" not in arguments:
                raise ValueError("Missing query argument")
            if not arguments["query"].strip().upper().startswith("SELECT"):
                raise ValueError("Only SELECT queries are allowed with read_query")
            results = db._execute_query(arguments["query"])
            return [types.TextContent(type="text", text=str(results))]

        elif name == "write_query":
            if not arguments or "query" not in arguments:
                raise ValueError("Missing query argument")
            if arguments["query"].strip().upper().startswith("SELECT"):
                raise ValueError("SELECT queries are not allowed with write_query, use read_query instead")
            results = db._execute_query(arguments["query"])
            return [types.TextContent(type="text", text=str(results))]

        elif name == "create_table":
            if not arguments or "query" not in arguments:
                raise ValueError("Missing query argument")
            if not arguments["query"].strip().upper().startswith("CREATE TABLE"):
                raise ValueError("Only CREATE TABLE queries are allowed with create_table")
            results = db._execute_query(arguments["query"])
            # Assuming _execute_query returns something meaningful for CREATE TABLE
            # or the logic inside _execute_query handles the success reporting well.
            # The previous version had f"Table created successfully: {results}" which might be fine.
            # For now, let's keep it simple if _execute_query gives useful feedback.
            return [types.TextContent(type="text", text=str(results))]

        # --- Added execute_script handler ---
        elif name == "execute_script":
            if not arguments or "script" not in arguments:
                raise ValueError("Missing script argument for execute_script")

            # Call the new database method
            results = db._execute_script(arguments["script"])
            # Return the success message from the method
            return [types.TextContent(type="text", text=str(results))]
        # --- End execute_script handler ---

        elif name == "get_unbilled_time":
            # Build query based on provided filters
            query = """
            SELECT
                be.billing_id,
                c.client_name,
                m.matter_name,
                be.billing_category,
                be.billing_start,
                be.billing_stop,
                be.billing_hours,
                be.billing_description
            FROM
                billing_entries be
            JOIN
                matters m ON be.matter_id = m.matter_id
            JOIN
                clients c ON m.client_id = c.client_id
            LEFT JOIN
                invoice_billing_items ibi ON be.billing_id = ibi.billing_id
            WHERE
                ibi.id IS NULL
            """

            params = []
            if arguments:
                if "client_id" in arguments and arguments["client_id"]:
                    query += " AND m.client_id = ?"
                    params.append(arguments["client_id"])
                if "matter_id" in arguments and arguments["matter_id"]:
                    query += " AND be.matter_id = ?"
                    params.append(arguments["matter_id"])

            query += " ORDER BY be.billing_start DESC"

            results = db._execute_query(query, params if params else None)

            if not results:
                return [types.TextContent(type="text", text="No unbilled time entries found.")]

            result_text = "Unbilled Time Entries:\n\n"
            result_text += "| ID | Client | Matter | Category | Start | End | Hours | Description |\n"
            result_text += "|-------|--------|--------|----------|-------|-----|-------|-------------|\n"

            total_hours = 0
            for entry in results:
                result_text += f"| {entry['billing_id']} | {entry['client_name']} | {entry['matter_name']} | "
                result_text += f"{entry['billing_category']} | {entry['billing_start']} | {entry['billing_stop']} | "
                result_text += f"{entry['billing_hours']:.2f} | {entry['billing_description'][:30]}... |\n"
                total_hours += entry['billing_hours']

            result_text += f"\nTotal Unbilled Hours: {total_hours:.2f} (${total_hours * 250:.2f} at $250/hr)"

            return [types.TextContent(type="text", text=result_text)]

        elif name == "create_invoice":
            if not arguments or not all(k in arguments for k in ["client_id", "matter_id", "invoice_number"]):
                raise ValueError("Missing required arguments for invoice creation")

            # Insert the new invoice
            query = """
            INSERT INTO client_invoices (
                invoice_number, client_id, matter_id, status,
                total_amount, total_hours, version_number
            ) VALUES (?, ?, ?, 'draft', 0, 0, 1)
            """

            params = [
                arguments["invoice_number"],
                arguments["client_id"],
                arguments["matter_id"]
            ]

            results = db._execute_query(query, params)

            # Get the ID of the newly created invoice
            invoice_id = db._execute_query(
                "SELECT last_insert_rowid() as id"
            )[0]['id']

            return [types.TextContent(
                type="text",
                text=f"Invoice created successfully. Invoice ID: {invoice_id}"
            )]

        elif name == "submit_invoice":
            if not arguments or "invoice_id" not in arguments:
                raise ValueError("Missing invoice_id argument")

            # Check if invoice exists and is in draft state
            invoice = db._execute_query(
                "SELECT * FROM client_invoices WHERE invoice_id = ?",
                [arguments["invoice_id"]]
            )

            if not invoice:
                raise ValueError(f"Invoice with ID {arguments['invoice_id']} not found")

            if invoice[0]['status'] != 'draft':
                raise ValueError("Invoice is already submitted")

            if not invoice[0]['is_valid']:
                return [types.TextContent(
                    type="text",
                    text="Cannot submit invoice: This invoice has time conflicts. Please use the check_invoice_validity tool to identify conflicts."
                )]

            # Submit the invoice
            try:
                db._execute_query(
                    "UPDATE client_invoices SET status = 'submitted' WHERE invoice_id = ?",
                    [arguments["invoice_id"]]
                )

                return [types.TextContent(
                    type="text",
                    text=f"Invoice #{invoice[0]['invoice_number']} submitted successfully. Billing entries have been committed."
                )]
            except Exception as e: # Catch specific exception if possible, e.g., sqlite3.Error
                return [types.TextContent(
                    type="text",
                    text=f"Error submitting invoice: {str(e)}"
                )]

        elif name == "check_invoice_validity":
            if not arguments or "invoice_id" not in arguments:
                raise ValueError("Missing invoice_id argument")

            # Check invoice validity
            invoice = db._execute_query(
                "SELECT invoice_id, invoice_number, is_valid, last_validity_check FROM client_invoices WHERE invoice_id = ?",
                [arguments["invoice_id"]]
            )
            
            # Check if query returned any results
            if not invoice:
                 raise ValueError(f"Invoice with ID {arguments['invoice_id']} not found")
            
            invoice = invoice[0] # Get the first row

            if invoice['is_valid']:
                return [types.TextContent(
                    type="text",
                    text=f"Invoice #{invoice['invoice_number']} is valid and can be submitted. No time conflicts found."
                )]
            else:
                # Get conflict details
                conflicts = db._execute_query(
                    "SELECT * FROM invalid_invoice_details WHERE invoice_id = ?",
                    [arguments["invoice_id"]]
                )

                result_text = f"Invoice #{invoice['invoice_number']} has time conflicts and cannot be submitted.\n\n"
                result_text += "The following billing entries have time conflicts with already committed entries:\n\n"

                for conflict in conflicts:
                    result_text += f"Problem Entry: {conflict['problematic_entry_id']} "
                    result_text += f"({conflict['billing_start']} to {conflict['billing_stop']})\n"
                    result_text += f"Conflicts with: Entry {conflict['conflicting_entry_id']} "
                    result_text += f"({conflict['conflicting_start']} to {conflict['conflicting_stop']})\n\n"

                result_text += "To resolve conflicts, you can:\n"
                result_text += "1. Remove the conflicting entries from this invoice\n"
                result_text += "2. Adjust the time of the conflicting entries to avoid overlap\n"

                return [types.TextContent(type="text", text=result_text)]

        elif name == "add_billing_to_invoice":
            if not arguments or not all(k in arguments for k in ["invoice_id", "billing_id"]):
                raise ValueError("Missing required arguments for adding billing to invoice")

            # Check if invoice exists and is in draft state
            invoice = db._execute_query(
                "SELECT * FROM client_invoices WHERE invoice_id = ?",
                [arguments["invoice_id"]]
            )

            if not invoice:
                raise ValueError(f"Invoice with ID {arguments['invoice_id']} not found")

            if invoice[0]['status'] != 'draft':
                raise ValueError("Cannot add billing to a non-draft invoice")

            # Check if billing entry exists
            billing = db._execute_query(
                "SELECT * FROM billing_entries WHERE billing_id = ?",
                [arguments["billing_id"]]
            )

            if not billing:
                raise ValueError(f"Billing entry with ID {arguments['billing_id']} not found")

            # Check if billing entry is already on this invoice
            existing = db._execute_query(
                "SELECT * FROM invoice_billing_items WHERE invoice_id = ? AND billing_id = ?",
                [arguments["invoice_id"], arguments["billing_id"]]
            )

            if existing:
                raise ValueError("This billing entry is already on this invoice")

            # Add billing entry to invoice
            db._execute_query(
                "INSERT INTO invoice_billing_items (invoice_id, billing_id, status) VALUES (?, ?, 'draft')",
                [arguments["invoice_id"], arguments["billing_id"]]
            )

            # Get updated invoice details
            updated_invoice = db._execute_query(
                "SELECT total_hours, total_amount FROM client_invoices WHERE invoice_id = ?",
                [arguments["invoice_id"]]
            )
            
            if not updated_invoice:
                 # Should not happen if invoice existed before, but handle defensively
                 raise ValueError(f"Invoice with ID {arguments['invoice_id']} could not be found after update.")

            updated_invoice = updated_invoice[0]

            return [types.TextContent(
                type="text",
                text=f"Billing entry added to invoice. Updated totals: {updated_invoice['total_hours']:.2f} hours, ${updated_invoice['total_amount']:.2f}"
            )]

        elif name == "record_case_entry":
            if not arguments or not all(k in arguments for k in ["matter_id", "type", "title", "content"]):
                raise ValueError("Missing required arguments for case entry")

            # Check if matter exists
            matter = db._execute_query(
                "SELECT * FROM matters WHERE matter_id = ?",
                [arguments["matter_id"]]
            )

            if not matter:
                raise ValueError(f"Matter with ID {arguments['matter_id']} not found")

            # Build query with available fields
            query_fields = ["matter_id", "type", "title", "content", "content_original"]
            query_values = ["?", "?", "?", "?", "?"]
            params = [
                arguments["matter_id"],
                arguments["type"],
                arguments["title"],
                arguments["content"],
                arguments["content"]  # Store original content as well
            ]

            # Add optional fields if provided
            for field in ["from_party", "to_party", "synopsis", "date"]:
                 if field in arguments and arguments[field]:
                     query_fields.append(field)
                     query_values.append("?")
                     params.append(arguments[field])

            # Create the query
            query = f"""
            INSERT INTO case_file_entries (
                {', '.join(query_fields)}
            ) VALUES (
                {', '.join(query_values)}
            )
            """

            results = db._execute_query(query, params)

            # Get the ID of the newly created entry
            entry_id = db._execute_query(
                "SELECT last_insert_rowid() as id"
            )[0]['id']

            return [types.TextContent(
                type="text",
                text=f"Case file entry created successfully. Entry ID: {entry_id}"
            )]

        elif name == "record_billable_time":
            if not arguments or not all(k in arguments for k in [
                "matter_id",
                "substantiating_entry_id_1",
                "billing_category",
                "billing_start",
                "billing_stop",
                "billing_description"
            ]):
                raise ValueError("Missing required arguments for billable time")

            # Check if matter exists
            matter = db._execute_query(
                "SELECT * FROM matters WHERE matter_id = ?",
                [arguments["matter_id"]]
            )

            if not matter:
                raise ValueError(f"Matter with ID {arguments['matter_id']} not found")

            # Check if substantiating entry exists
            entry = db._execute_query(
                "SELECT * FROM case_file_entries WHERE id = ?", # Corrected column name likely 'id' or 'entry_id'
                [arguments["substantiating_entry_id_1"]]
            )

            if not entry:
                # Assuming entry_id might be the correct column name if 'id' doesn't work
                entry = db._execute_query(
                    "SELECT * FROM case_file_entries WHERE entry_id = ?",
                    [arguments["substantiating_entry_id_1"]]
                )
                if not entry:
                    raise ValueError(f"Case file entry with ID {arguments['substantiating_entry_id_1']} not found")


            # Calculate hours if not provided
            billing_hours = arguments.get("billing_hours")
            if billing_hours is None: # Check for None explicitly
                # Would normally calculate from start/stop, but for simplicity just use 1.0
                # TODO: Implement proper time calculation if needed
                billing_hours = 1.0

            # Insert the billing entry
            query = """
            INSERT INTO billing_entries (
                matter_id,
                substantiating_entry_id_1,
                billing_category,
                billing_start,
                billing_stop,
                billing_hours,
                billing_description,
                status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'unbilled')
            """

            params = [
                arguments["matter_id"],
                arguments["substantiating_entry_id_1"],
                arguments["billing_category"],
                arguments["billing_start"],
                arguments["billing_stop"],
                billing_hours,
                arguments["billing_description"]
            ]

            results = db._execute_query(query, params)

            # Get the ID of the newly created billing entry
            billing_id = db._execute_query(
                "SELECT last_insert_rowid() as id"
            )[0]['id']

            return [types.TextContent(
                type="text",
                text=f"Billable time recorded successfully. Billing ID: {billing_id}"
            )]

        else:
            raise ValueError(f"Unsupported tool: {name}")
        # Removed the stray ")]" that was here

    except sqlite3.Error as e: # Catch specific database errors
        logger.error(f"Database error handling tool {name}: {str(e)}")
        return [types.TextContent(type="text", text=f"Database error: {str(e)}")]
    except ValueError as e: # Catch specific value errors (like missing args)
        logger.warning(f"Value error handling tool {name}: {str(e)}")
        return [types.TextContent(type="text", text=f"Input error: {str(e)}")]
    except Exception as e: # Catch any other unexpected errors
        logger.error(f"Unexpected error handling tool {name}: {str(e)}", exc_info=True) # Log traceback
        return [types.TextContent(type="text", text=f"Unexpected server error: {str(e)}")]
    # Removed the redundant 'except Exception as e' block