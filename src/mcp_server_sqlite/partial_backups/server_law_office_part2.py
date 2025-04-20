    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict[str, Any] | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
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
                )[0]
                
                return [types.TextContent(
                    type="text", 
                    text=f"Billing entry added to invoice. Updated totals: {updated_invoice['total_hours']:.2f} hours, ${updated_invoice['total_amount']:.2f}"
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
                except sqlite3.Error as e:
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
                )[0]
                
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

            elif name == "record_case_entry":
                if not arguments or not all(k in arguments for k in ["matter_id", "type", "title", "content"]):
                    raise ValueError("Missing required arguments for case entry")
                
                # Build query with optional fields
                fields = ["matter_id", "type", "title", "content"]
                values = ["?", "?", "?", "?"]
                params = [
                    arguments["matter_id"],
                    arguments["type"],
                    arguments["title"],
                    arguments["content"]
                ]
                
                for field in ["from_party", "to_party", "synopsis"]:
                    if field in arguments and arguments[field]:
                        fields.append(field)
                        values.append("?")
                        params.append(arguments[field])
                
                # Add original content
                fields.append("content_original")
                values.append("?")
                params.append(arguments["content"])
                
                # Add date if not provided
                if "date" not in arguments or not arguments["date"]:
                    fields.append("date")
                    values.append("datetime('now')")
                else:
                    fields.append("date")
                    values.append("?")
                    params.append(arguments["date"])
                
                # Create the query
                query = f"""
                INSERT INTO case_file_entries (
                    {', '.join(fields)}
                ) VALUES (
                    {', '.join(values)}
                )
                """
                
                db._execute_query(query, params)
                
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
                    "matter_id", "substantiating_entry_id_1", "billing_category", 
                    "billing_start", "billing_stop", "billing_description"
                ]):
                    raise ValueError("Missing required arguments for billable time entry")
                
                # Calculate hours if not provided
                if "billing_hours" not in arguments or not arguments["billing_hours"]:
                    # We would need to parse dates and calculate hours - simplified version
                    arguments["billing_hours"] = 1.0  # Placeholder
                
                # Build query
                query = """
                INSERT INTO billing_entries (
                    matter_id, 
                    substantiating_entry_id_1,
                    billing_category,
                    billing_start,
                    billing_stop,
                    billing_hours,
                    billing_description
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                
                params = [
                    arguments["matter_id"],
                    arguments["substantiating_entry_id_1"],
                    arguments["billing_category"],
                    arguments["billing_start"],
                    arguments["billing_stop"],
                    arguments["billing_hours"],
                    arguments["billing_description"]
                ]
                
                db._execute_query(query, params)
                
                # Get the ID of the newly created billing entry
                billing_id = db._execute_query(
                    "SELECT last_insert_rowid() as id"
                )[0]['id']
                
                return [types.TextContent(
                    type="text", 
                    text=f"Billable time recorded successfully. Billing ID: {billing_id}"
                )]

            if not arguments:
                raise ValueError("Missing arguments")

            if name == "read_query":
                if not arguments["query"].strip().upper().startswith("SELECT"):
                    raise ValueError("Only SELECT queries are allowed for read_query")
                results = db._execute_query(arguments["query"])
                return [types.TextContent(type="text", text=str(results))]

            elif name == "write_query":
                if arguments["query"].strip().upper().startswith("SELECT"):
                    raise ValueError("SELECT queries are not allowed for write_query")
                results = db._execute_query(arguments["query"])
                return [types.TextContent(type="text", text=str(results))]

            elif name == "create_table":
                if not arguments["query"].strip().upper().startswith("CREATE TABLE"):
                    raise ValueError("Only CREATE TABLE statements are allowed")
                    
                # Execute the CREATE TABLE query which will also set up timestamp triggers via _execute_query
                db._execute_query(arguments["query"])
                
                # Extract table name from the query for better user feedback
                query_upper = arguments["query"].upper()
                start_idx = query_upper.find("CREATE TABLE") + len("CREATE TABLE")
                if "IF NOT EXISTS" in query_upper[start_idx:]:
                    start_idx = query_upper.find("IF NOT EXISTS", start_idx) + len("IF NOT EXISTS")
                
                # Find table name
                while start_idx < len(arguments["query"]) and arguments["query"][start_idx].isspace():
                    start_idx += 1
                
                end_idx = start_idx
                while end_idx < len(arguments["query"]) and not arguments["query"][end_idx].isspace() and arguments["query"][end_idx] != '(':
                    end_idx += 1
                
                table_name = arguments["query"][start_idx:end_idx].strip('`"[]')
                
                # Check if the table has timestamp columns
                with closing(sqlite3.connect(db.db_path)) as conn:
                    has_created = auto_timestamps.has_column(conn, table_name, "created")
                    has_last_modified = auto_timestamps.has_column(conn, table_name, "last_modified")
                    
                    # Create response with information about automatic timestamps
                    timestamp_info = ""
                    if has_created or has_last_modified:
                        timestamp_info = " with automatic timestamps"
                        if has_created:
                            timestamp_info += " ('created' field will be set on insert)"
                        if has_last_modified:
                            if has_created:
                                timestamp_info += " and"
                            timestamp_info += " ('last_modified' field will be updated on changes)"
                
                return [types.TextContent(type="text", text=f"Table {table_name} created successfully{timestamp_info}")]

            else:
                raise ValueError(f"Unknown tool: {name}")

        except sqlite3.Error as e:
            return [types.TextContent(type="text", text=f"Database error: {str(e)}")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    # Server initialization and execution
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Law Office Database Server running with stdio transport")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="law-office-sqlite",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Law Office SQLite MCP Server")
    parser.add_argument(
        "--db-path", type=str, default="./database/mcp_server.db", help="Path to SQLite database file"
    )
    parser.add_argument(
        "--log-level", type=str, default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )

    args = parser.parse_args()

    # Configure logging
    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {args.log_level}")

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )

    # Create a separate logger for the application
    app_logger = logging.getLogger("mcp_law_office_server")
    app_logger.setLevel(numeric_level)

    # Run the server
    import asyncio
    asyncio.run(main(args.db_path))
