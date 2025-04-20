"""
Resource handlers for the Law Office SQLite MCP Server.
Provides implementations for handling dynamic resources like case summaries,
billing reports, and invoice details.
"""

import logging
from pydantic import AnyUrl
from typing import Any, Dict

logger = logging.getLogger('mcp_law_office_server.resources')

def handle_list_resources():
    """Handle resource listing - returns a list of available resources"""
    from mcp.types import Resource, ResourceTemplate
    from pydantic import AnyUrl
    
    logger.debug("Handling list_resources request")
    return [
        Resource(
            uri=AnyUrl("case://summary/all"),
            name="All Cases Summary",
            description="Summary of all case matters",
            mimeType="text/plain",
        ),
        Resource(
            uri=AnyUrl("billing://report/all"),
            name="All Billing Report",
            description="Report of all billing entries",
            mimeType="text/plain",
        ),
        ResourceTemplate(
            uriTemplate="case://summary/{matter_id}",
            name="Case Summary",
            description="Summary of a specific case matter",
            mimeType="text/plain",
        ),
        ResourceTemplate(
            uriTemplate="billing://report/{matter_id}",
            name="Matter Billing Report",
            description="Billing report for a specific matter",
            mimeType="text/plain",
        ),
        ResourceTemplate(
            uriTemplate="billing://client/{client_id}",
            name="Client Billing Report",
            description="Billing report for a specific client",
            mimeType="text/plain",
        ),
        ResourceTemplate(
            uriTemplate="invoice://detail/{invoice_id}",
            name="Invoice Detail",
            description="Detailed information about a specific invoice",
            mimeType="text/plain",
        )
    ]

def handle_case_summary(db, path: str) -> str:
    """Handle case summary resources"""
    if path == "all":
        # Get summary of all matters
        query = """
        SELECT 
            m.matter_id,
            m.matter_name,
            c.client_name,
            COUNT(cf.id) as num_entries,
            MAX(cf.date) as last_updated,
            (SELECT COUNT(*) FROM billing_entries be WHERE be.matter_id = m.matter_id) as num_billing_entries
        FROM 
            matters m
        JOIN 
            clients c ON m.client_id = c.client_id
        LEFT JOIN 
            case_file_entries cf ON m.matter_id = cf.matter_id
        GROUP BY 
            m.matter_id
        ORDER BY 
            last_updated DESC
        """
        
        results = db._execute_query(query)
        
        if not results:
            return "No case matters found."
        
        resource_text = "# Case Matters Summary\n\n"
        resource_text += "| ID | Client | Matter | Entries | Billing Entries | Last Updated |\n"
        resource_text += "|-----|--------|--------|---------|----------------|-------------|\n"
        
        for matter in results:
            resource_text += f"| {matter['matter_id']} | {matter['client_name']} | {matter['matter_name']} | "
            resource_text += f"{matter['num_entries']} | {matter['num_billing_entries']} | {matter['last_updated'] or 'Never'} |\n"
        
        return resource_text
    else:
        # Handle individual matter summary
        try:
            matter_id = int(path)
        except ValueError:
            raise ValueError(f"Invalid matter ID: {path}")
        
        # Get matter details
        matter_query = """
        SELECT 
            m.*, 
            c.client_name,
            (SELECT COUNT(*) FROM case_file_entries cf WHERE cf.matter_id = m.matter_id) as num_entries,
            (SELECT COUNT(*) FROM billing_entries be WHERE be.matter_id = m.matter_id) as num_billing_entries,
            (SELECT SUM(be.billing_hours) FROM billing_entries be WHERE be.matter_id = m.matter_id) as total_hours,
            (SELECT MAX(cf.date) FROM case_file_entries cf WHERE cf.matter_id = m.matter_id) as last_updated
        FROM 
            matters m
        JOIN 
            clients c ON m.client_id = c.client_id
        WHERE 
            m.matter_id = ?
        """
        
        matter_results = db._execute_query(matter_query, [matter_id])
        
        if not matter_results:
            raise ValueError(f"Matter not found: {matter_id}")
        
        matter = matter_results[0]
        
        # Get recent entries
        entries_query = """
        SELECT 
            id, type, title, date, synopsis
        FROM 
            case_file_entries
        WHERE 
            matter_id = ?
        ORDER BY 
            date DESC
        LIMIT 5
        """
        
        entries = db._execute_query(entries_query, [matter_id])
        
        # Get billing summary
        billing_query = """
        SELECT 
            billing_category, 
            COUNT(*) as count, 
            SUM(billing_hours) as total_hours
        FROM 
            billing_entries
        WHERE 
            matter_id = ?
        GROUP BY 
            billing_category
        """
        
        billing = db._execute_query(billing_query, [matter_id])
        
        # Generate resource text
        resource_text = f"# Case Matter: {matter['matter_name']}\n\n"
        resource_text += f"**Client:** {matter['client_name']} (ID: {matter['client_id']})\n"
        resource_text += f"**Matter ID:** {matter['matter_id']}\n"
        resource_text += f"**Status:** {matter['status']}\n"
        if matter['created']:
            resource_text += f"**Created:** {matter['created']}\n"
        if matter['last_modified']:
            resource_text += f"**Last Modified:** {matter['last_modified']}\n"
        resource_text += f"**Last Activity:** {matter['last_updated'] or 'No activity'}\n\n"
        
        resource_text += f"**Case File Entries:** {matter['num_entries']}\n"
        resource_text += f"**Billing Entries:** {matter['num_billing_entries']}\n"
        resource_text += f"**Total Hours:** {matter['total_hours'] or 0}\n\n"
        
        if entries:
            resource_text += "## Recent Entries\n\n"
            resource_text += "| ID | Type | Date | Title | Synopsis |\n"
            resource_text += "|-----|------|------|-------|----------|\n"
            
            for entry in entries:
                resource_text += f"| {entry['id']} | {entry['type']} | {entry['date']} | "
                resource_text += f"{entry['title']} | {entry['synopsis'] or ''} |\n"
            
            resource_text += "\n"
        
        if billing:
            resource_text += "## Billing Summary\n\n"
            resource_text += "| Category | Entries | Hours |\n"
            resource_text += "|----------|---------|-------|\n"
            
            for b in billing:
                resource_text += f"| {b['billing_category']} | {b['count']} | {b['total_hours']} |\n"
        
        return resource_text

