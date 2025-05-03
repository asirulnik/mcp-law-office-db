import sqlite3
import csv
import os
from datetime import datetime

# Configuration
DATABASE_PATH = "/Users/andrewsirulnik/claude_mcp_servers/mcp-law-office-db/database/law_office.db"
INPUT_FILE_PATH = input("Enter path to CSV file: ")

# Ensure the input file exists
if not os.path.exists(INPUT_FILE_PATH):
    print(f"Error: Input file {INPUT_FILE_PATH} not found.")
    exit(1)

# Connect to the database
try:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    print(f"Connected to database: {DATABASE_PATH}")
except sqlite3.Error as e:
    print(f"Error connecting to database: {e}")
    exit(1)

# Get the highest entry_id currently in use
cursor.execute("SELECT MAX(entry_id) FROM case_file_entries")
result = cursor.fetchone()
last_entry_id = result[0] if result[0] is not None else 0
print(f"Last entry ID in database: {last_entry_id}")

# Present client options
cursor.execute("SELECT client_id, client_name FROM clients ORDER BY client_name")
clients = cursor.fetchall()

print("\nExisting clients:")
for i, (client_id, client_name) in enumerate(clients, 1):
    print(f"{i}. {client_name} (ID: {client_id})")
print(f"{len(clients) + 1}. Create new client")

client_choice = int(input("\nSelect client (enter number): "))

if client_choice <= len(clients):
    selected_client_id = clients[client_choice - 1][0]
    selected_client_name = clients[client_choice - 1][1]
    print(f"Selected client: {selected_client_name}")
else:
    new_client_name = input("Enter new client name: ")
    new_client_contact = input("Enter client contact info: ")
    cursor.execute("INSERT INTO clients (client_name, contact_info) VALUES (?, ?)", 
                  (new_client_name, new_client_contact))
    conn.commit()
    selected_client_id = cursor.lastrowid
    selected_client_name = new_client_name
    print(f"Created new client '{new_client_name}' with ID: {selected_client_id}")

# Present matter options for the selected client
cursor.execute("SELECT matter_id, matter_name FROM matters WHERE client_id = ? ORDER BY matter_name", 
              (selected_client_id,))
matters = cursor.fetchall()

print("\nExisting matters for this client:")
for i, (matter_id, matter_name) in enumerate(matters, 1):
    print(f"{i}. {matter_name} (ID: {matter_id})")
print(f"{len(matters) + 1}. Create new matter")

matter_choice = int(input("\nSelect matter (enter number): "))

if matter_choice <= len(matters):
    selected_matter_id = matters[matter_choice - 1][0]
    selected_matter_name = matters[matter_choice - 1][1]
    print(f"Selected matter: {selected_matter_name}")
else:
    new_matter_name = input("Enter new matter name: ")
    new_matter_status = input("Enter matter status (e.g., Active): ")
    cursor.execute("INSERT INTO matters (client_id, matter_name, matter_status) VALUES (?, ?, ?)", 
                  (selected_client_id, new_matter_name, new_matter_status))
    conn.commit()
    selected_matter_id = cursor.lastrowid
    selected_matter_name = new_matter_name
    print(f"Created new matter '{new_matter_name}' with ID: {selected_matter_id}")

# Function to parse date string into SQLite datetime format
def parse_date(date_str):
    if not date_str or date_str.strip() == '' or date_str.strip('"\'') == '':
        return None
        
    try:
        # Remove any quotes
        date_str = date_str.strip('"\'')
        
        # Handle different date formats
        if '/' in date_str:
            parts = date_str.split('/')
            if len(parts) == 3:
                month, day, year = parts
                
                # Check if there's a time component
                if ' ' in year:
                    year_part, time_part = year.split(' ', 1)
                    year = year_part
                    
                    # Parse time if present
                    if ':' in time_part:
                        hours, minutes = time_part.split(':', 1)
                        if ' ' in minutes:  # Handle AM/PM
                            minutes, am_pm = minutes.split(' ', 1)
                            hours = int(hours)
                            if 'pm' in am_pm.lower() and hours < 12:
                                hours += 12
                            elif 'am' in am_pm.lower() and hours == 12:
                                hours = 0
                        
                        return f"{year.zfill(4)}-{month.zfill(2)}-{day.zfill(2)} {str(hours).zfill(2)}:{minutes.zfill(2)}:00"
                
                # Date only
                return f"{year.zfill(4)}-{month.zfill(2)}-{day.zfill(2)} 00:00:00"
        
        # ISO format
        if 'T' in date_str:
            date_part, time_part = date_str.split('T')
            return f"{date_part} {time_part[0:8]}"
            
        # Simple date-time format
        if ' ' in date_str and '-' in date_str:
            return date_str
            
        print(f"Warning: Could not parse date format: {date_str}")
        return None
        
    except Exception as e:
        print(f"Error parsing date {date_str}: {e}")
        return None

