"""
Prompt handlers for the Law Office SQLite MCP Server.
Provides implementations for specialized prompts related to legal work.
"""

import logging
from typing import Any, Dict
import mcp.types as types

logger = logging.getLogger('mcp_law_office_server.prompts')

def list_prompts():
    """List available prompts for the Law Office SQLite MCP Server"""
    logger.debug("Handling list_prompts request")
    return [
        types.Prompt(
            name="new-matter",
            description="Create a new legal matter for a client",
            arguments=[
                types.PromptArgument(
                    name="client_id",
                    description="Client ID to create the matter for",
                    required=True,
                ),
                types.PromptArgument(
                    name="matter_name",
                    description="Name of the legal matter",
                    required=True,
                ),
                types.PromptArgument(
                    name="matter_type",
                    description="Type of legal matter (litigation, transaction, etc.)",
                    required=True,
                )
            ],
        ),
        types.Prompt(
            name="billing-analysis",
            description="Analyze billing patterns for a client or matter",
            arguments=[
                types.PromptArgument(
                    name="client_id",
                    description="Client ID to analyze",
                    required=False,
                ),
                types.PromptArgument(
                    name="matter_id",
                    description="Matter ID to analyze",
                    required=False,
                )
            ],
        ),
        types.Prompt(
            name="create-invoice",
            description="Create an invoice for billable time",
            arguments=[
                types.PromptArgument(
                    name="matter_id",
                    description="Matter ID to create invoice for",
                    required=True,
                )
            ],
        )
    ]

def handle_new_matter_prompt(db, arguments: dict[str, str]) -> types.GetPromptResult:
    """Handle the new-matter prompt"""
    if not arguments or "client_id" not in arguments or "matter_name" not in arguments or "matter_type" not in arguments:
        raise ValueError("Missing required arguments for new-matter prompt")
    
    client_id = arguments["client_id"]
    matter_name = arguments["matter_name"]
    matter_type = arguments["matter_type"]
    
    # Get client details
    client_query = "SELECT * FROM clients WHERE client_id = ?"
    client_results = db._execute_query(client_query, [client_id])
    
    if not client_results:
        raise ValueError(f"Client not found: {client_id}")
    
    client = client_results[0]
    
    text = f"I'm creating a new legal matter for {client['client_name']} (Client ID: {client_id}).\n\n"
    text += f"The matter will be named: {matter_name}\n"
    text += f"Type: {matter_type}\n\n"
    text += "Please help me set up this matter by describing:\n\n"
    text += "1. Initial case file entries that should be created\n"
    text += "2. Any billable time that should be recorded for the matter setup\n"
    text += "3. Any important deadlines or dates that should be tracked\n\n"
    text += "Let me guide you through the process of creating the new matter and setting up the initial documentation."
    
    return types.GetPromptResult(
        description="Prompt for creating a new legal matter",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(type="text", text=text),
            )
        ],
    )

def handle_billing_analysis_prompt(db, arguments: dict[str, str]) -> types.GetPromptResult:
    """Handle the billing-analysis prompt"""
    if not arguments or ("client_id" not in arguments and "matter_id" not in arguments):
        raise ValueError("Missing required arguments for billing-analysis prompt")
    
    text = "Please analyze the billing patterns based on the following criteria:\n\n"
    
    if "client_id" in arguments and arguments["client_id"]:
        client_id = arguments["client_id"]
        # Get client details
        client_query = "SELECT * FROM clients WHERE client_id = ?"
        client_results = db._execute_query(client_query, [client_id])
        
        if not client_results:
            raise ValueError(f"Client not found: {client_id}")
        
        client = client_results[0]
        text += f"**Client:** {client['client_name']} (ID: {client_id})\n"
        text += "Analyze billing patterns across all matters for this client.\n\n"
    
    if "matter_id" in arguments and arguments["matter_id"]:
        matter_id = arguments["matter_id"]
        # Get matter details
        matter_query = """
        SELECT m.*, c.client_name 
        FROM matters m JOIN clients c ON m.client_id = c.client_id 
        WHERE m.matter_id = ?
        """
        matter_results = db._execute_query(matter_query, [matter_id])
        
        if not matter_results:
            raise ValueError(f"Matter not found: {matter_id}")
        
        matter = matter_results[0]
        text += f"**Matter:** {matter['matter_name']} (ID: {matter_id})\n"
        text += f"**Client:** {matter['client_name']} (ID: {matter['client_id']})\n"
        text += "Focus on billing patterns for this specific matter.\n\n"
    
    text += "Please analyze:\n\n"
    text += "1. Billing efficiency (billable vs. non-billable time)\n"
    text += "2. Distribution of time across different billing categories\n"
    text += "3. Time entry patterns and potential optimization opportunities\n"
    text += "4. Invoice performance metrics\n"
    text += "5. Recommendations for improving billing practices\n\n"
    text += "You can use the billing-related resources to gather the necessary data for your analysis."
    
    return types.GetPromptResult(
        description="Prompt for analyzing billing patterns",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(type="text", text=text),
            )
        ],
    )