def handle_billing_report(db, path: str) -> str:
    """Handle billing report resources"""
    if path == "all":
        # Get all billing entries
        query = """
        SELECT 
            be.billing_id,
            c.client_name,
            m.matter_name,
            be.billing_category,
            be.billing_start,
            be.billing_stop,
            be.billing_hours,
            be.billing_description,
            be.status
        FROM 
            billing_entries be
        JOIN 
            matters m ON be.matter_id = m.matter_id
        JOIN 
            clients c ON m.client_id = c.client_id
        ORDER BY 
            be.billing_start DESC
        LIMIT 50
        """
        
        results = db._execute_query(query)
        
        if not results:
            return "No billing entries found."
        
        resource_text = "# All Billing Entries\n\n"
        resource_text += "| ID | Client | Matter | Category | Date | Hours | Status | Description |\n"
        resource_text += "|-----|--------|--------|----------|------|-------|--------|-------------|\n"
        
        for entry in results:
            resource_text += f"| {entry['billing_id']} | {entry['client_name']} | {entry['matter_name']} | "
            resource_text += f"{entry['billing_category']} | {entry['billing_start']} | "
            resource_text += f"{entry['billing_hours']} | {entry['status'] or 'unbilled'} | {entry['billing_description'][:30]}... |\n"
        
        return resource_text
    else:
        # Get billing for specific matter
        try:
            matter_id = int(path)
        except ValueError:
            raise ValueError(f"Invalid matter ID: {path}")
        
        # Get matter details first
        matter_query = """
        SELECT 
            m.*, 
            c.client_name
        FROM 
            matters m
        JOIN 
            clients c ON m.client_id = c.client_id
        WHERE 
            m.matter_id = ?
        """
        
        matter_results = db._execute_query(matter_query, [matter_id])
        
        if not matter_results:
            raise ValueError(f"Matter not found: {matter_id}")
        
        matter = matter_results[0]
        
        # Get billing entries
        billing_query = """
        SELECT 
            be.*,
            CASE 
                WHEN ibi.invoice_id IS NOT NULL THEN 'billed' 
                ELSE 'unbilled' 
            END as invoice_status,
            ibi.invoice_id
        FROM 
            billing_entries be
        LEFT JOIN 
            invoice_billing_items ibi ON be.billing_id = ibi.billing_id
        WHERE 
            be.matter_id = ?
        ORDER BY 
            be.billing_start DESC
        """
        
        entries = db._execute_query(billing_query, [matter_id])
        
        # Get billing summary
        summary_query = """
        SELECT 
            billing_category, 
            COUNT(*) as count, 
            SUM(billing_hours) as total_hours,
            COUNT(CASE WHEN status = 'committed' THEN 1 END) as billed_count,
            SUM(CASE WHEN status = 'committed' THEN billing_hours ELSE 0 END) as billed_hours
        FROM 
            billing_entries
        WHERE 
            matter_id = ?
        GROUP BY 
            billing_category
        """
        
        summary = db._execute_query(summary_query, [matter_id])
        
        # Generate resource text
        resource_text = f"# Billing Report: {matter['matter_name']}\n\n"
        resource_text += f"**Client:** {matter['client_name']} (ID: {matter['client_id']})\n"
        resource_text += f"**Matter ID:** {matter['matter_id']}\n\n"
        
        if summary:
            total_hours = sum(s['total_hours'] for s in summary)
            billed_hours = sum(s['billed_hours'] for s in summary)
            unbilled_hours = total_hours - billed_hours
            
            resource_text += f"**Total Hours:** {total_hours}\n"
            resource_text += f"**Billed Hours:** {billed_hours}\n"
            resource_text += f"**Unbilled Hours:** {unbilled_hours}\n\n"
            
            resource_text += "## Billing Summary\n\n"
            resource_text += "| Category | Entries | Hours | Billed Entries | Billed Hours |\n"
            resource_text += "|----------|---------|-------|---------------|-------------|\n"
            
            for s in summary:
                resource_text += f"| {s['billing_category']} | {s['count']} | {s['total_hours']} | "
                resource_text += f"{s['billed_count']} | {s['billed_hours']} |\n"
            
            resource_text += "\n"
        
        if entries:
            resource_text += "## Billing Entries\n\n"
            resource_text += "| ID | Category | Start | Stop | Hours | Status | Description |\n"
            resource_text += "|-----|----------|-------|------|-------|--------|-------------|\n"
            
            for entry in entries:
                invoice_status = f"Inv #{entry['invoice_id']}" if entry['invoice_id'] else "Unbilled"
                resource_text += f"| {entry['billing_id']} | {entry['billing_category']} | "
                resource_text += f"{entry['billing_start']} | {entry['billing_stop']} | "
                resource_text += f"{entry['billing_hours']} | {invoice_status} | {entry['billing_description'][:30]}... |\n"
        
        return resource_text

