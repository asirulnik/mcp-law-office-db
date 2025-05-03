# Inside resource_handlers.py

"""
Resource handlers for the Law Office SQLite MCP Server.
Provides implementations for handling dynamic resources like case summaries,
billing reports, invoice details, and deadlines.
"""

import logging
from pydantic import AnyUrl
from typing import Any, Dict, List
from datetime import datetime, timedelta # Added timedelta

# Initialize logger for this module
logger = logging.getLogger('mcp_law_office_server.resources')

def handle_list_resources():
    """Handle resource listing - returns a list of available resources"""
    from mcp.types import Resource, ResourceTemplate
    from pydantic import AnyUrl

    logger.debug("Handling list_resources request")
    return [
        # Existing Resources
        Resource(
            uri=AnyUrl("case://summary/all"),
            name="All Cases Summary",
            description="Summary of all active case matters.",
            mimeType="text/plain",
        ),
        Resource(
            uri=AnyUrl("billing://report/all"),
            name="All Billing Report",
            description="Report of the latest 50 billing entries across all matters.",
            mimeType="text/plain",
        ),
        ResourceTemplate(
            uriTemplate="case://summary/{matter_id}",
            name="Case Summary",
            description="Detailed summary of a specific case matter.",
            mimeType="text/plain",
        ),
        ResourceTemplate(
            uriTemplate="billing://report/{matter_id}",
            name="Matter Billing Report",
            description="Complete billing report for a specific matter.",
            mimeType="text/plain",
        ),
        ResourceTemplate(
            uriTemplate="billing://client/{client_id}",
            name="Client Billing Report",
            description="Consolidated billing report for all matters of a specific client.",
            mimeType="text/plain",
        ),
        ResourceTemplate(
            uriTemplate="invoice://detail/{invoice_id}",
            name="Invoice Detail",
            description="Detailed information and line items for a specific invoice.",
            mimeType="text/plain",
        ),
        # New Resource for Deadlines
        ResourceTemplate(
            uriTemplate="deadline://list/{matter_id}",
            name="Matter Deadlines",
            description="Lists upcoming deadlines and events for a specific matter from the calendar.",
            mimeType="text/plain",
        )
    ]

# --- Individual Resource Generation Functions ---

