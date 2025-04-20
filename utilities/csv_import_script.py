#!/usr/bin/env python3
"""
CSV Import Script for Heaven Sampson Matter

This script imports case file entry data from a CSV file into the SQLite database
for the Heaven Sampson matter (matter_id: 1).
"""

import csv
import sqlite3
import os
from datetime import datetime

# Configuration - Updated with the actual paths
DB_PATH = "/Users/andrewsirulnik/Claude_mcp_servers/mcp-sqlite-server/database/mcp_server.db"
CSV_PATH = "/Users/andrewsirulnik/Library/CloudStorage/OneDrive-LawOffice/clients/~GAL Appts/Heaven S/billing/export_4-8-25.csv"
MATTER_ID = 1  # This is the matter_id for Heaven Sampson matter

def connect_to_db():
    """Connect to the SQLite database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        exit(1)

def validate_csv_file(csv_path):
    """Validate that the CSV file exists and has the expected headers."""
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        return False
    
    required_headers = ["date", "type", "title", "from", "to", "cc", "content", 
                      "attachments", "synopsis", "comments"]
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as csvfile:  # Using utf-8-sig to handle BOM
            reader = csv.reader(csvfile)
            headers = next(reader)
            
            # Check if headers match (case-insensitive)
            headers_lower = [h.lower() for h in headers]
            print(f"Found headers: {headers}")
            
            # Check if all required headers are present
            missing_headers = []
            for required_header in required_headers:
                if required_header not in headers_lower:
                    missing_headers.append(required_header)
            
            if missing_headers:
                print(f"Error: Missing required headers: {missing_headers}")
                return False
                
            # Check if file has data
            if sum(1 for _ in reader) == 0:
                print("Warning: CSV file is empty (contains only headers).")
        
        return True
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return False

def parse_date(date_str):
    """Parse date string into datetime object."""
    # Try common date formats - adjust as needed for your data
    formats = [
        "%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y",
        "%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", 
        "%d-%m-%Y %H:%M:%S", "%m-%d-%Y %H:%M:%S",
        "%a %Y-%m-%d    %I:%M %p" # Format for day-of-week YYYY-MM-DD    HH:MM AM/PM
    ]
    
    if not date_str:
        return None
    
    for date_format in formats:
        try:
            return datetime.strptime(date_str, date_format)
        except ValueError:
            continue
    
    # For the record, let's still show we couldn't parse it but don't flood the output
    # print(f"Warning: Unable to parse date '{date_str}'. Using NULL.")
    return None

def import_data():
    """Import data from CSV into the database."""
    if not validate_csv_file(CSV_PATH):
        return
    
    conn = connect_to_db()
    cursor = conn.cursor()
    
    # First, check if the matter exists
    cursor.execute("SELECT matter_id FROM case_files WHERE matter_id = ?", (MATTER_ID,))
    if not cursor.fetchone():
        print(f"Error: Matter ID {MATTER_ID} does not exist in the database.")
        conn.close()
        return
    
    # Get column mapping from CSV headers to database fields
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as csvfile:  # Using utf-8-sig to handle BOM
        reader = csv.reader(csvfile)
        headers = [header.lower() for header in next(reader)]
        
        # Prepare for data import
        inserted_count = 0
        error_count = 0
        
        # Process each row
        for row_num, row in enumerate(reader, start=2):  # Start from 2 to account for header row
            if not any(row):  # Skip empty rows
                continue
                
            try:
                # Create a dictionary from the row data
                row_data = {headers[i]: value for i, value in enumerate(row) if i < len(headers)}
                
                # Parse date
                date_value = parse_date(row_data.get('date', ''))
                date_str = date_value.isoformat() if date_value else None
                
                # Prepare values for insertion
                values = (
                    MATTER_ID,
                    row_data.get('type', ''),
                    date_str,
                    row_data.get('title', ''),
                    row_data.get('from', ''),
                    row_data.get('to', ''),
                    row_data.get('cc', ''),
                    row_data.get('content', ''),
                    row_data.get('attachments', ''),
                    row_data.get('synopsis', ''),
                    row_data.get('comments', '')
                )
                
                # Insert the data
                cursor.execute('''
                    INSERT INTO case_file_entries
                    (matter_id, type, date, title, from_party, to_party, cc_party, 
                     content, attachments, synopsis, comments)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', values)
                
                inserted_count += 1
            except Exception as e:
                print(f"Error inserting row {row_num}: {e}")
                print(f"Row data: {row}")
                error_count += 1
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        print(f"Import completed. {inserted_count} rows inserted, {error_count} errors.")

if __name__ == "__main__":
    print("Starting CSV import for Heaven Sampson matter...")
    import_data()
    print("Import process completed.")