def handle_client_billing(db, client_id: str) -> str:
    """Handle client billing resources"""
    try:
        client_id = int(client_id)
    except ValueError:
        raise ValueError(f"Invalid client ID: {client_id}")
    
    # Get client details
    client_query = """
    SELECT * FROM clients WHERE client_id = ?
    """
    
    client_results = db._execute_query(client_query, [client_id])
    
    if not client_results:
        raise ValueError(f"Client not found: {client_id}")
    
    client = client_results[0]
    
    # Get matters for this client
    matters_query = """
    SELECT 
        m.*,
        (SELECT COUNT(*) FROM billing_entries be WHERE be.matter_id = m.matter_id) as billing_count,
        (SELECT SUM(be.billing_hours) FROM billing_entries be WHERE be.matter_id = m.matter_id) as billing_hours
    FROM 
        matters m
    WHERE 
        m.client_id = ?
    """
    
    matters = db._execute_query(matters_query, [client_id])
    
    # Get billing summary
    billing_query = """
    SELECT 
        m.matter_id,
        m.matter_name,
        be.billing_category,
        COUNT(*) as entry_count,
        SUM(be.billing_hours) as total_hours,
        COUNT(CASE WHEN be.status = 'committed' THEN 1 END) as billed_count,
        SUM(CASE WHEN be.status = 'committed' THEN be.billing_hours ELSE 0 END) as billed_hours
    FROM 
        billing_entries be
    JOIN 
        matters m ON be.matter_id = m.matter_id
    WHERE 
        m.client_id = ?
    GROUP BY 
        m.matter_id, be.billing_category
    """
    
    billing = db._execute_query(billing_query, [client_id])
    
    # Get invoices
    invoices_query = """
    SELECT 
        ci.*,
        m.matter_name
    FROM 
        client_invoices ci
    JOIN 
        matters m ON ci.matter_id = m.matter_id
    WHERE 
        ci.client_id = ?
    ORDER BY 
        ci.date_created DESC
    """
    
    invoices = db._execute_query(invoices_query, [client_id])
    
    # Generate resource
    resource_text = f"# Client Billing Report: {client['client_name']}\n\n"
    resource_text += f"**Client ID:** {client['client_id']}\n"
    if client['created']:
        resource_text += f"**Client Since:** {client['created']}\n"
    resource_text += "\n"
    
    if matters:
        resource_text += "## Client Matters\n\n"
        resource_text += "| ID | Matter | Status | Billing Entries | Total Hours |\n"
        resource_text += "|-----|--------|--------|----------------|------------|\n"
        
        for matter in matters:
            resource_text += f"| {matter['matter_id']} | {matter['matter_name']} | {matter['status']} | "
            resource_text += f"{matter['billing_count'] or 0} | {matter['billing_hours'] or 0} |\n"
        
        resource_text += "\n"
    
    if billing:
        # Restructure billing data by matter
        billing_by_matter = {}
        for b in billing:
            if b['matter_id'] not in billing_by_matter:
                billing_by_matter[b['matter_id']] = {
                    'matter_name': b['matter_name'],
                    'categories': [],
                    'total_hours': 0,
                    'billed_hours': 0
                }
            
            billing_by_matter[b['matter_id']]['categories'].append(b)
            billing_by_matter[b['matter_id']]['total_hours'] += b['total_hours']
            billing_by_matter[b['matter_id']]['billed_hours'] += b['billed_hours']
        
        resource_text += "## Billing Details\n\n"
        
        for matter_id, matter_data in billing_by_matter.items():
            resource_text += f"### {matter_data['matter_name']} (Matter #{matter_id})\n\n"
            resource_text += f"**Total Hours:** {matter_data['total_hours']}\n"
            resource_text += f"**Billed Hours:** {matter_data['billed_hours']}\n"
            resource_text += f"**Unbilled Hours:** {matter_data['total_hours'] - matter_data['billed_hours']}\n\n"
            
            resource_text += "| Category | Entries | Hours | Billed Entries | Billed Hours |\n"
            resource_text += "|----------|---------|-------|---------------|-------------|\n"
            
            for cat in matter_data['categories']:
                resource_text += f"| {cat['billing_category']} | {cat['entry_count']} | {cat['total_hours']} | "
                resource_text += f"{cat['billed_count']} | {cat['billed_hours']} |\n"
            
            resource_text += "\n"
    
    if invoices:
        resource_text += "## Client Invoices\n\n"
        resource_text += "| ID | Number | Matter | Date | Status | Hours | Amount | Valid |\n"
        resource_text += "|-----|--------|--------|------|--------|-------|--------|-------|\n"
        
        for invoice in invoices:
            valid_status = "✓" if invoice['is_valid'] else "✗"
            resource_text += f"| {invoice['invoice_id']} | {invoice['invoice_number']} | {invoice['matter_name']} | "
            resource_text += f"{invoice['date_created']} | {invoice['status']} | {invoice['total_hours']} | "
            resource_text += f"${invoice['total_amount']} | {valid_status} |\n"
    
    return resource_text