def handle_create_invoice_prompt(db, arguments: dict[str, str]) -> types.GetPromptResult:
    """Handle the create-invoice prompt"""
    if not arguments or "matter_id" not in arguments:
        raise ValueError("Missing required arguments for create-invoice prompt")
    
    matter_id = arguments["matter_id"]
    # Get matter details
    matter_query = """
    SELECT m.*, c.client_name, c.client_id 
    FROM matters m JOIN clients c ON m.client_id = c.client_id 
    WHERE m.matter_id = ?
    """
    matter_results = db._execute_query(matter_query, [matter_id])
    
    if not matter_results:
        raise ValueError(f"Matter not found: {matter_id}")
    
    matter = matter_results[0]
    
    # Get unbilled time entries
    unbilled_query = """
    SELECT 
        be.billing_id,
        be.billing_category,
        be.billing_start,
        be.billing_hours,
        be.billing_description
    FROM 
        billing_entries be
    LEFT JOIN 
        invoice_billing_items ibi ON be.billing_id = ibi.billing_id
    WHERE 
        be.matter_id = ? AND ibi.id IS NULL
    ORDER BY 
        be.billing_start
    """
    
    unbilled = db._execute_query(unbilled_query, [matter_id])
    
    # Get last invoice number
    invoice_query = "SELECT MAX(invoice_number) as last_number FROM client_invoices"
    invoice_result = db._execute_query(invoice_query)
    last_number = invoice_result[0]['last_number'] if invoice_result[0]['last_number'] else 1000
    next_number = last_number + 1
    
    text = f"I'd like to create a new invoice for matter '{matter['matter_name']}' (ID: {matter_id}).\n\n"
    text += f"**Client:** {matter['client_name']} (ID: {matter['client_id']})\n"
    text += f"**Suggested Invoice Number:** {next_number}\n\n"
    
    if unbilled:
        total_hours = sum(entry['billing_hours'] for entry in unbilled)
        text += f"There are {len(unbilled)} unbilled time entries totaling {total_hours} hours.\n\n"
        text += "Examples of unbilled entries:\n\n"
        
        for i, entry in enumerate(unbilled[:3]):
            text += f"{i+1}. {entry['billing_category']} - {entry['billing_hours']} hours - {entry['billing_description'][:50]}...\n"
        
        if len(unbilled) > 3:
            text += f"...and {len(unbilled) - 3} more entries.\n\n"
    else:
        text += "There are no unbilled time entries for this matter.\n\n"
    
    text += "Please help me complete the invoice creation process by:\n\n"
    text += "1. Confirming the invoice number to use\n"
    text += "2. Selecting which unbilled entries to include in this invoice\n"
    text += "3. Validating for time conflicts with previous invoices\n"
    text += "4. Finalizing the invoice for submission\n\n"
    text += "You can use the law office tools to create the invoice, add billing entries, and submit it."
    
    return types.GetPromptResult(
        description="Prompt for creating an invoice",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(type="text", text=text),
            )
        ],
    )

def handle_get_prompt(db, name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
    """Handle prompt retrieval requests"""
    logger.debug(f"Handling get_prompt request for prompt: {name}")
    
    if name == "new-matter":
        return handle_new_matter_prompt(db, arguments)
    
    elif name == "billing-analysis":
        return handle_billing_analysis_prompt(db, arguments)
    
    elif name == "create-invoice":
        return handle_create_invoice_prompt(db, arguments)
    
    else:
        raise ValueError(f"Unsupported prompt: {name}")