def handle_case_summary_all(db) -> str:
    """Generates summary of all matters"""
    query = """
    SELECT
        m.matter_id,
        m.matter_name,
        c.client_name,
        m.matter_status, -- Added status
        (SELECT COUNT(*) FROM case_file_entries cf WHERE cf.matter_id = m.matter_id) as num_entries,
        MAX(cf.date) as last_activity -- Renamed from last_updated for clarity
        -- Removed billing counts for brevity in the 'all' summary
    FROM
        matters m
    JOIN
        clients c ON m.client_id = c.client_id
    LEFT JOIN
        case_file_entries cf ON m.matter_id = cf.matter_id
    -- Optionally filter by status, e.g., WHERE m.matter_status = 'Open'
    GROUP BY
        m.matter_id
    ORDER BY
        last_activity DESC NULLS LAST, m.matter_id -- Ensure consistent ordering
    """
    results = db._execute_query(query)
    if not results: return "No case matters found."

    resource_text = "# All Case Matters Summary\n\n"
    resource_text += "| Matter ID | Client | Matter Name | Status | Entries | Last Activity |\n"
    resource_text += "|-----------|--------|-------------|--------|---------|---------------|\n"
    for matter in results:
        last_act = matter.get('last_activity', 'N/A') or 'N/A' # Handle None
        if last_act != 'N/A':
             try: # Format date nicely
                 last_act = datetime.strptime(last_act.split('.')[0], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
             except ValueError: pass # Keep original if format is unexpected

        resource_text += f"| {matter.get('matter_id', 'N/A')} | {matter.get('client_name', 'N/A')} | {matter.get('matter_name', 'N/A')} | "
        resource_text += f"{matter.get('matter_status', 'N/A')} | {matter.get('num_entries', 0)} | {last_act} |\n"
    return resource_text

def handle_case_summary_single(db, matter_id_str: str) -> str:
    """Generates summary for a single matter"""
    try:
        matter_id = int(matter_id_str)
    except ValueError:
        raise ValueError(f"Invalid matter ID format: {matter_id_str}")

    # Get matter details
    matter_query = """
    SELECT
        m.*, -- Select all from matters
        c.client_name,
        (SELECT COUNT(*) FROM case_file_entries cf WHERE cf.matter_id = m.matter_id) as num_entries,
        (SELECT COUNT(*) FROM billing_entries be WHERE be.matter_id = m.matter_id) as num_billing_entries,
        COALESCE((SELECT SUM(be.billing_hours) FROM billing_entries be WHERE be.matter_id = m.matter_id), 0) as total_hours, -- Handle NULL sum
        (SELECT MAX(cf.date) FROM case_file_entries cf WHERE cf.matter_id = m.matter_id) as last_activity
    FROM
        matters m
    JOIN
        clients c ON m.client_id = c.client_id
    WHERE
        m.matter_id = ?
    """
    matter_results = db._execute_query(matter_query, [matter_id])
    if not matter_results: raise ValueError(f"Matter not found: {matter_id}")
    matter = matter_results[0]

    # Get recent entries
    entries_query = """
    SELECT entry_id, type, title, date, synopsis
    FROM case_file_entries
    WHERE matter_id = ? ORDER BY date DESC LIMIT 5
    """
    entries = db._execute_query(entries_query, [matter_id])

    # Get billing summary by category
    billing_query = """
    SELECT billing_category, COUNT(*) as count, SUM(billing_hours) as total_hours
    FROM billing_entries
    WHERE matter_id = ? GROUP BY billing_category ORDER BY billing_category
    """
    billing = db._execute_query(billing_query, [matter_id])

    # Format resource text
    resource_text = f"# Case Matter Summary: {matter.get('matter_name', 'N/A')}\n\n"
    resource_text += f"**Client:** {matter.get('client_name', 'N/A')} (ID: {matter.get('client_id', 'N/A')})\n"
    resource_text += f"**Matter ID:** {matter.get('matter_id', 'N/A')}\n"
    resource_text += f"**Status:** {matter.get('matter_status', 'N/A')}\n"
    # Timestamps might not exist if added later, use .get()
    created_ts = matter.get('created')
    modified_ts = matter.get('last_modified')
    if created_ts: resource_text += f"**Created:** {created_ts}\n"
    if modified_ts: resource_text += f"**Last Modified:** {modified_ts}\n"
    last_act = matter.get('last_activity') or 'No activity'
    if last_act != 'No activity':
         try: last_act = datetime.strptime(last_act.split('.')[0], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M')
         except ValueError: pass
    resource_text += f"**Last Activity:** {last_act}\n\n"

    resource_text += f"**Case File Entries:** {matter.get('num_entries', 0)}\n"
    resource_text += f"**Billing Entries:** {matter.get('num_billing_entries', 0)}\n"
    resource_text += f"**Total Hours Logged:** {matter.get('total_hours', 0.0):.2f}\n\n" # Format hours

    if entries:
        resource_text += "## Recent Case File Entries\n\n"
        resource_text += "| Entry ID | Type | Date & Time | Title | Synopsis (Start) |\n"
        resource_text += "|----------|------|-------------|-------|------------------|\n"
        for entry in entries:
            entry_date = entry.get('date', 'N/A')
            if entry_date != 'N/A':
                 try: entry_date = datetime.strptime(entry_date.split('.')[0], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M')
                 except ValueError: pass
            synopsis = (entry.get('synopsis') or '')[:50] + ('...' if entry.get('synopsis') and len(entry['synopsis']) > 50 else '')
            resource_text += f"| {entry.get('entry_id', 'N/A')} | {entry.get('type', 'N/A')} | {entry_date} | "
            resource_text += f"{entry.get('title', 'N/A')} | {synopsis} |\n"
        resource_text += "\n"

    if billing:
        resource_text += "## Billing Summary by Category\n\n"
        resource_text += "| Category | Entries | Total Hours |\n"
        resource_text += "|----------|---------|-------------|\n"
        for b in billing:
            resource_text += f"| {b.get('billing_category', 'N/A')} | {b.get('count', 0)} | {b.get('total_hours', 0.0):.2f} |\n" # Format hours
        resource_text += "\n"

    # Add link to deadlines resource
    resource_text += f"See also: [Upcoming Deadlines](deadline://list/{matter_id})\n"

    return resource_text

def handle_billing_report_all(db) -> str:
    """Generates report of latest 50 billing entries"""
    query = """
    SELECT
        be.billing_id,
        c.client_name,
        m.matter_name,
        be.billing_category,
        be.billing_start,
        be.billing_hours,
        CASE WHEN ibi.id IS NOT NULL THEN ci.status ELSE 'unbilled' END as entry_status, -- Show invoice status if billed
        be.billing_description
    FROM
        billing_entries be
    JOIN
        matters m ON be.matter_id = m.matter_id
    JOIN
        clients c ON m.client_id = c.client_id
    LEFT JOIN
        invoice_billing_items ibi ON be.billing_id = ibi.billing_id
    LEFT JOIN
        client_invoices ci ON ibi.invoice_id = ci.invoice_id
    ORDER BY
        be.billing_start DESC
    LIMIT 50
    """
    results = db._execute_query(query)
    if not results: return "No billing entries found."

    resource_text = "# Recent Billing Entries (Latest 50)\n\n"
    resource_text += "| Bill ID | Client | Matter | Category | Start Date | Hours | Status | Description (Start) |\n"
    resource_text += "|---------|--------|--------|----------|------------|-------|--------|---------------------|\n"
    for entry in results:
        start_date = entry.get('billing_start', '').split(' ')[0] if entry.get('billing_start') else 'N/A'
        hours = entry.get('billing_hours', 0.0) or 0.0
        desc = (entry.get('billing_description') or '')[:30] + '...'
        status = entry.get('entry_status', 'unbilled') or 'unbilled'
        resource_text += f"| {entry.get('billing_id', 'N/A')} | {entry.get('client_name', 'N/A')} | {entry.get('matter_name', 'N/A')} | "
        resource_text += f"{entry.get('billing_category', 'N/A')} | {start_date} | {hours:.2f} | {status} | {desc} |\n"
    return resource_text

def handle_billing_report_single(db, matter_id_str: str) -> str:
    """Generates billing report for a single matter"""
    try:
        matter_id = int(matter_id_str)
    except ValueError:
        raise ValueError(f"Invalid matter ID format: {matter_id_str}")

    # Get matter details
    matter_query = "SELECT m.matter_name, c.client_name, m.client_id FROM matters m JOIN clients c ON m.client_id = c.client_id WHERE m.matter_id = ?"
    matter_results = db._execute_query(matter_query, [matter_id])
    if not matter_results: raise ValueError(f"Matter not found: {matter_id}")
    matter = matter_results[0]

    # Get billing entries with invoice status
    billing_query = """
    SELECT
        be.*, -- Select all from billing_entries
        CASE WHEN ibi.id IS NOT NULL THEN ci.status ELSE 'unbilled' END as invoice_status,
        ibi.invoice_id,
        ci.invoice_number
    FROM
        billing_entries be
    LEFT JOIN
        invoice_billing_items ibi ON be.billing_id = ibi.billing_id
    LEFT JOIN
        client_invoices ci ON ibi.invoice_id = ci.invoice_id
    WHERE
        be.matter_id = ?
    ORDER BY
        be.billing_start DESC
    """
    entries = db._execute_query(billing_query, [matter_id])

    # Get billing summary by category, including billed vs unbilled breakdown
    summary_query = """
    SELECT
        billing_category,
        COUNT(*) as count,
        SUM(billing_hours) as total_hours,
        SUM(CASE WHEN ibi.id IS NOT NULL THEN 1 ELSE 0 END) as billed_count,
        SUM(CASE WHEN ibi.id IS NOT NULL THEN billing_hours ELSE 0 END) as billed_hours
    FROM
        billing_entries be
    LEFT JOIN
        invoice_billing_items ibi ON be.billing_id = ibi.billing_id
    WHERE
        be.matter_id = ?
    GROUP BY
        billing_category
    ORDER BY billing_category
    """
    summary = db._execute_query(summary_query, [matter_id])

    # Format report
    resource_text = f"# Billing Report: {matter.get('matter_name', 'N/A')}\n\n"
    resource_text += f"**Client:** {matter.get('client_name', 'N/A')} (ID: {matter.get('client_id', 'N/A')})\n"
    resource_text += f"**Matter ID:** {matter_id}\n\n"

    if summary:
        total_hours_all = sum(s.get('total_hours', 0.0) or 0.0 for s in summary)
        total_billed_hours = sum(s.get('billed_hours', 0.0) or 0.0 for s in summary)
        total_unbilled_hours = total_hours_all - total_billed_hours

        resource_text += f"**Overall Total Hours:** {total_hours_all:.2f}\n"
        resource_text += f"**Overall Billed Hours:** {total_billed_hours:.2f}\n"
        resource_text += f"**Overall Unbilled Hours:** {total_unbilled_hours:.2f}\n\n"

        resource_text += "## Billing Summary by Category\n\n"
        resource_text += "| Category | Total Entries | Total Hours | Billed Entries | Billed Hours | Unbilled Hours |\n"
        resource_text += "|----------|---------------|-------------|----------------|--------------|----------------|\n"
        for s in summary:
            cat_total = s.get('total_hours', 0.0) or 0.0
            cat_billed = s.get('billed_hours', 0.0) or 0.0
            cat_unbilled = cat_total - cat_billed
            resource_text += f"| {s.get('billing_category', 'N/A')} | {s.get('count', 0)} | {cat_total:.2f} | "
            resource_text += f"{s.get('billed_count', 0)} | {cat_billed:.2f} | {cat_unbilled:.2f} |\n"
        resource_text += "\n"

    if entries:
        resource_text += "## All Billing Entries for Matter\n\n"
        resource_text += "| Bill ID | Category | Start Date/Time | Hours | Status | Invoice # | Description (Start) |\n"
        resource_text += "|---------|----------|-----------------|-------|--------|-----------|---------------------|\n"
        for entry in entries:
            start_dt = entry.get('billing_start', 'N/A')
            if start_dt != 'N/A':
                 try: start_dt = datetime.strptime(start_dt.split('.')[0], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M')
                 except ValueError: pass
            hours = entry.get('billing_hours', 0.0) or 0.0
            status = entry.get('invoice_status', 'unbilled') or 'unbilled'
            inv_num = entry.get('invoice_number', '') or '' # Handle None
            desc = (entry.get('billing_description') or '')[:30] + '...'
            resource_text += f"| {entry.get('billing_id', 'N/A')} | {entry.get('billing_category', 'N/A')} | {start_dt} | "
            resource_text += f"{hours:.2f} | {status} | {inv_num} | {desc} |\n"
    else:
        resource_text += "No billing entries found for this matter.\n"

    return resource_text

def handle_client_billing(db, client_id_str: str) -> str:
    """Generates billing report for a specific client across all matters"""
    try:
        client_id = int(client_id_str)
    except ValueError:
        raise ValueError(f"Invalid client ID format: {client_id_str}")

    # Get client details
    client_query = "SELECT client_name, created FROM clients WHERE client_id = ?"
    client_results = db._execute_query(client_query, [client_id])
    if not client_results: raise ValueError(f"Client not found: {client_id}")
    client = client_results[0]

    # Get matters summary for this client
    matters_query = """
    SELECT
        m.matter_id, m.matter_name, m.matter_status,
        COUNT(be.billing_id) as billing_count,
        SUM(COALESCE(be.billing_hours, 0)) as billing_hours -- Sum hours, handle NULL
    FROM matters m
    LEFT JOIN billing_entries be ON m.matter_id = be.matter_id
    WHERE m.client_id = ?
    GROUP BY m.matter_id, m.matter_name, m.matter_status
    ORDER BY m.matter_id
    """
    matters = db._execute_query(matters_query, [client_id])

    # Get billing summary by matter and category
    billing_query = """
    SELECT
        m.matter_id, m.matter_name, be.billing_category,
        COUNT(*) as entry_count, SUM(be.billing_hours) as total_hours,
        SUM(CASE WHEN ibi.id IS NOT NULL THEN 1 ELSE 0 END) as billed_count,
        SUM(CASE WHEN ibi.id IS NOT NULL THEN be.billing_hours ELSE 0 END) as billed_hours
    FROM billing_entries be
    JOIN matters m ON be.matter_id = m.matter_id
    LEFT JOIN invoice_billing_items ibi ON be.billing_id = ibi.billing_id
    WHERE m.client_id = ?
    GROUP BY m.matter_id, m.matter_name, be.billing_category
    ORDER BY m.matter_id, be.billing_category
    """
    billing = db._execute_query(billing_query, [client_id])

    # Get invoices for this client
    invoices_query = """
    SELECT ci.*, m.matter_name
    FROM client_invoices ci
    JOIN matters m ON ci.matter_id = m.matter_id
    WHERE ci.client_id = ? ORDER BY ci.date_created DESC
    """
    invoices = db._execute_query(invoices_query, [client_id])

    # Format Report
    resource_text = f"# Client Billing Report: {client.get('client_name', 'N/A')}\n\n"
    resource_text += f"**Client ID:** {client_id}\n"
    created_ts = client.get('created')
    if created_ts: resource_text += f"**Client Since:** {created_ts}\n"
    resource_text += "\n"

    if matters:
        resource_text += "## Client Matters Summary\n\n"
        resource_text += "| Matter ID | Matter Name | Status | Billing Entries | Total Hours |\n"
        resource_text += "|-----------|-------------|--------|-----------------|-------------|\n"
        for matter in matters:
            resource_text += f"| {matter.get('matter_id', 'N/A')} | {matter.get('matter_name', 'N/A')} | {matter.get('matter_status', 'N/A')} | "
            resource_text += f"{matter.get('billing_count', 0)} | {matter.get('billing_hours', 0.0):.2f} |\n"
        resource_text += "\n"

    if billing:
        # Group billing by matter for structured output
        billing_by_matter = defaultdict(lambda: {'matter_name': '', 'categories': [], 'total_hours': 0.0, 'billed_hours': 0.0})
        for b in billing:
            matter_id = b['matter_id']
            billing_by_matter[matter_id]['matter_name'] = b['matter_name']
            billing_by_matter[matter_id]['categories'].append(b)
            billing_by_matter[matter_id]['total_hours'] += b.get('total_hours', 0.0) or 0.0
            billing_by_matter[matter_id]['billed_hours'] += b.get('billed_hours', 0.0) or 0.0

        resource_text += "## Billing Details by Matter\n\n"
        for matter_id, matter_data in sorted(billing_by_matter.items()):
            unbilled_hours = matter_data['total_hours'] - matter_data['billed_hours']
            resource_text += f"### {matter_data['matter_name']} (Matter ID: {matter_id})\n\n"
            resource_text += f"**Total Hours:** {matter_data['total_hours']:.2f}\n"
            resource_text += f"**Billed Hours:** {matter_data['billed_hours']:.2f}\n"
            resource_text += f"**Unbilled Hours:** {unbilled_hours:.2f}\n\n"
            resource_text += "| Category | Total Entries | Total Hours | Billed Entries | Billed Hours |\n"
            resource_text += "|----------|---------------|-------------|----------------|--------------|\n"
            for cat in sorted(matter_data['categories'], key=lambda x: x['billing_category']):
                resource_text += f"| {cat.get('billing_category', 'N/A')} | {cat.get('entry_count', 0)} | {cat.get('total_hours', 0.0):.2f} | "
                resource_text += f"{cat.get('billed_count', 0)} | {cat.get('billed_hours', 0.0):.2f} |\n"
            resource_text += "\n"

    if invoices:
        resource_text += "## Client Invoices\n\n"
        resource_text += "| Inv ID | Inv # | Matter Name | Date Created | Status | Hours | Amount | Balance Due | Valid |\n"
        resource_text += "|--------|-------|-------------|--------------|--------|-------|--------|-------------|-------|\n"
        for invoice in invoices:
            # Format currency and hours
            amount = f"${invoice.get('total_amount', 0.0):,.2f}"
            balance = f"${invoice.get('balance_due', 0.0):,.2f}"
            hours = f"{invoice.get('total_hours', 0.0):.2f}"
            valid_status = "✓" if bool(invoice.get('is_valid', False)) else "✗"
            created_date = invoice.get('date_created', 'N/A')
            if created_date != 'N/A':
                 try: created_date = datetime.strptime(created_date.split('.')[0], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
                 except ValueError: pass

            resource_text += f"| {invoice.get('invoice_id', 'N/A')} | {invoice.get('invoice_number', 'N/A')} | {invoice.get('matter_name', 'N/A')} | "
            resource_text += f"{created_date} | {invoice.get('status', 'N/A')} | {hours} | {amount} | {balance} | {valid_status} |\n"
        resource_text += "\n"

    return resource_text

def handle_invoice_detail(db, invoice_id_str: str) -> str:
    """Generates detailed view of a specific invoice"""
    try:
        invoice_id = int(invoice_id_str)
    except ValueError:
        raise ValueError(f"Invalid invoice ID format: {invoice_id_str}")

    # Get invoice header details
    invoice_query = """
    SELECT ci.*, c.client_name, m.matter_name
    FROM client_invoices ci
    JOIN clients c ON ci.client_id = c.client_id
    JOIN matters m ON ci.matter_id = m.matter_id
    WHERE ci.invoice_id = ?
    """
    invoice_results = db._execute_query(invoice_query, [invoice_id])
    if not invoice_results: raise ValueError(f"Invoice not found: {invoice_id}")
    invoice = invoice_results[0]

    # Get invoice line items
    items_query = """
    SELECT ibi.status as item_status, be.* -- Get item status and all billing details
    FROM invoice_billing_items ibi
    JOIN billing_entries be ON ibi.billing_id = be.billing_id
    WHERE ibi.invoice_id = ? ORDER BY be.billing_start
    """
    items = db._execute_query(items_query, [invoice_id])

    # Format Report
    resource_text = f"# Invoice Detail: #{invoice.get('invoice_number', 'N/A')}\n\n"
    resource_text += f"**Invoice ID:** {invoice.get('invoice_id', 'N/A')}\n"
    resource_text += f"**Client:** {invoice.get('client_name', 'N/A')} (ID: {invoice.get('client_id', 'N/A')})\n"
    resource_text += f"**Matter:** {invoice.get('matter_name', 'N/A')} (ID: {invoice.get('matter_id', 'N/A')})\n"
    resource_text += f"**Status:** {invoice.get('status', 'N/A')}\n"
    created_date = invoice.get('date_created', 'N/A')
    submitted_date = invoice.get('date_submitted') # Might be None
    if created_date != 'N/A':
         try: created_date = datetime.strptime(created_date.split('.')[0], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
         except ValueError: pass
    resource_text += f"**Created:** {created_date}\n"
    if submitted_date:
         try: submitted_date = datetime.strptime(submitted_date.split('.')[0], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
         except ValueError: pass
         resource_text += f"**Submitted:** {submitted_date}\n"
    resource_text += f"**Version:** {invoice.get('version_number', 1)}\n"
    resource_text += f"**Valid for Submission:** {'Yes' if bool(invoice.get('is_valid', False)) else 'No'}\n"
    resource_text += f"**Last Validity Check:** {invoice.get('last_validity_check', 'N/A')}\n\n"

    resource_text += f"**Total Hours:** {invoice.get('total_hours', 0.0):.2f}\n"
    resource_text += f"**Total Amount:** ${invoice.get('total_amount', 0.0):,.2f}\n"
    resource_text += f"**Balance Due:** ${invoice.get('balance_due', 0.0):,.2f}\n\n"
    if invoice.get('notes'):
         resource_text += f"**Notes:** {invoice['notes']}\n\n"

    if not bool(invoice.get('is_valid', True)) and invoice.get('status') == 'draft':
         # Optionally add conflict details if the view/tool exists
         resource_text += "**⚠️ Validation Conflicts:** This draft invoice has time conflicts and cannot be submitted until resolved.\n\n"

    if items:
        resource_text += "## Invoice Line Items\n\n"
        resource_text += "| Bill ID | Category | Start Date/Time | Hours | Item Status | Description (Start) |\n"
        resource_text += "|---------|----------|-----------------|-------|-------------|---------------------|\n"
        for item in items:
            start_dt = item.get('billing_start', 'N/A')
            if start_dt != 'N/A':
                 try: start_dt = datetime.strptime(start_dt.split('.')[0], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M')
                 except ValueError: pass
            hours = item.get('billing_hours', 0.0) or 0.0
            desc = (item.get('billing_description') or '')[:30] + '...'
            item_status = item.get('item_status', 'N/A') # Status from invoice_billing_items
            resource_text += f"| {item.get('billing_id', 'N/A')} | {item.get('billing_category', 'N/A')} | {start_dt} | "
            resource_text += f"{hours:.2f} | {item_status} | {desc} |\n"
    else:
        resource_text += "No line items found for this invoice.\n"

    return resource_text

def handle_deadline_list(db, matter_id_str: str) -> str:
    """Generates list of upcoming deadlines for a specific matter"""
    try:
        matter_id = int(matter_id_str)
    except ValueError:
        raise ValueError(f"Invalid matter ID format: {matter_id_str}")

    # Verify matter exists
    matter_query = "SELECT matter_name FROM matters WHERE matter_id = ?"
    matter_info = db._execute_query(matter_query, [matter_id])
    if not matter_info: raise ValueError(f"Matter not found: {matter_id}")
    matter_name = matter_info[0]['matter_name']

    # Get upcoming events from calendar_events table for this matter
    # Assuming 'case_id' in calendar_events corresponds to 'matter_id'
    # Fetch events starting from today onwards
    today_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    deadline_query = """
    SELECT
        event_id,
        event_title,
        event_start,
        event_end,
        event_type,
        event_description,
        event_location,
        event_status
    FROM calendar_events
    WHERE case_id = ? AND event_start >= ?
    ORDER BY event_start ASC
    LIMIT 20 -- Limit results for brevity
    """
    deadlines = db._execute_query(deadline_query, [matter_id, today_str])

    # Format Report
    resource_text = f"# Upcoming Deadlines & Events: {matter_name} (Matter ID: {matter_id})\n\n"

    if not deadlines:
        resource_text += "No upcoming deadlines or events found in the calendar for this matter."
        return resource_text

    resource_text += "| Event ID | Date & Time | Type | Title | Status | Location |\n"
    resource_text += "|----------|---------------|------|-------|--------|----------|\n"
    dt_format_in = '%Y-%m-%d %H:%M:%S'
    dt_format_out = '%Y-%m-%d %H:%M'

    for event in deadlines:
        start_dt = event.get('event_start', 'N/A')
        if start_dt != 'N/A':
             try: start_dt = datetime.strptime(start_dt.split('.')[0], dt_format_in).strftime(dt_format_out)
             except ValueError: pass # Keep original if format is wrong

        resource_text += f"| {event.get('event_id', 'N/A')} | {start_dt} | {event.get('event_type', 'N/A')} | "
        resource_text += f"{event.get('event_title', 'N/A')} | {event.get('event_status', 'N/A')} | {event.get('event_location', 'N/A')} |\n"
        # Optionally add description on a new line if needed
        # desc = event.get('event_description')
        # if desc:
        #    resource_text += f"|          |               |      |       |        | > {desc[:50]}... |\n"

    return resource_text


# --- Main Resource Reading Dispatcher ---

def handle_read_resource(db, uri: AnyUrl) -> str:
    """Handle resource reading requests by dispatching based on URI scheme and path"""
    logger.debug(f"Handling read_resource request for URI: {uri}")
    uri_str = str(uri)
    scheme = uri.scheme

    try:
        if scheme == "case":
            path = uri_str.replace("case://", "")
            if path.startswith("summary/"):
                matter_id_str = path.replace("summary/", "")
                if matter_id_str == "all":
                    return handle_case_summary_all(db)
                else:
                    return handle_case_summary_single(db, matter_id_str)

        elif scheme == "billing":
            path = uri_str.replace("billing://", "")
            if path.startswith("report/"):
                report_id_str = path.replace("report/", "")
                if report_id_str == "all":
                    return handle_billing_report_all(db)
                else: # Assumes report ID is matter ID
                    return handle_billing_report_single(db, report_id_str)
            elif path.startswith("client/"):
                client_id_str = path.replace("client/", "")
                return handle_client_billing(db, client_id_str)

        elif scheme == "invoice":
            path = uri_str.replace("invoice://", "")
            if path.startswith("detail/"):
                invoice_id_str = path.replace("detail/", "")
                return handle_invoice_detail(db, invoice_id_str)

        elif scheme == "deadline":
            path = uri_str.replace("deadline://", "")
            if path.startswith("list/"):
                matter_id_str = path.replace("list/", "")
                return handle_deadline_list(db, matter_id_str)

        # If no match above
        logger.warning(f"Unsupported resource URI structure: {uri_str}")
        raise ValueError(f"Unsupported or unrecognized resource URI: {uri_str}")

    except ValueError as e:
         # Catch specific errors like invalid IDs or formats
         logger.error(f"Error handling resource {uri_str}: {e}")
         return f"Error: {e}" # Return error message to the client
    except Exception as e:
         # Catch unexpected errors during resource generation
         logger.error(f"Unexpected error generating resource {uri_str}: {e}", exc_info=True)
         return f"An unexpected server error occurred while generating the resource."