def handle_invoice_detail(db, invoice_id: str) -> str:
    """Handle invoice detail resources"""
    try:
        invoice_id = int(invoice_id)
    except ValueError:
        raise ValueError(f"Invalid invoice ID: {invoice_id}")
    
    # Get invoice details
    invoice_query = """
    SELECT 
        ci.*,
        c.client_name,
        m.matter_name
    FROM 
        client_invoices ci
    JOIN 
        clients c ON ci.client_id = c.client_id
    JOIN 
        matters m ON ci.matter_id = m.matter_id
    WHERE 
        ci.invoice_id = ?
    """
    
    invoice_results = db._execute_query(invoice_query, [invoice_id])
    
    if not invoice_results:
        raise ValueError(f"Invoice not found: {invoice_id}")
    
    invoice = invoice_results[0]
    
    # Get invoice items
    items_query = """
    SELECT 
        ibi.*,
        be.billing_category,
        be.billing_start,
        be.billing_stop,
        be.billing_hours,
        be.billing_description
    FROM 
        invoice_billing_items ibi
    JOIN 
        billing_entries be ON ibi.billing_id = be.billing_id
    WHERE 
        ibi.invoice_id = ?
    ORDER BY 
        be.billing_start
    """
    
    items = db._execute_query(items_query, [invoice_id])
    
    # Generate resource
    resource_text = f"# Invoice #{invoice['invoice_number']}\n\n"
    resource_text += f"**Client:** {invoice['client_name']} (ID: {invoice['client_id']})\n"
    resource_text += f"**Matter:** {invoice['matter_name']} (ID: {invoice['matter_id']})\n"
    resource_text += f"**Status:** {invoice['status']}\n"
    resource_text += f"**Created:** {invoice['date_created']}\n"
    if invoice['date_submitted']:
        resource_text += f"**Submitted:** {invoice['date_submitted']}\n"
    resource_text += f"**Version:** {invoice['version_number']}\n"
    resource_text += f"**Valid:** {'Yes' if invoice['is_valid'] else 'No'}\n"
    resource_text += f"**Last Validity Check:** {invoice['last_validity_check']}\n\n"
    
    resource_text += f"**Total Hours:** {invoice['total_hours']}\n"
    resource_text += f"**Total Amount:** ${invoice['total_amount']}\n\n"
    
    if not invoice['is_valid']:
        # Get conflict details
        conflicts_query = """
        SELECT * FROM invalid_invoice_details WHERE invoice_id = ?
        """
        
        conflicts = db._execute_query(conflicts_query, [invoice_id])
        
        if conflicts:
            resource_text += "## ⚠️ Validation Conflicts\n\n"
            resource_text += "This invoice has time conflicts that must be resolved before submission.\n\n"
            
            for conflict in conflicts:
                resource_text += f"Problem Entry: {conflict['problematic_entry_id']} "
                resource_text += f"({conflict['billing_start']} to {conflict['billing_stop']})\n"
                resource_text += f"Conflicts with: Entry {conflict['conflicting_entry_id']} "
                resource_text += f"({conflict['conflicting_start']} to {conflict['conflicting_stop']})\n\n"
    
    if items:
        resource_text += "## Invoice Items\n\n"
        resource_text += "| ID | Category | Start | Stop | Hours | Status | Description |\n"
        resource_text += "|-----|----------|-------|------|-------|--------|-------------|\n"
        
        for item in items:
            resource_text += f"| {item['billing_id']} | {item['billing_category']} | "
            resource_text += f"{item['billing_start']} | {item['billing_stop']} | "
            resource_text += f"{item['billing_hours']} | {item['status']} | {item['billing_description'][:30]}... |\n"
    
    return resource_text

def handle_read_resource(db, uri: AnyUrl) -> str:
    """Handle resource reading requests"""
    logger.debug(f"Handling read_resource request for URI: {uri}")
    uri_str = str(uri)
    
    if uri.scheme == "case":
        path = uri_str.replace("case://", "")
        if path.startswith("summary/"):
            matter_id = path.replace("summary/", "")
            return handle_case_summary(db, matter_id)
        
    elif uri.scheme == "billing":
        path = uri_str.replace("billing://", "")
        
        if path.startswith("report/"):
            report_id = path.replace("report/", "")
            return handle_billing_report(db, report_id)
        
        elif path.startswith("client/"):
            client_id = path.replace("client/", "")
            return handle_client_billing(db, client_id)
        
    elif uri.scheme == "invoice":
        path = uri_str.replace("invoice://", "")
        
        if path.startswith("detail/"):
            invoice_id = path.replace("detail/", "")
            return handle_invoice_detail(db, invoice_id)
            
    raise ValueError(f"Unsupported resource URI: {uri_str}")