# Read and parse CSV file with proper handling of quoted values
entries = []
with open(INPUT_FILE_PATH, 'r', encoding='utf-8') as file:
    # Use CSV reader to properly handle quoted fields
    csv_reader = csv.reader(file)
    
    # Read header
    header = next(csv_reader)
    print(f"\nDetected headers: {header}")
    
    # Clean up header names (remove quotes)
    clean_header = [h.strip('"\'') for h in header]
    print(f"Cleaned headers: {clean_header}")
    
    # Map column indices
    try:
        sent_idx = clean_header.index('Sent')
        received_idx = clean_header.index('Received')
        from_idx = clean_header.index('From')
        to_idx = clean_header.index('To')
        cc_idx = clean_header.index('CC')
        subject_idx = clean_header.index('Subject')
        message_idx = clean_header.index('Message')
    except ValueError as e:
        print(f"Error: Required column missing in CSV file: {e}")
        exit(1)
    
    # Parse the rest of the CSV
    for row in csv_reader:
        if row and len(row) >= max(sent_idx, received_idx, from_idx, to_idx, cc_idx, subject_idx, message_idx) + 1:
            entries.append(row)
        else:
            print(f"Warning: Row has insufficient columns: {len(row)}. Skipping.")

print(f"\nFound {len(entries)} entries to process")

# Counters for statistics
entries_processed = 0
entries_added = 0
entries_skipped = 0
errors = 0

# Process each entry
next_entry_id = last_entry_id + 1
for row in entries:
    try:
        # Extract data from row (stripping quotes)
        sent_value = row[sent_idx].strip() if sent_idx < len(row) else ""
        received_value = row[received_idx].strip() if received_idx < len(row) else ""
        from_party = row[from_idx].strip() if from_idx < len(row) else ""
        to_party = row[to_idx].strip() if to_idx < len(row) else ""
        cc_party = row[cc_idx].strip() if cc_idx < len(row) else ""
        title = row[subject_idx].strip() if subject_idx < len(row) else ""
        content = row[message_idx].strip() if message_idx < len(row) else ""
        
        # Debug output for the Received field
        print(f"Raw received value: '{received_value}'")
        
        # Parse dates
        sent = parse_date(sent_value) if sent_value else None
        received = parse_date(received_value) if received_value else None
        
        # Debug output after parsing
        print(f"Parsed sent: {sent}")
        print(f"Parsed received: {received}")
        
        # Determine entry type
        entry_type = "Email"  # Default to Email type
        
        # Determine if this is an outgoing or incoming email
        is_outgoing = False
        if from_party:
            email_parts = [addr.strip().lower() for addr in from_party.split(';')]
            if any("andrew@sirulnik-law.com" in addr for addr in email_parts):
                is_outgoing = True
                print("Detected outgoing email")
            else:
                print("Detected incoming email")
        
        # Determine date based on rules:
        # For outgoing emails (from contains user's email), date = sent
        # For incoming emails, date = received
        date = None
        if is_outgoing and sent:
            date = sent
            print(f"Using sent date ({sent}) as primary date for outgoing email")
        elif not is_outgoing and received:
            date = received
            print(f"Using received date ({received}) as primary date for incoming email")
        else:
            print("Could not determine primary date based on email direction")
        
        # Insert new entry
        entry_id = next_entry_id
        cursor.execute('''
            INSERT INTO case_file_entries (
                entry_id, client_id, matter_id, type, date, sent, received, "from", "to", cc, 
                title, content, last_modified
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ''', (
            entry_id, selected_client_id, selected_matter_id, entry_type, date, sent, received,
            from_party, to_party, cc_party, title, content
        ))
        
        next_entry_id += 1
        entries_added += 1
        print(f"Added entry {entry_id}: {title[:50]}" + ("..." if len(title) > 50 else ""))
        print(f"Entry details - sent: {sent}, received: {received}, date: {date}\n")
    
    except Exception as e:
        print(f"Error processing entry: {e}")
        print(f"Problematic row: {row[:5]}...")  # Show first few columns for debugging
        errors += 1
    
    entries_processed += 1

# Commit changes and close connection
conn.commit()
print("\nDatabase update summary:")
print(f"  Entries processed: {entries_processed}")
print(f"  Entries added: {entries_added}")
print(f"  Entries skipped: {entries_skipped}")
print(f"  Errors: {errors}")

conn.close()
print("Database connection closed.")